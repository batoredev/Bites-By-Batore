import asyncio
import json
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
import pytest
from sqlalchemy import select
from app.db import Session, ResearchSource, ResearchCorrection, Job, now
from app import research
from app.providers import Unavailable
from app.visual_places import signature, compare, fetch_reference
from app.branch_matching import branch_match, rank_google
from app.trust import review_statistics, calibration
from app.evaluation import measure, report, fingerprint, run_comparison
from app.comment_analysis import analyze_comments


def source_fixture(db, user="owner", code="quality", caption="Zircon Cafe Coimbatore", analysis=None):
    case = research.start_case(
        db,
        user,
        "Coimbatore cafes",
        seed_sources=[
            {"platform": "instagram", "url": f"https://www.instagram.com/p/{code}/", "caption": caption}
        ],
    )
    source = research.case_sources(db, case)[0]
    source.analysis = analysis or {
        "caption": {"status": "observations_only", "venue_candidates": [{"name": "Zircon Cafe"}]}
    }
    db.commit()
    return source


def test_local_visual_geometry_matches_transformed_scene_and_rejects_unrelated():
    import cv2
    import numpy as np

    rng = np.random.default_rng(41)
    image = rng.integers(0, 255, (500, 600), dtype=np.uint8)
    image = cv2.GaussianBlur(image, (3, 3), 0)
    for i in range(25):
        cv2.putText(
            image,
            f"SIGN{i}",
            (int(rng.integers(10, 450)), int(rng.integers(30, 480))),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            255,
            2,
        )
    matrix = cv2.getRotationMatrix2D((300, 250), 6, 0.95)
    transformed = cv2.warpAffine(image, matrix, (600, 500))
    encode = lambda im: cv2.imencode(".png", im)[1].tobytes()
    original, changed = signature(encode(image)), signature(encode(transformed))
    assert compare(original, changed)["matched"]
    unrelated = signature(encode(rng.integers(0, 255, (500, 600), dtype=np.uint8)))
    assert not compare(original, unrelated)["matched"]
    blank = signature(encode(np.zeros((500, 600), dtype=np.uint8)))
    assert not compare(original, blank)["matched"]
    with pytest.raises(ValueError):
        signature(b"not an image")


def test_reference_fetch_rejects_local_and_different_hosts(client):
    with Session() as db:
        with pytest.raises(Unavailable):
            fetch_reference(db, "https://127.0.0.1/image.png", "https://fixture.example/page")
        with pytest.raises(Unavailable):
            fetch_reference(db, "https://other.example/image.png", "https://fixture.example/page")


def test_branch_evidence_requires_more_than_name_and_exposes_conflicts():
    spot = SimpleNamespace(
        id="fixture",
        name="Zircon Cafe",
        area="RS Puram",
        data={"address": "No. 14 Fixture Road, RS Puram, Coimbatore"},
    )
    candidate = {"name": "Zircon Cafe", "address_clues": ["RS Puram"]}
    assert branch_match(candidate, spot)["status"] == "ambiguous_candidate"
    candidate["address_clues"] = [spot.data["address"]]
    assert branch_match(candidate, spot)["status"] == "corroborated_candidate"
    candidate["address_clues"] = ["No. 25 Fixture Road, RS Puram, Coimbatore"]
    assert branch_match(candidate, spot)["status"] == "conflicting"


def test_maps_ranking_excludes_other_cities_and_never_confirms():
    places = [
        {
            "id": "outside",
            "displayName": {"text": "Zircon Cafe"},
            "location": {"latitude": 13.08, "longitude": 80.27},
        },
        {
            "id": "near",
            "displayName": {"text": "Zircon Cafe"},
            "formattedAddress": "RS Puram Coimbatore",
            "location": {"latitude": 11.01, "longitude": 76.96},
        },
    ]
    result = rank_google({"name": "Zircon Cafe", "address_clues": ["RS Puram"]}, places)
    assert len(result) == 1 and result[0]["id"] == "near"
    assert result[0]["match_review"]["status"] == "candidate_only"


def test_trust_history_deduplicates_origins_and_has_uncertainty():
    rows = [
        SimpleNamespace(evidence_group="one", outcome="supported", created_at=now()),
        SimpleNamespace(
            evidence_group="one",
            outcome="refuted",
            created_at=(datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
        ),
        SimpleNamespace(
            evidence_group="old",
            outcome="supported",
            created_at=(datetime.now(timezone.utc) - timedelta(days=200)).isoformat(),
        ),
        SimpleNamespace(evidence_group="stale", outcome="outdated", created_at=now()),
    ]
    value = review_statistics(rows)
    assert value["judged_groups"] == 1 and value["outdated"] == 1
    assert (
        value["support_interval_95"][0] < 0.3 and value["calibration"] == "not_validated_on_future_outcomes"
    )
    assert review_statistics([])["observed_support_rate"] is None


def test_calibration_excludes_retrospective_scores_and_repeated_origins():
    values = [
        {
            "origin": "a",
            "predicted_at": "2026-01-01",
            "judged_at": "2026-02-01",
            "probability": 0.8,
            "outcome": 1,
        },
        {
            "origin": "b",
            "predicted_at": "2026-03-01",
            "judged_at": "2026-02-01",
            "probability": 1,
            "outcome": 1,
        },
    ]
    result = calibration(values + [values[0]])
    assert result["groups"] == 1 and result["brier_score"] == 0.04
    assert result["status"] == "insufficient_prospective_labels"


def test_comment_batches_resume_and_classify_all_collected_comments(client):
    with Session() as db:
        source = source_fixture(db)
        source.content = {**source.content, "comment_texts": [f"Fixture comment {i}" for i in range(12)]}
        calls = []

        def failing(db, role, content):
            calls.append(content["indexed_comments"][0]["index"])
            if len(calls) == 2:
                raise Unavailable("Fixture interruption")
            return {
                "comment_labels": [
                    {"index": i["index"], "kind": "question"} for i in content["indexed_comments"]
                ]
            }

        with pytest.raises(Unavailable):
            analyze_comments(db, source, {}, failing)

        def success(db, role, content):
            calls.append(content["indexed_comments"][0]["index"])
            return {
                "comment_labels": [
                    {"index": i["index"], "kind": "opinion"} for i in content["indexed_comments"]
                ]
            }

        result = analyze_comments(db, source, {}, success)
        assert calls == [0, 5, 5, 10]
        assert result["classified_count"] == 12 and result["counts"] == {"opinion": 7, "question": 5}
        assert result["venue_candidates"] == []


def test_unclassified_comments_are_explicit_unclear_not_invented(client):
    with Session() as db:
        source = source_fixture(db)
        source.content = {"comments": "One comment\nAnother comment"}
        result = analyze_comments(
            db, source, {}, lambda *a: {"comment_labels": [{"index": 99, "kind": "promotion"}]}
        )
        assert result["counts"] == {"unclear": 2}


def test_public_reply_extraction_is_bound_to_post_and_visible_text():
    from app.browser_sources import extract_public_data

    data = {
        "code": "target",
        "media_type": 2,
        "comments_connection": {
            "edges": [
                {
                    "node": {
                        "id": "parent",
                        "text": "Parent question",
                        "edge_threaded_comments": {
                            "edges": [
                                {"node": {"id": "reply", "text": "Visible reply"}},
                                {"node": {"id": "hidden", "text": "Hidden reply"}},
                            ]
                        },
                    }
                }
            ]
        },
    }
    result = extract_public_data([data], "target", "Parent question Visible reply", 100)
    assert result["comment_texts"] == ["Parent question", "Visible reply"]
    assert "Hidden reply" not in json.dumps(result)


def test_public_comment_controls_only_expand_exact_post_without_network():
    from playwright.async_api import async_playwright
    from app.browser_sources import expand_visible_comments

    async def run():
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.route("**/*", lambda route: route.abort())
            await page.set_content(
                '<article><a href="/p/target/">Post</a><button onclick="this.textContent=\'Done\';document.getElementById(\'reply\').hidden=false">View replies</button><span id="reply" hidden>Reply text</span></article><article><a href="/p/other/">Other</a><button onclick="throw Error(\'must not click\')">View replies</button></article>'
            )
            result = await expand_visible_comments(page, "target", 3)
            assert result["expanded_controls"] == 1 and await page.locator("#reply").is_visible()
            await browser.close()

    asyncio.run(run())


def test_evaluation_metrics_do_not_confuse_missing_predictions_with_success():
    prediction = {
        "venue_candidates": [{"name": "Zircon Cafe"}, {"name": "False venue"}],
        "transcript": "we ate food",
        "visual_text": "CAFE",
        "comment_labels": [],
    }
    value = measure(
        prediction,
        {
            "evaluate_names": True,
            "expected_names": ["Zircon Cafe"],
            "transcript": "we ate good food",
            "visual_text": "CAFE",
            "comment_labels": {"0": "question"},
        },
    )
    assert value["names"] == {"tp": 1, "fp": 1, "fn": 0, "exact_set": False}
    assert value["transcript"]["rate"] == 0.25 and value["visual_text"]["rate"] == 0
    assert value["comments"]["correct"] == 0


def test_labels_require_original_review_and_remain_owner_scoped(client, auth):
    user = client.get("/api/me", headers=auth).json()["id"]
    with Session() as db:
        source = source_fixture(db, user)
        other = source_fixture(db, "someone-else", "other")
        sid, oid = source.id, other.id
    label = {
        "role": "caption",
        "language": "en",
        "evaluate_names": True,
        "expected_names": ["Zircon Cafe"],
        "source_checked": False,
        "note": "Independent fixture review only",
    }
    assert (
        client.post(f"/api/admin/evaluation/sources/{sid}/label", headers=auth, json=label).status_code == 422
    )
    label["source_checked"] = True
    assert client.post(
        f"/api/admin/evaluation/sources/{sid}/label", headers=auth,
        json={**label, "comment_labels": {"0": "question"}},
    ).status_code == 422
    assert client.post(
        f"/api/admin/evaluation/sources/{sid}/label", headers=auth,
        json={**label, "transcript": "Wrong modality"},
    ).status_code == 422
    assert (
        client.post(f"/api/admin/evaluation/sources/{oid}/label", headers=auth, json=label).status_code == 404
    )
    assert (
        client.post(f"/api/admin/evaluation/sources/{sid}/label", headers=auth, json=label).status_code == 200
    )
    report = client.get("/api/admin/evaluation", headers=auth).json()
    assert report["labelled_tasks"] == 1 and report["status"] == "needs_evaluation"
    assert all(s["id"] != oid for s in report["sources"])
    exported = client.get("/api/me/export", headers=auth).json()
    assert "evaluation_labels" in json.dumps(exported)
    with Session() as db:
        db.add(
            Job(
                key="eval-fixture",
                kind="evaluation_compare",
                payload={"source_id": sid, "user_id": user, "role": "caption"},
            )
        )
        db.commit()
    assert client.delete("/api/me/data", headers=auth).status_code == 200
    with Session() as db:
        assert db.get(ResearchSource, sid) is None and db.get(ResearchSource, oid)
        assert not db.scalar(select(Job).where(Job.key == "eval-fixture"))


def test_same_source_correction_cannot_prove_learning(client):
    with Session() as db:
        source = source_fixture(db)
        source.analysis = {
            **source.analysis,
            "evaluation_labels": {
                "caption": {
                    "input_fingerprint": fingerprint(source),
                    "origin": source.canonical_url,
                    "evaluate_names": True,
                    "expected_names": ["Zircon Cafe"],
                }
            },
        }
        db.add(
            ResearchCorrection(
                user_id="owner",
                source_id=source.id,
                role="caption",
                scope="Zircon",
                original="Wrong",
                corrected="Zircon Cafe",
                reason="Fixture scope correction",
            )
        )
        db.commit()
        with pytest.raises(Unavailable, match="independent correction"):
            run_comparison(db, "owner", source.id, "caption")


def test_evaluation_has_no_accuracy_without_labels(client):
    with Session() as db:
        result = report(db, "owner")
        assert result["name_precision"] is None and result["name_recall"] is None
        assert result["blockers"] and result["labelled_tasks"] == 0
