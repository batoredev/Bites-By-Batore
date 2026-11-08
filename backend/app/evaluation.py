"""Owner-scoped human labels and leakage-aware local comparisons. No invented gold labels."""

import hashlib
import json
from datetime import datetime, timezone, timedelta
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from .auth import admin_user
from .db import ResearchSource, Investigation, ResearchCorrection, get_db, now
from .spot_identity import name_key
from .config import settings
from .providers import Unavailable

router = APIRouter(prefix="/api/admin/evaluation")


def fingerprint(source):
    return hashlib.sha256(
        json.dumps(
            {k: source.content.get(k) for k in ("caption", "comments", "comment_texts", "transcript")},
            sort_keys=True,
        ).encode()
    ).hexdigest()


def source_rows(db, user_id):
    return list(
        db.scalars(
            select(ResearchSource)
            .join(Investigation, ResearchSource.case_id == Investigation.id)
            .where(Investigation.user_id == user_id)
        )
    )


def owned_source(db, user_id, source_id):
    source = db.get(ResearchSource, source_id)
    case = db.get(Investigation, source.case_id) if source else None
    if not case or case.user_id != user_id:
        raise HTTPException(404, "Source not found")
    return source


def edit_distance(a, b):
    previous = list(range(len(b) + 1))
    for i, left in enumerate(a, 1):
        row = [i]
        for j, right in enumerate(b, 1):
            row.append(min(row[-1] + 1, previous[j] + 1, previous[j - 1] + (left != right)))
        previous = row
    return previous[-1]


def measure(prediction, label):
    result = {}
    if label.get("evaluate_names"):
        expected = {name_key(n) for n in label.get("expected_names", [])}
        observed = {name_key(n["name"]) for n in prediction.get("venue_candidates", [])}
        tp, fp, fn = len(expected & observed), len(observed - expected), len(expected - observed)
        result["names"] = {"tp": tp, "fp": fp, "fn": fn, "exact_set": expected == observed}
    for key in ("transcript", "visual_text"):
        reference = label.get(key)
        if reference is not None:
            observed = prediction.get(key, "")
            a, b = name_key(reference), name_key(observed)
            if key == "transcript":
                a, b = a.split(), b.split()
            result[key] = {
                "errors": edit_distance(a, b),
                "reference_units": len(a),
                "rate": edit_distance(a, b) / len(a) if a else (0 if not b else None),
            }
    if label.get("comment_labels"):
        predicted = {str(c["index"]): c["kind"] for c in prediction.get("comment_labels", [])}
        result["comments"] = {
            "correct": sum(predicted.get(str(i)) == kind for i, kind in label["comment_labels"].items()),
            "total": len(label["comment_labels"]),
        }
    return result


def snapshot(source, role):
    prediction = dict(source.analysis.get(role, {}))
    if role == "video":
        prediction["transcript"] = source.content.get("transcript", "")[:2000]
        prediction["visual_text"] = " ".join(
            o["verbatim_text"]
            for o in prediction.get("observations", [])
            if o.get("basis") == "visual" and o.get("verbatim_text")
        )[:2000]
    return prediction


class Label(BaseModel):
    role: Literal["caption", "comments", "video"]
    language: str = Field(min_length=2, max_length=30)
    evaluate_names: bool = False
    expected_names: list[str] = Field(default_factory=list, max_length=30)
    transcript: str | None = Field(default=None, max_length=2000)
    visual_text: str | None = Field(default=None, max_length=2000)
    comment_labels: dict[
        int,
        Literal["firsthand_claim", "question", "promotion", "correction", "opinion", "unrelated", "unclear"],
    ] = Field(default_factory=dict)
    source_checked: bool
    note: str = Field(min_length=10, max_length=1000)


@router.post("/sources/{source_id}/label")
def save_label(source_id: str, data: Label, user=Depends(admin_user), db=Depends(get_db)):
    source = owned_source(db, user.id, source_id)
    if not data.source_checked or not (
        data.evaluate_names
        or data.transcript is not None
        or data.visual_text is not None
        or data.comment_labels
    ):
        raise HTTPException(422, "Inspect the original source and label at least one evaluation task")
    if (
        any(len(n) < 2 or len(n) > 150 for n in data.expected_names)
        or len(data.comment_labels) > 100
        or any(i < 0 or i >= 100 for i in data.comment_labels)
    ):
        raise HTTPException(422, "Invalid name or comment label")
    prediction = snapshot(source, data.role)
    if (data.transcript is not None or data.visual_text is not None) and data.role != "video":
        raise HTTPException(422, "Transcript and visual-text labels require video analysis")
    if data.comment_labels:
        comments = source.content.get("comment_texts") or str(source.content.get("comments", "")).splitlines()
        count = len([c for c in comments if str(c).strip()][:100])
        if data.role != "comments" or any(i >= count for i in data.comment_labels):
            raise HTTPException(422, "Label only available comments in the comments modality")
    if prediction.get("status") != "observations_only":
        raise HTTPException(409, "This modality has no completed prediction to evaluate")
    group = source.content.get("content_fingerprint") or source.canonical_url
    split = "holdout" if int(hashlib.sha256(group.encode()).hexdigest()[:8], 16) % 5 == 0 else "development"
    label = {
        **data.model_dump(mode="json"),
        "reviewer": user.id,
        "labelled_at": now(),
        "origin": group,
        "split": split,
        "input_fingerprint": fingerprint(source),
        "prediction": prediction,
        "label_origin": "operator",
        "metrics": measure(prediction, data.model_dump(mode="json")),
    }
    source.analysis = {
        **source.analysis,
        "evaluation_labels": {**source.analysis.get("evaluation_labels", {}), data.role: label},
    }
    db.commit()
    return {"saved": True, "split": split, "metrics": label["metrics"], "publication": False}


@router.delete("/sources/{source_id}/labels")
def remove_labels(source_id: str, user=Depends(admin_user), db=Depends(get_db)):
    source = owned_source(db, user.id, source_id)
    source.analysis = {
        k: v
        for k, v in source.analysis.items()
        if k not in {"evaluation_labels", "evaluation_comparisons", "performance_comparisons"}
    }
    db.commit()
    return {"removed": True}


def report(db, user_id):
    from .trust import calibration

    rows = source_rows(db, user_id)
    from .db import IdentifiedSpot

    spots = list(db.scalars(select(IdentifiedSpot).where(IdentifiedSpot.user_id == user_id)))
    active_spots = [s for s in spots if s.status not in {"merged", "quarantined", "rejected"}]
    coverage = {
        "sources_found": len(rows),
        "sources_with_publication_dates": sum(bool(s.content.get("published_at")) for s in rows),
        "sources_with_video_analysis": sum(
            s.analysis.get("video", {}).get("status") == "observations_only" for s in rows
        ),
        "classified_comments": sum(
            len(s.analysis.get("comments", {}).get("comment_labels", [])) for s in rows
        ),
        "reported_comments": sum(s.content.get("comments_count", 0) or 0 for s in rows),
        "active_spots": len(active_spots),
        "maps_reviewed": sum(bool(s.data.get("maps_identity", {}).get("confirmed_by")) for s in active_spots),
        "indexed_reference_images": sum(len(s.data.get("visual_references", [])) for s in active_spots),
        "missing_menu": sum(
            not s.data.get("menu_links")
            and not any(o.get("price_inr") is not None for o in s.data.get("offerings", []))
            for s in active_spots
        ),
        "missing_hours": sum(not s.data.get("hours") for s in active_spots),
        "missing_vibes": sum(not s.data.get("vibes") for s in active_spots),
        "limitation": "Counts describe collected records and can include repeated posts across investigations. They do not establish exhaustive city or Instagram coverage.",
    }
    unique = {}
    cutoff = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
    for source in rows:
        for role, label in source.analysis.get("evaluation_labels", {}).items():
            if label.get("label_origin") == "operator" and label.get("labelled_at", "") >= cutoff:
                key = (label["origin"], role)
                if key not in unique or label["labelled_at"] > unique[key]["labelled_at"]:
                    unique[key] = label
    labels = list(unique.values())
    held = [l for l in labels if l["split"] == "holdout"]
    names = [l["metrics"]["names"] for l in held if "names" in l["metrics"]]
    tp, fp, fn = (sum(x[k] for x in names) for k in ("tp", "fp", "fn"))
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    languages = {
        language: sum(l["language"] == language for l in held) for language in {l["language"] for l in held}
    }
    blockers = []
    if len({l["origin"] for l in held}) < 30:
        blockers.append("Need at least 30 independently grouped held-out sources")
    if languages.get("en", 0) < 10 or languages.get("ta", 0) < 10:
        blockers.append("Need held-out English and Tamil coverage (10 labels each)")
    if len(names) < 20 or precision is None or recall is None or precision < 0.95 or recall < 0.9:
        blockers.append("Venue-name precision/recall gates are not met")
    for metric, threshold in (("transcript", 0.2), ("visual_text", 0.1)):
        samples = [l["metrics"][metric] for l in held if metric in l["metrics"]]
        units = sum(s["reference_units"] for s in samples)
        if len(samples) < 10 or not units or sum(s["errors"] for s in samples) / units > threshold:
            blockers.append(metric + " evaluation gate is not met")
    comments = [l["metrics"]["comments"] for l in held if "comments" in l["metrics"]]
    total = sum(c["total"] for c in comments)
    if total < 100 or sum(c["correct"] for c in comments) / max(1, total) < 0.85:
        blockers.append("Comment classification needs 100 held-out labels and at least 85% agreement")
    return {
        "collection_coverage": coverage,
        "creator_calibration": calibration(
            [s.analysis["prospective_assessment"] for s in rows if s.analysis.get("prospective_assessment")]
        ),
        "labelled_tasks": len(labels),
        "heldout_tasks": len(held),
        "languages": languages,
        "name_precision": precision,
        "name_recall": recall,
        "blockers": blockers,
        "status": "needs_evaluation" if blockers else "provisional_gates_met",
        "threshold_basis": "Provisional engineering thresholds; user outcomes and representative sampling still required",
        "comparisons": [
            {"source_id": s.id, "results": s.analysis["evaluation_comparisons"]}
            for s in rows
            if s.analysis.get("evaluation_comparisons")
        ],
        "performance_comparisons": [
            {"source_id": s.id, "results": s.analysis["performance_comparisons"]}
            for s in rows
            if s.analysis.get("performance_comparisons")
        ],
        "sources": [
            {
                "id": s.id,
                "url": s.canonical_url,
                "roles": [
                    r
                    for r in ("caption", "comments", "video")
                    if s.analysis.get(r, {}).get("status") == "observations_only"
                ],
                "labels": list(s.analysis.get("evaluation_labels", {})),
            }
            for s in rows
        ],
    }


@router.get("")
def evaluation_report(user=Depends(admin_user), db=Depends(get_db)):
    return report(db, user.id)


@router.get("/sources/{source_id}")
def source_for_review(source_id: str, user=Depends(admin_user), db=Depends(get_db)):
    source = owned_source(db, user.id, source_id)
    comments = source.content.get("comment_texts") or str(source.content.get("comments", "")).splitlines()
    return {
        "id": source.id,
        "url": source.canonical_url,
        "comment_texts": [str(c).strip()[:1000] for c in comments if str(c).strip()][:100],
        "predictions": {r: snapshot(source, r) for r in ("caption", "comments", "video")},
        "content_available": {r: bool(source.content.get(r)) for r in ("caption", "comments", "transcript")},
    }


class Comparison(BaseModel):
    role: Literal["caption", "comments"]


@router.post("/sources/{source_id}/benchmark")
def benchmark_source(source_id: str, data: Comparison, user=Depends(admin_user), db=Depends(get_db)):
    from .jobs import enqueue

    source = owned_source(db, user.id, source_id)
    label = source.analysis.get("evaluation_labels", {}).get(data.role)
    if settings().app_mode != "local" or not label or label.get("input_fingerprint") != fingerprint(source):
        raise HTTPException(
            409, "Local benchmark requires independent labels for the unchanged retained input"
        )
    job = enqueue(
        db,
        "evaluation_compare",
        {"source_id": source.id, "user_id": user.id, "role": data.role, "mode": "performance"},
        f"performance:{source.id}:{data.role}:{now()}",
        priority=20,
    )
    return {"job_id": job.id, "state": job.state, "publication": False}


def run_benchmark(db, user_id, source_id, role):
    """Compare a saved independently labelled prediction to fresh uncached inference."""
    from .analysts import analyze
    from .learning import relevant_examples
    from .analysis_reuse import PIPELINE_VERSION, model_digest
    from .performance import Trace, ACTIVE_TRACE
    from .providers import renew_job
    from types import SimpleNamespace

    source = owned_source(db, user_id, source_id)
    label = source.analysis.get("evaluation_labels", {}).get(role)
    if not label or fingerprint(source) != label["input_fingerprint"] or not source.content.get(role):
        raise Unavailable("Labelled source input expired or changed; benchmark cannot run")
    baseline = label["prediction"]
    examples = relevant_examples(db, user_id, source, role)
    if sorted(e["correction_id"] for e in examples) != sorted(baseline.get("learning_example_ids", [])):
        raise Unavailable("Correction context changed since baseline; save a new independent baseline")
    content = {"source_url": source.canonical_url, "reviewed_examples": examples}
    keys = ["comments", "comments_coverage"] if role == "comments" else ["caption", "transcript"]
    content.update({k: source.content[k] for k in keys if k in source.content})
    if role == "caption" and source.content.get("machine_transcript"):
        content.pop("transcript", None)
    digest = model_digest()
    trace = Trace()
    token = ACTIVE_TRACE.set(trace)
    try:
        if role == "comments":
            from .comment_analysis import analyze_comments

            prediction = analyze_comments(
                db,
                SimpleNamespace(content=source.content, analysis={}),
                content,
                analyze,
                context_version=digest,
            )
        else:
            prediction = analyze(db, role, content)
    finally:
        ACTIVE_TRACE.reset(token)
    renew_job(db)
    db.refresh(source)
    if (
        source.analysis.get("evaluation_labels", {}).get(role) != label
        or fingerprint(source) != label["input_fingerprint"]
    ):
        raise Unavailable("Input or label changed during benchmark; result discarded")
    if relevant_examples(db, user_id, source, role) != examples:
        raise Unavailable("Correction context changed during benchmark; result discarded")
    result = {
        "at": now(),
        "pipeline": PIPELINE_VERSION,
        "model": settings().ollama_model,
        "model_digest": digest,
        "input_fingerprint": label["input_fingerprint"],
        "baseline_metrics": measure(baseline, label),
        "current_metrics": measure(prediction, label),
        "execution": trace.summary(),
        "baseline_execution_seconds": None,
        "baseline_model": baseline.get("model"),
        "scope": "Fresh uncached local inference versus a saved human-labelled prediction. Historical baseline wall time is unavailable; no speedup or general accuracy guarantee. Video/branch and sustained-load evaluation remain separate.",
    }
    source.analysis = {
        **source.analysis,
        "performance_comparisons": {**source.analysis.get("performance_comparisons", {}), role: result},
    }
    db.commit()
    return result


@router.post("/sources/{source_id}/compare")
def compare_corrections(source_id: str, data: Comparison, user=Depends(admin_user), db=Depends(get_db)):
    from .jobs import enqueue

    source = owned_source(db, user.id, source_id)
    if settings().app_mode != "local":
        raise HTTPException(409, "Correction comparison runs in local mode")
    if data.role not in source.analysis.get("evaluation_labels", {}):
        raise HTTPException(409, "Label the source before requesting a comparison")
    job = enqueue(
        db,
        "evaluation_compare",
        {"source_id": source.id, "user_id": user.id, "role": data.role},
        f"evaluation:{source.id}:{data.role}:{now()}",
        priority=20,
    )
    return {"job_id": job.id, "state": job.state}


def run_comparison(db, user_id, source_id, role):
    from .analysts import analyze
    from .learning import relevant_examples

    source = owned_source(db, user_id, source_id)
    label = source.analysis.get("evaluation_labels", {}).get(role)
    if not label or fingerprint(source) != label["input_fingerprint"] or not source.content.get(role):
        raise Unavailable(
            "Labelled input expired or changed; fetch and label the exact current source before comparison"
        )
    examples = relevant_examples(db, user_id, source, role)
    allowed = []
    for example in examples:
        correction = db.get(ResearchCorrection, example["correction_id"])
        origin = db.get(ResearchSource, correction.source_id) if correction else None
        if (
            origin
            and origin.canonical_url != source.canonical_url
            and (origin.content.get("content_fingerprint") or origin.canonical_url) != label["origin"]
        ):
            allowed.append(example)
    if not allowed:
        raise Unavailable(
            "No independent correction examples are available; same-source labels cannot prove learning"
        )
    content = {role: source.content[role], "source_url": source.canonical_url}
    if role == "comments":
        from types import SimpleNamespace
        from .comment_analysis import analyze_comments

        baseline = analyze_comments(
            db, SimpleNamespace(content=source.content, analysis={}), content, analyze
        )
        corrected = analyze_comments(
            db,
            SimpleNamespace(content=source.content, analysis={}),
            {**content, "reviewed_examples": allowed},
            analyze,
        )
    else:
        baseline = analyze(db, role, content)
        corrected = analyze(db, role, {**content, "reviewed_examples": allowed})
    db.refresh(source)
    if (
        source.analysis.get("evaluation_labels", {}).get(role) != label
        or fingerprint(source) != label["input_fingerprint"]
    ):
        raise Unavailable("Evaluation label or input changed during comparison; result discarded")
    for example in allowed:
        correction = db.get(ResearchCorrection, example["correction_id"], populate_existing=True)
        if not correction or not correction.active:
            raise Unavailable("A correction was revoked during comparison; result discarded")
    result = {
        "at": now(),
        "model": settings().ollama_model,
        "baseline": measure(baseline, label),
        "with_corrections": measure(corrected, label),
        "example_ids": [e["correction_id"] for e in allowed],
        "input_fingerprint": label["input_fingerprint"],
        "scope": "One fixed-input comparison, not a trained model or general improvement claim",
    }
    source.analysis = {
        **source.analysis,
        "evaluation_comparisons": {**source.analysis.get("evaluation_comparisons", {}), role: result},
    }
    db.commit()
    return result
