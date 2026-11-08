"""Reuse only identical, versioned, owner-private interpretation. Never renew facts."""

import hashlib
import json
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy import or_
from .db import Investigation, ResearchSource, now
from .config import settings
from .performance import span

PIPELINE_VERSION = "2026-11-08-coverage-v4"


def model_digest():
    import httpx
    from .local_models import endpoint, inference_client

    if not settings().analysis_reuse_enabled:
        return None
    try:
        response = inference_client().get(endpoint() + "/api/tags", timeout=2)
        response.raise_for_status()
        return next(
            (
                m["digest"]
                for m in response.json().get("models", [])
                if m.get("name") == settings().ollama_model
            ),
            None,
        )
    except (httpx.HTTPError, ValueError, KeyError):
        return None  # No model identity means no cross-source cache hit.


def analysis_key(role, data, content, digest=None):
    cfg = settings()
    media = content.get("media", {})
    media_hash = (
        hashlib.sha256(media["base64"].encode()).hexdigest()
        if media.get("base64")
        else content.get("media_receipt", {}).get("sha256")
    )
    # Prefer the persisted decoded-byte receipt so pre/post-cleanup keys agree.
    media_hash = content.get("media_receipt", {}).get("sha256") or media_hash
    value = {
        "pipeline": PIPELINE_VERSION,
        "role": role,
        "data": data,
        "model": cfg.ollama_model,
        "digest": digest,
        "gpu_layers": cfg.ollama_gpu_layers,
        "frames": cfg.media_max_frames,
        "seconds": cfg.media_max_seconds,
        "speech_model": cfg.whisper_model,
        "media": media_hash if role == "video" else None,
    }
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def reusable(db, case, source, role, key, digest):
    if not settings().analysis_reuse_enabled or not digest:
        return None
    origin = source.content.get("content_fingerprint")
    same_origin = ResearchSource.canonical_url == source.canonical_url
    if origin:
        same_origin = or_(same_origin, ResearchSource.content["content_fingerprint"].as_string() == origin)
    rows = list(
        db.scalars(
            select(ResearchSource)
            .join(Investigation, ResearchSource.case_id == Investigation.id)
            .where(Investigation.user_id == case.user_id, same_origin)
        )
    )
    # An evaluation origin must not borrow another case's labelled or cached output.
    if any(s.analysis.get("evaluation_labels") for s in rows):
        return None
    for other in rows:
        if other.id == source.id or other.canonical_url != source.canonical_url:
            continue
        result = other.analysis.get(role, {})
        metadata = result.get("reuse", {})
        at = metadata.get("computed_at")
        if (
            result.get("status") != "observations_only"
            or result.get("early_exit")
            or metadata.get("key") != key
            or not at
        ):
            continue
        try:
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(at)).total_seconds()
        except (ValueError, TypeError):
            continue
        if not 0 <= age <= 86400:
            continue
        origin = db.get(ResearchSource, metadata.get("from_source_id", other.id))
        if not origin or origin not in rows:
            continue
        with span("analysis_cache_hit"):
            output = {
                **result,
                "reuse": {
                    **metadata,
                    "reused": True,
                    "from_source_id": origin.id,
                    "note": "Identical private interpretation; not independent evidence or a new fact approval",
                },
            }
            if role == "video" and other.content.get("machine_transcript"):
                output["_transcription"] = {
                    "text": other.content.get("transcript", ""),
                    "segments": other.content.get("speech_segments", []),
                    "language": other.content.get("speech_language"),
                    "model": other.content.get("speech_model"),
                }
            return output
    return None


def valid_result(result, key):
    metadata = result.get("reuse", {})
    if result.get("status") != "observations_only" or result.get("early_exit") or metadata.get("key") != key:
        return False
    try:
        age = (
            datetime.now(timezone.utc) - datetime.fromisoformat(metadata.get("computed_at", ""))
        ).total_seconds()
        return 0 <= age <= 86400
    except (ValueError, TypeError):
        return False


def mark(result, key, digest):
    return {
        **result,
        "reuse": {
            "key": key,
            "model_digest": digest,
            "computed_at": now(),
            "pipeline": PIPELINE_VERSION,
            "reused": False,
        },
    }
