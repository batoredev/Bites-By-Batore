"""Checkpointed classification of every collected comment, without author profiling."""

import hashlib
import json
from .providers import renew_job
from .analysis_reuse import PIPELINE_VERSION
from .config import settings
from .performance import span
from .analysis_inputs import AnalysisLimit


def analyze_comments(db, source, content, analyzer, context_version=None):
    comments = source.content.get("comment_texts") or str(source.content.get("comments", "")).splitlines()
    comments = [str(c).strip()[:1000] for c in comments if str(c).strip()][:100]
    digest = hashlib.sha256(json.dumps(comments, ensure_ascii=False).encode()).hexdigest()
    saved = source.analysis.get("comment_batches", {})
    context = hashlib.sha256(
        json.dumps(
            {
                "content": {k: v for k, v in content.items() if k != "comments"},
                "pipeline": PIPELINE_VERSION,
                "model": context_version or settings().ollama_model,
            },
            sort_keys=True,
            ensure_ascii=False,
        ).encode()
    ).hexdigest()
    same_context = saved.get("context_hash") == context and (
        bool(context_version) or not settings().analysis_reuse_enabled
    )
    batches = list(saved.get("batches", [])) if same_context and saved.get("input_hash") == digest else []
    entries = dict(saved.get("entries", {})) if same_context and settings().analysis_reuse_enabled else {}

    def classify(batch):
        try:
            return analyzer(
                db,
                "comments",
                {**content, "comments": "\n".join(c["text"] for c in batch), "indexed_comments": batch},
            )
        except AnalysisLimit:
            if len(batch) == 1:
                raise  # One unclassifiable comment remains an explicit coverage gap.
            middle = len(batch) // 2
            parts = [classify(batch[:middle]), classify(batch[middle:])]
            return {
                "status": "observations_only",
                "venue_candidates": [],
                "languages": sorted({l for p in parts for l in p.get("languages", [])}),
                "observations": [o for p in parts for o in p.get("observations", [])],
                "comment_labels": [l for p in parts for l in p.get("comment_labels", [])],
                "coverage": [c for p in parts for c in p.get("coverage", [])],
            }

    for offset in range(len(batches) * 5, len(comments), 5):
        renew_job(db)
        batch = [{"index": i, "text": text} for i, text in enumerate(comments[offset : offset + 5], offset)]
        batch_key = hashlib.sha256(json.dumps(batch, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        result = entries.get(batch_key)
        if result is None:
            result = classify(batch)
        else:
            with span("comment_batch_cache_hit"):
                result = dict(result)
        labels = {
            l["index"]: l
            for l in result.get("comment_labels", [])
            if l["index"] in {c["index"] for c in batch}
        }
        result["comment_labels"] = [
            {
                **labels.get(
                    c["index"],
                    {
                        "index": c["index"],
                        "kind": "unclear",
                        "aspect": "other",
                        "claim": "Model did not classify this comment",
                    },
                ),
                "text_sha256": hashlib.sha256(c["text"].encode()).hexdigest(),
            }
            for c in batch
        ]
        result.pop("_visual_signatures", None)
        result.pop("_transcription", None)
        batches.append(result)
        entries[batch_key] = result
        source.analysis = {
            **source.analysis,
            "comment_batches": {
                "input_hash": digest,
                "context_hash": context,
                "batches": batches,
                "entries": entries,
            },
        }
        db.commit()
    labels = [label for b in batches for label in b["comment_labels"]]
    return {
        "status": "observations_only",
        "summary": "Classified collected comments in resumable batches; claims remain unverified.",
        "languages": sorted({lang for b in batches for lang in b.get("languages", [])}),
        "observations": [o for b in batches for o in b.get("observations", [])],
        "venue_candidates": [],
        "comment_labels": labels,
        "classified_count": len(labels),
        "collected_count": len(comments),
        "counts": {
            kind: sum(l["kind"] == kind for l in labels) for kind in sorted({l["kind"] for l in labels})
        },
        "limitations": "A firsthand_claim is self-reported, not a verified visit. Loaded comments are not a representative poll. No commenter identity or bot probability is inferred.",
    }
