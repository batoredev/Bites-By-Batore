"""Local-only inference. No cloud fallback and no implicit model downloads."""

import base64
import json
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse
import httpx
import threading
import atexit
from .performance import span, model_metrics
from .analysis_inputs import AnalysisLimit
from .config import ROOT, settings
from .providers import Unavailable

GPU_LANE = threading.BoundedSemaphore(1)


@lru_cache(maxsize=1)
def inference_client():
    client = httpx.Client(timeout=240, trust_env=False)
    atexit.register(client.close)
    return client


def endpoint():
    value = settings().ollama_url.rstrip("/")
    parsed = urlparse(value)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"127.0.0.1", "::1"}
        or parsed.username
        or parsed.password
        or parsed.path
    ):
        raise Unavailable("Ollama must use a loopback IP, without credentials or a path")
    if "cloud" in settings().ollama_model.lower():
        raise Unavailable("Cloud models are disabled for local research")
    return value


def local_chat(prompt, content, schema, frames=None):
    bases = ["visual", "inference"] if frames else ["caption", "transcript", "inference"]
    if "comments" in content:
        bases = ["comment", "inference"]
    if frames and content.get("audio", {}).get("text"):
        bases.append("speech")
    # Small local models handle a compact, fully specified contract more reliably
    # than the broad hosted-model schema with arbitrary nested fact values.
    candidate = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "minLength": 2, "maxLength": 150},
            "address_clues": {"type": "array", "items": {"type": "string", "maxLength": 180}, "maxItems": 3},
            "dish_or_activity": {"type": "string", "maxLength": 200},
            "price_claim": {"type": "string", "maxLength": 200},
        },
        "required": ["name", "address_clues", "dish_or_activity", "price_claim"],
        "additionalProperties": False,
    }
    observation = {
        "type": "object",
        "properties": {
            "text": {"type": "string", "maxLength": 400},
            "basis": {"enum": bases},
            "timestamp_seconds": {"type": ["number", "null"], "minimum": 0, "maximum": 86400}
            if frames
            else {"type": "null"},
        },
        "required": ["text", "basis", "timestamp_seconds"],
        "additionalProperties": False,
    }
    compact = {
        "type": "object",
        "properties": {
            "summary": {"type": "string", "maxLength": 400},
            "languages": {"type": "array", "items": {"type": "string"}, "maxItems": 3},
            "observations": {"type": "array", "items": observation, "maxItems": 3},
            "venue_candidates": {
                "type": "array",
                "items": candidate,
                **({"maxItems": 0} if "comments" in content else {}),
            },
            "unknowns": {"type": "array", "items": {"type": "string", "maxLength": 200}, "maxItems": 3},
        },
        "required": ["summary", "languages", "observations", "venue_candidates", "unknowns"],
        "additionalProperties": False,
    }
    if frames:
        observation["properties"]["verbatim_text"] = {"type": ["string", "null"], "maxLength": 400}
        observation["required"].append("verbatim_text")
    if frames:
        compact["properties"]["followup_seconds"] = {
            "type": "array",
            "items": {"type": "number", "minimum": 0, "maximum": max(f["seconds"] for f in frames) + 0.15},
            "maxItems": 2,
        }
        compact["required"].append("followup_seconds")
    if content.get("indexed_comments"):
        compact["properties"]["comment_labels"] = {
            "type": "array",
            "maxItems": len(content["indexed_comments"]),
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer", "enum": [c["index"] for c in content["indexed_comments"]]},
                    "kind": {
                        "enum": [
                            "firsthand_claim",
                            "question",
                            "promotion",
                            "correction",
                            "opinion",
                            "unrelated",
                            "unclear",
                        ]
                    },
                    "aspect": {"enum": ["food", "service", "price", "location", "hours", "other"]},
                    "claim": {"type": "string", "maxLength": 120},
                },
                "required": ["index", "kind", "aspect", "claim"],
                "additionalProperties": False,
            },
        }
        compact["required"].append("comment_labels")
    prompt = (
        prompt.split(" Schema: ")[0]
        + " Return concise JSON, retaining every explicitly supported venue. Do not drop names to meet a word count. Summarize descriptions instead of copying hashtags. Preserve uncertainty, negation and branch distinctions. Use empty arrays when no evidence exists. Never infer prices. Timestamp means seconds within the supplied clip, never a calendar date. Text-only observations use null timestamps. Use this exact structure: "
        + json.dumps(compact)
    )
    images = (frames or [])[:4]
    serialized = json.dumps(content, ensure_ascii=False)
    if len(serialized) > 18000:
        raise AnalysisLimit("Evidence needs segmented analysis; no input was truncated")
    message = {"role": "user", "content": serialized}
    if images:
        message["images"] = [f["base64"] for f in images]
        message["content"] += "\nFrame times (seconds, in image order): " + str(
            [f["seconds"] for f in images]
        )
    from .local_tokenizer import input_tokens

    context = 8192 if images else 4096
    # Reserve output, chat-template overhead and conservative visual token space.
    with span("token_budget"):
        required = input_tokens(prompt, message["content"]) + 256 + 1024 * len(images) + 1536
    if required > context:
        raise AnalysisLimit("Evidence exceeds the verified context budget; split rather than truncate")
    try:
        with span("gpu_queue_wait"):
            GPU_LANE.acquire()
        try:
            from .providers import ACTIVE_JOB, renew_job

            if ACTIVE_JOB.get():
                from .db import Session

                with Session() as guard:
                    renew_job(guard)  # Cancellation may have arrived while waiting for the GPU.
            with span("local_model"):
                response = inference_client().post(
                    endpoint() + "/api/chat",
                    json={
                        "model": settings().ollama_model,
                        "stream": False,
                        "think": False,
                        "format": compact,
                        "keep_alive": settings().ollama_keep_alive,
                        "options": {
                            "temperature": 0,
                            "num_ctx": context,
                            "num_predict": 1536,
                            "num_gpu": settings().ollama_gpu_layers,
                        },
                        "messages": [{"role": "system", "content": prompt}, message],
                    },
                )
                response.raise_for_status()
                result = response.json()
                model_metrics(result)
                if result.get("done_reason") == "length":
                    raise AnalysisLimit(
                        "Local analysis exceeded output limit; split the evidence instead of discarding it"
                    )
                return result["message"]["content"]
        finally:
            GPU_LANE.release()
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        raise Unavailable("Local model unavailable or timed out; check Ollama and installed model") from exc


@lru_cache(maxsize=1)
def speech_model():
    from faster_whisper import WhisperModel

    try:
        return WhisperModel(
            settings().whisper_model,
            device="cpu",
            compute_type="int8",
            cpu_threads=4,
            download_root=str(ROOT / "data" / "models"),
            local_files_only=True,
        )
    except Exception as exc:
        raise Unavailable("Local speech model is not installed; run scripts/setup-local.ps1") from exc


def transcribe(media):
    from imageio_ffmpeg import get_ffmpeg_exe

    cfg = settings()
    data = base64.b64decode(media["base64"], validate=True)
    if len(data) > cfg.max_media_mb * 1024 * 1024:
        raise Unavailable("Media exceeds local transcription limit")
    with tempfile.TemporaryDirectory(prefix="batore-audio-") as folder:
        source, target = Path(folder) / "input.video", Path(folder) / "speech.wav"
        source.write_bytes(data)
        try:
            result = subprocess.run(
                [
                    cfg.ffmpeg_binary or get_ffmpeg_exe(),
                    "-nostdin",
                    "-loglevel",
                    "error",
                    "-protocol_whitelist",
                    "file,pipe",
                    "-i",
                    str(source),
                    "-t",
                    str(min(cfg.media_max_seconds, 300)),
                    "-vn",
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    "-y",
                    str(target),
                ],
                capture_output=True,
                timeout=30,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if result.returncode:
                raise Unavailable("No decodable audio track was available")
            try:
                segments, info = speech_model().transcribe(str(target), beam_size=1, vad_filter=True)
                rows = [{"start": s.start, "end": s.end, "text": s.text.strip()} for s in segments]
            except Unavailable:
                raise
            except Exception as exc:
                raise Unavailable(
                    "Local speech decoding or transcription failed; check the pinned runtime"
                ) from exc
            return {
                "language": info.language,
                "language_probability": info.language_probability,
                "segments": rows,
                "text": "\n".join(s["text"] for s in rows),
                "model": cfg.whisper_model,
                "machine_transcript": True,
            }
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise Unavailable("Local audio extraction failed") from exc
