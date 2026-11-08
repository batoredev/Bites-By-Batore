"""Isolated coverage, privacy, retry and scheduling regressions; no invented real labels."""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import pytest
from sqlalchemy import select
from app import research, jobs
from app.config import settings
from app.db import Session, ResearchSource, Job, now
from app.analysis_inputs import split_evidence, AnalysisLimit
from app.analysis_reuse import analysis_key, mark, reusable
from app.media import frame_points
from app.performance import Trace, ACTIVE_TRACE, span, delivery_metrics, model_metrics, owner_report
from app.providers import DeferredCollection, ACTIVE_JOB, Unavailable


def source_case(db, owner="owner", code="coverage"):
    case = research.start_case(
        db,
        owner,
        "Coimbatore cafes",
        seed_sources=[
            {
                "platform": "instagram",
                "url": f"https://www.instagram.com/p/{code}/",
                "caption": "Private fixture cafe Coimbatore",
            }
        ],
    )
    return case, research.case_sources(db, case)[0]


def test_sampling_preserves_end_with_many_early_scene_changes():
    points = frame_points(90, 8, [i / 10 for i in range(1, 200)])
    assert points[0] == 0 and points[-1] == 89.85 and len(points) == 8
    assert max(b - a for a, b in zip(points, points[1:])) < 25
    assert frame_points(0.1, 8, []) == [0.0]
    assert frame_points(90, 1, [10]) == [0.0]


def test_unicode_segmentation_keeps_every_character_and_absolute_offsets():
    text = ("தமிழ் address and offer conditions. " * 500) + "FINAL BRANCH ONLY; NOT A GROUP PRICE"
    parts = split_evidence({"caption": text, "source_url": "https://example.org/"}, 1400)
    covered = set()
    for part in parts:
        segment = part["evidence_segment"]
        assert part["caption"] == text[segment["start"] : segment["end"]]
        assert len(json.dumps(part, ensure_ascii=False)) <= 1400
        covered.update(range(segment["start"], segment["end"]))
    assert len(covered) == len(text) and text.endswith(parts[-1]["caption"])
    nested = split_evidence(parts[2], 900)
    for part in nested:
        segment = part["evidence_segment"]
        assert segment["total"] == len(text)
        assert part["caption"] == text[segment["start"] : segment["end"]]


def test_oversized_metadata_is_explicitly_incomplete():
    with pytest.raises(AnalysisLimit, match="no text was discarded"):
        split_evidence({"reviewed_examples": ["x" * 5000], "caption": "short"}, 1000)


def test_all_text_fields_are_segmented_without_tail_loss():
    content = {"caption": "c" * 8000, "transcript": "t" * 8000, "audio": {"text": "a" * 8000}}
    parts = split_evidence(content)
    assert {p["evidence_segment"]["field"] for p in parts} == {"caption", "transcript", "audio.text"}
    for key in ("caption", "transcript", "audio.text"):
        assert any(
            p["evidence_segment"]["field"] == key and p["evidence_segment"]["end"] == 8000 for p in parts
        )


def test_failure_timings_and_model_components_have_no_source_text():
    trace = Trace()
    token = ACTIVE_TRACE.set(trace)
    try:
        with pytest.raises(ValueError):
            with span("frame_preparation"):
                raise ValueError("private caption must not be logged")
        model_metrics({"load_duration": 2_000_000_000, "eval_duration": 3_000_000_000, "eval_count": 4})
    finally:
        ACTIVE_TRACE.reset(token)
    assert trace.phases["frame_preparation"]["failures"] == 1
    assert trace.model["load_seconds"] == 2 and trace.model["generation_seconds"] == 3
    assert "private caption" not in json.dumps(trace.summary())


def test_due_wait_excludes_the_scheduled_quota_delay():
    trace = Trace()
    start = datetime.fromisoformat(trace.at)
    job = SimpleNamespace(
        created_at=(start - timedelta(hours=3)).isoformat(),
        due_at=(start - timedelta(seconds=5)).isoformat(),
        state="queued",
    )
    first = delivery_metrics(job, trace, {}, "quota_or_collection_cooldown")
    assert first["last"]["age_at_start_seconds"] == 10800
    assert first["last"]["eligible_queue_wait_seconds"] == 5
    result = first
    for _ in range(25):
        result = delivery_metrics(job, trace, result)
    assert result["delivery_count"] == 26 and len(result["deliveries"]) == 20


def test_job_failure_and_retry_metrics_persist(client, monkeypatch):
    with Session() as db:
        job = jobs.enqueue(db, "timing-fixture", {}, "timing")
        ident = job.id
    monkeypatch.setattr(
        jobs, "execute_job", lambda *args: (_ for _ in ()).throw(DeferredCollection("fixture wait"))
    )
    assert jobs.run_once(include_kinds=["timing-fixture"])
    with Session() as db:
        job = db.get(Job, ident)
        assert job.state == "queued"
        perf = job.result["_performance"]
        assert perf["last"]["wait_reason"] == "quota_or_collection_cooldown"
        assert perf["last"]["phases"]["job.timing-fixture"]["failures"] == 1
        assert perf["deferred_until"] == job.due_at
        job.due_at = now()
        db.commit()
    monkeypatch.setattr(jobs, "execute_job", lambda *args: {"ready": True})
    jobs.run_once(include_kinds=["timing-fixture"])
    with Session() as db:
        job = db.get(Job, ident)
        assert job.result["ready"] and job.result["_performance"]["delivery_count"] == 2


def test_lane_filters_claim_only_eligible_kinds(client):
    with Session() as db:
        control = jobs.enqueue(db, "control-fixture", {}, "control", priority=100)
        analysis = jobs.enqueue(db, "source_analysis", {}, "analysis", priority=10)
        assert jobs.claim_job(db, include_kinds=["source_analysis"]).id == analysis.id
        assert jobs.claim_job(db, exclude_kinds=["source_analysis"]).id == control.id
        assert jobs.claim_job(db, include_kinds=["source_analysis"]) is None


def test_reuse_owner_context_holdout_expiry_and_erasure(client, monkeypatch):
    monkeypatch.setattr(settings(), "analysis_reuse_enabled", True)
    with Session() as db:
        first, source = source_case(db)
        second, target = source_case(db)
        _, private = source_case(db, "different-owner")
        data = {"caption": "Private fixture cafe", "reviewed_examples": []}
        key = analysis_key("caption", data, {}, "digest-a")
        source.analysis = {
            "caption": mark({"status": "observations_only", "venue_candidates": []}, key, "digest-a")
        }
        db.commit()
        hit = reusable(db, second, target, "caption", key, "digest-a")
        assert hit["reuse"]["from_source_id"] == source.id
        assert hit["reuse"]["computed_at"] == source.analysis["caption"]["reuse"]["computed_at"]
        assert reusable(db, db.get(type(first), private.case_id), private, "caption", key, "digest-a") is None
        assert (
            reusable(db, second, target, "caption", analysis_key("caption", data, {}, "digest-b"), "digest-b")
            is None
        )
        assert analysis_key("caption", {**data, "reviewed_examples": ["revoked"]}, {}, "digest-a") != key
        source.analysis = {**source.analysis, "evaluation_labels": {"caption": {"split": "holdout"}}}
        db.commit()
        assert reusable(db, second, target, "caption", key, "digest-a") is None
        original = source.analysis["caption"]
        for at in [
            "bad",
            "2026-01-01",
            (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
            (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
        ]:
            source.analysis = {"caption": {**original, "reuse": {**original["reuse"], "computed_at": at}}}
            db.commit()
            assert reusable(db, second, target, "caption", key, "digest-a") is None
        source.analysis = {"caption": original}
        db.commit()
        assert reusable(db, second, target, "caption", key, "digest-a")
        from app.analysis_reuse import valid_result

        assert valid_result(original, key)
        assert not valid_result({**original, "reuse": {**original["reuse"], "computed_at": "bad"}}, key)
        _, repost = source_case(db, "owner", "heldout-repost")
        for row in (source, target, repost):
            row.content = {**row.content, "content_fingerprint": "shared-fixture-origin"}
        repost.analysis = {"evaluation_labels": {"caption": {"split": "holdout"}}}
        db.commit()
        assert reusable(db, second, target, "caption", key, "digest-a") is None
        research.erase_cases(db, first.user_id)
        db.commit()
        assert not db.get(ResearchSource, source.id)


def test_changed_comment_batch_only_and_correction_context_invalidation(client, monkeypatch):
    from app.comment_analysis import analyze_comments

    monkeypatch.setattr(settings(), "analysis_reuse_enabled", True)
    calls = []

    def analyzer(db, role, content):
        calls.append(content)
        return {
            "status": "observations_only",
            "comment_labels": [
                {"index": c["index"], "kind": "question"} for c in content["indexed_comments"]
            ],
        }

    with Session() as db:
        _, source = source_case(db)
        source.content = {**source.content, "comment_texts": [f"question {i}" for i in range(12)]}
        analyze_comments(db, source, {"reviewed_examples": []}, analyzer, "model-a")
        assert len(calls) == 3
        result = analyze_comments(db, source, {"reviewed_examples": []}, analyzer, "model-a")
        assert len(calls) == 3 and [c["index"] for c in result["comment_labels"]] == list(range(12))
        changed = list(source.content["comment_texts"])
        changed[7] = "changed question"
        source.content = {**source.content, "comment_texts": changed}
        analyze_comments(db, source, {"reviewed_examples": []}, analyzer, "model-a")
        assert len(calls) == 4 and calls[-1]["indexed_comments"][0]["index"] == 5
        analyze_comments(db, source, {"reviewed_examples": ["new correction"]}, analyzer, "model-a")
        assert len(calls) == 7
        analyze_comments(db, source, {"reviewed_examples": ["new correction"]}, analyzer, "model-b")
        assert len(calls) == 10


def test_pipeline_dispatches_durable_source_jobs_without_inference(client, monkeypatch):
    monkeypatch.setattr(settings(), "app_mode", "local")
    monkeypatch.setattr(settings(), "research_streaming", True)
    monkeypatch.setattr(settings(), "research_pipeline_enabled", True)
    monkeypatch.setattr(settings(), "instagram_browser_enabled", False)
    monkeypatch.setattr(settings(), "local_search_enabled", False)
    monkeypatch.setattr(research, "stream_source", lambda *args: pytest.fail("collection called inference"))
    with Session() as db:
        case, source = source_case(db)
        research.collect_stage(db, case, SimpleNamespace())
        assert source.content["analysis_pending"]
        job = db.scalar(select(Job).where(Job.key == f"source-analysis:{source.id}"))
        assert job.state == "queued"
        with pytest.raises(research.PendingSource):
            research.analysis_stage(db, case, SimpleNamespace(role="caption"))
        case.state = "cancelled"
        db.commit()
        assert "cancelled" in jobs.execute_job(db, job)["message"]
        research.erase_cases(db, case.user_id)
        db.commit()
        assert db.get(Job, job.id) is None


def test_scheduler_recovers_missing_analysis_delivery(client, monkeypatch):
    monkeypatch.setattr(settings(), "app_mode", "local")
    monkeypatch.setattr(settings(), "research_pipeline_enabled", True)
    with Session() as db:
        case, source = source_case(db)
        source.content = {**source.content, "analysis_pending": True}
        db.commit()
        source_id = source.id
    jobs.schedule()
    jobs.schedule()
    with Session() as db:
        rows = list(db.scalars(select(Job).where(Job.key == f"source-analysis:{source_id}")))
        assert len(rows) == 1 and rows[0].state == "queued"


def test_all_locations_and_separate_same_brand_branches_survive_matching(client):
    with Session() as db:
        case, source = source_case(db)
        candidates = [{"name": f"Fixture cafe {i}", "address_clues": [f"Road {i}"]} for i in range(12)]
        candidates += [
            {"name": "Shared brand fixture", "address_clues": ["Road A"]},
            {"name": "Shared brand fixture", "address_clues": ["Road B"]},
        ]
        source.analysis = {"caption": {"venue_candidates": candidates}}
        db.commit()
        research.location_stage(db, case, None)
        assert len(source.analysis["location"]["hypotheses"]) == 14


def test_multi_pass_merge_preserves_more_than_five_venues(client, monkeypatch):
    from app.analysts import analyze
    from app import local_models

    monkeypatch.setattr(settings(), "app_mode", "local")
    seen = []

    def chat(prompt, content, schema, frames):
        seen.append(content)
        start = content.get("evidence_segment", {}).get("start", 0)
        return json.dumps({"venue_candidates": [{"name": f"Fixture {start}-{i}"} for i in range(4)]})

    monkeypatch.setattr(local_models, "local_chat", chat)
    with Session() as db:
        result = analyze(db, "caption", {"caption": "c" * 15000})
    assert len(seen) >= 3 and len(result["venue_candidates"]) == len(seen) * 4
    assert result["coverage"][-1]["segment"]["end"] == 15000


def test_output_limit_recursively_processes_all_frames(client, monkeypatch):
    from app.analysts import analyze
    from app import local_models

    monkeypatch.setattr(settings(), "app_mode", "local")

    def chat(prompt, content, schema, frames):
        if len(frames) > 1:
            raise AnalysisLimit("fixture output full")
        return "{}"

    monkeypatch.setattr(local_models, "local_chat", chat)
    frames = [{"seconds": i, "mime": "image/jpeg", "base64": ""} for i in range(4)]
    with Session() as db:
        result = analyze(db, "reinspect", {}, frames=frames)
    assert [c["frames"] for c in result["coverage"]] == [[0], [1], [2], [3]]


def test_oversized_chat_input_never_sends_truncated_json(monkeypatch):
    from app.local_models import local_chat

    with pytest.raises(AnalysisLimit, match="no input was truncated"):
        local_chat("fixture", {"caption": "x" * 19000}, {})


def test_readiness_does_not_exit_early_on_a_smaller_comment_sample(monkeypatch):
    from app import browser_sources

    snapshots = iter([1, 2])
    calls = []

    async def snapshot(page):
        return {"scripts": [], "text": str(next(snapshots))}

    def extract(payloads, code, text, maximum):
        return {
            "caption": "fixture",
            "media_url": "https://example.org/video",
            "comment_texts": ["c"] * int(text),
        }

    class Page:
        async def wait_for_timeout(self, ms):
            calls.append(ms)

    monkeypatch.setattr(browser_sources, "read_public_snapshot", snapshot)
    monkeypatch.setattr(browser_sources, "extract_public_data", extract)
    assert asyncio.run(browser_sources.wait_public_ready(Page(), "fixture", 2)) == "configured_sample_ready"
    assert calls == [400]


def test_performance_owner_scoping_and_plan_timing_header(client, auth, request_data):
    with Session() as db:
        case, _ = source_case(db)
        other, _ = source_case(db, "private-other")
        jobs.enqueue(db, "source_analysis", {"case_id": case.id}, "perf-owner")
        jobs.enqueue(db, "source_analysis", {"case_id": other.id}, "perf-other")
        report = owner_report(db, "owner")
        assert report["owner_jobs"] == 2  # initial case discovery plus source delivery
        assert report["measured_jobs"] == 0 and report["delivery_execution"]["p95_seconds"] is None
        assert "private-other" not in json.dumps(report)
    assert client.get("/api/admin/research-performance").status_code == 401
    response = client.post("/api/plans", headers=auth, json=request_data)
    assert response.status_code == 200 and float(response.headers["Server-Timing"].split("=")[1]) >= 0


def test_cancelled_delivery_cannot_make_more_model_calls(client):
    with Session() as db:
        case, source = source_case(db)
        case.state = "cancelled"
        job = jobs.enqueue(
            db, "source_analysis", {"case_id": case.id, "source_id": source.id}, "cancelled-source"
        )
        token = ACTIVE_JOB.set(job.id)
        try:
            with pytest.raises(Unavailable, match="cancelled"):
                from app.providers import renew_job

                renew_job(db)
        finally:
            ACTIVE_JOB.reset(token)


def test_browser_host_reuses_process_and_restarts_after_eof(monkeypatch):
    import io
    from app import browser_host

    processes = []
    streams = iter(["", '{"browser":{"status":"public_content"}}\n' * 2])

    class Process:
        def __init__(self, *args, **kwargs):
            self.stdin, self.stdout = io.StringIO(), io.StringIO(next(streams))
            self.killed = False
            processes.append(self)

        def poll(self):
            return None

        def wait(self, timeout):
            return 0

        def kill(self):
            self.killed = True

    monkeypatch.setattr(browser_host.subprocess, "Popen", Process)
    host = browser_host.BrowserHost()
    try:
        with pytest.raises(Unavailable, match="helper unavailable"):
            host.request("https://www.instagram.com/reel/a/", 10)
        assert host.process is None
        assert host.request("https://www.instagram.com/reel/b/", 10)["browser"]["status"] == "public_content"
        assert host.request("https://www.instagram.com/reel/c/", 10)["browser"]["status"] == "public_content"
        assert len(processes) == 2
        assert processes[1].stdin.getvalue().count("\n") == 2
    finally:
        host.close()
    assert host.idle_timer is None


def test_shared_browser_always_closes_each_context_after_failure():
    from app.browser_sources import collect_in_browser

    contexts = []

    class Page:
        async def goto(self, *args, **kwargs):
            return SimpleNamespace(status=429)

    class Context:
        closed = False

        async def new_page(self):
            return Page()

        async def route(self, *args):
            pass

        async def close(self):
            self.closed = True

    class Browser:
        async def new_context(self, **kwargs):
            ctx = Context()
            contexts.append(ctx)
            return ctx

    async def run():
        shared = Browser()
        for code in ("one", "two"):
            result = await collect_in_browser(f"https://www.instagram.com/reel/{code}/", 10, shared)
            assert result["browser"]["status"] == "rate_limited"

    asyncio.run(run())
    assert len(contexts) == 2 and all(ctx.closed for ctx in contexts)


def test_pipeline_complete_case_waits_for_sources_and_does_not_publish(client, monkeypatch):
    from app.db import Investigation, Venue

    cfg = settings()
    for key, value in {
        "app_mode": "local",
        "research_streaming": True,
        "research_pipeline_enabled": True,
        "instagram_browser_enabled": False,
        "local_search_enabled": False,
    }.items():
        monkeypatch.setattr(cfg, key, value)
    monkeypatch.setattr(research, "discover_stage", lambda *args: {"source_count": 1})
    monkeypatch.setattr(research, "google_search", lambda *args: [])
    monkeypatch.setattr(research, "web_search", lambda *args: [])
    monkeypatch.setattr("app.analysis_reuse.model_digest", lambda: None)
    calls = []

    def analyzer(db, role, *args, **kwargs):
        calls.append(role)
        return {"status": "observations_only", "venue_candidates": [{"name": "Zircon Cafe"}]}

    monkeypatch.setattr(research, "analyze", analyzer)
    with Session() as db:
        case, source = source_case(db)
        case_id, source_id = case.id, source.id
    jobs.run_once(exclude_kinds=["source_analysis"])
    jobs.run_once(exclude_kinds=["source_analysis"])
    jobs.run_once(exclude_kinds=["source_analysis"])
    with Session() as db:
        assert db.get(ResearchSource, source_id).content["analysis_pending"]
        assert db.get(Investigation, case_id).state != "review"
    jobs.run_once(include_kinds=["source_analysis"])
    for _ in range(10):
        with Session() as db:
            for job in db.scalars(
                select(Job).where(Job.payload["case_id"].as_string() == case_id, Job.state == "queued")
            ):
                job.due_at = now()
            db.commit()
        if not jobs.run_once(exclude_kinds=["source_analysis"]):
            break
    with Session() as db:
        assert db.get(Investigation, case_id).state == "review"
        assert db.get(ResearchSource, source_id).content["streamed"]
        assert calls == ["caption"]
        assert not list(db.scalars(select(Venue).where(Venue.is_demo.is_(False))))


def test_labelled_benchmark_records_timing_without_inventing_baseline_time(client, monkeypatch):
    from app.evaluation import fingerprint, run_benchmark

    monkeypatch.setattr("app.analysis_reuse.model_digest", lambda: "fixture-digest")
    monkeypatch.setattr(
        "app.analysts.analyze",
        lambda *args, **kwargs: {
            "status": "observations_only",
            "venue_candidates": [{"name": "Zircon Cafe"}],
        },
    )
    with Session() as db:
        case, source = source_case(db)
        baseline = {"venue_candidates": [], "learning_example_ids": []}
        source.analysis = {
            "evaluation_labels": {
                "caption": {
                    "evaluate_names": True,
                    "expected_names": ["Zircon Cafe"],
                    "prediction": baseline,
                    "input_fingerprint": fingerprint(source),
                    "source_checked": True,
                    "label_origin": "fixture_only",
                }
            }
        }
        db.commit()
        result = run_benchmark(db, case.user_id, source.id, "caption")
        assert result["baseline_metrics"]["names"]["fn"] == 1
        assert result["current_metrics"]["names"]["tp"] == 1
        assert result["baseline_execution_seconds"] is None
        assert result["execution"]["execution_seconds"] >= 0
        source.content = {**source.content, "caption": "changed evidence"}
        db.commit()
        with pytest.raises(Unavailable, match="expired or changed"):
            run_benchmark(db, case.user_id, source.id, "caption")


def test_labelled_benchmark_rejects_missing_gold_and_revoked_context(client, monkeypatch):
    from app.evaluation import fingerprint, run_benchmark

    with Session() as db:
        case, source = source_case(db)
        with pytest.raises(Unavailable, match="expired or changed"):
            run_benchmark(db, case.user_id, source.id, "caption")
        source.analysis = {
            "evaluation_labels": {
                "caption": {
                    "prediction": {"learning_example_ids": ["revoked"]},
                    "input_fingerprint": fingerprint(source),
                }
            }
        }
        db.commit()
        with pytest.raises(Unavailable, match="Correction context changed"):
            run_benchmark(db, case.user_id, source.id, "caption")


def test_multilingual_token_budget_rejects_before_model_request(monkeypatch):
    from app.local_models import local_chat

    monkeypatch.setattr("app.local_tokenizer.input_tokens", lambda *args: 4000)
    with pytest.raises(AnalysisLimit, match="verified context budget"):
        local_chat("fixture prompt", {"caption": "தமிழ் end address"}, {})


def test_comment_context_overflow_splits_batches_without_losing_indices(client):
    from app.comment_analysis import analyze_comments

    calls = []

    def analyzer(db, role, content):
        batch = content["indexed_comments"]
        if len(batch) > 1:
            raise AnalysisLimit("fixture context overflow")
        calls.append(batch[0]["index"])
        return {"comment_labels": [{"index": batch[0]["index"], "kind": "question"}]}

    with Session() as db:
        _, source = source_case(db)
        source.content = {**source.content, "comment_texts": ["தமிழ் question"] * 7}
        result = analyze_comments(db, source, {}, analyzer)
        assert calls == list(range(7))
        assert [c["index"] for c in result["comment_labels"]] == list(range(7))


def test_new_metrics_export_and_submission_erasure_include_analysis_jobs(client, auth):
    from app.db import Submission, ResearchCorrection

    user_id = client.get("/api/me", headers=auth).json()["id"]
    with Session() as db:
        submission = Submission(user_id=user_id, content={"caption": "isolated fixture"})
        db.add(submission)
        db.flush()
        submission_id = submission.id
        case, source = source_case(db, user_id)
        case.context = {"submission_id": submission_id}
        db.add(
            ResearchCorrection(
                user_id=user_id,
                source_id=source.id,
                role="caption",
                scope="fixture",
                original="fixture error",
                corrected="fixture correction",
                reason="isolated regression",
            )
        )
        source.analysis = {"caption": mark({"status": "observations_only"}, "fixture-key", "fixture-digest")}
        job_ids = []
        for kind, payload in [
            ("source_analysis", {"case_id": case.id, "source_id": source.id}),
            ("evaluation_compare", {"source_id": source.id, "user_id": user_id}),
            ("analysis", {"submission_id": submission_id}),
        ]:
            job = jobs.enqueue(db, kind, payload, "erase-fixture:" + kind)
            job.result = {"_performance": {"delivery_count": 1, "execution_seconds": 1}}
            job_ids.append(job.id)
        other = jobs.enqueue(db, "evaluation_compare", {"user_id": "unrelated-owner"}, "erase-private-other")
        other_id = other.id
        db.commit()
    exported = client.get("/api/me/export", headers=auth).json()
    assert len(exported["research_job_metrics"]) == 3
    assert "unrelated-owner" not in json.dumps(exported)
    response = client.delete(f"/api/submissions/{submission_id}", headers=auth)
    assert response.status_code == 200
    with Session() as db:
        assert all(db.get(Job, key) is None for key in job_ids)
        assert not list(db.scalars(select(ResearchCorrection).where(ResearchCorrection.user_id == user_id)))
        assert db.get(Job, other_id) is not None


def test_account_erasure_removes_standalone_timed_analysis(client, auth):
    from app.db import Submission

    user_id = client.get("/api/me", headers=auth).json()["id"]
    with Session() as db:
        sub = Submission(user_id=user_id, content={"caption": "isolated fixture"})
        db.add(sub)
        db.flush()
        job = jobs.enqueue(db, "analysis", {"submission_id": sub.id}, "standalone-erasure")
        ident = job.id
    assert client.delete("/api/me/data", headers=auth).status_code == 200
    with Session() as db:
        assert db.get(Job, ident) is None


def test_cancellation_during_gpu_wait_prevents_inference(client, monkeypatch):
    from app import local_models
    from app.db import Investigation

    monkeypatch.setattr("app.local_tokenizer.input_tokens", lambda *args: 50)
    monkeypatch.setattr(
        local_models, "inference_client", lambda: pytest.fail("Cancelled job reached inference")
    )
    with Session() as db:
        case, source = source_case(db)
        job = jobs.enqueue(db, "source_analysis", {"case_id": case.id, "source_id": source.id}, "gpu-cancel")
        case_id, job_id = case.id, job.id

    class Lane:
        released = False

        def acquire(self):
            with Session() as db:
                db.get(Investigation, case_id).state = "cancelled"
                db.commit()

        def release(self):
            self.released = True

    lane = Lane()
    monkeypatch.setattr(local_models, "GPU_LANE", lane)
    token = ACTIVE_JOB.set(job_id)
    try:
        with pytest.raises(Unavailable, match="cancelled"):
            local_models.local_chat("fixture", {"caption": "fixture"}, {})
    finally:
        ACTIVE_JOB.reset(token)
    assert lane.released


def test_benchmark_endpoint_requires_owned_independent_labels(client, monkeypatch):
    monkeypatch.setattr(settings(), "app_mode", "local")
    token = client.post("/api/auth/local").json()["access_token"]
    headers = {"Authorization": "Bearer " + token}
    with Session() as db:
        _, source = source_case(db, "local-operator")
        _, other = source_case(db, "private-other")
        own_id, other_id = source.id, other.id
    assert (
        client.post(
            f"/api/admin/evaluation/sources/{own_id}/benchmark", headers=headers, json={"role": "caption"}
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/api/admin/evaluation/sources/{other_id}/benchmark", headers=headers, json={"role": "caption"}
        ).status_code
        == 404
    )
