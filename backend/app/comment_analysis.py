"""Checkpointed classification of every collected comment, without author profiling."""

import hashlib
import json
from .providers import renew_job


def analyze_comments(db, source, content, analyzer):
    comments = source.content.get("comment_texts") or str(source.content.get("comments", "")).splitlines()
    comments = [str(c).strip()[:1000] for c in comments if str(c).strip()][:100]
    digest = hashlib.sha256(json.dumps(comments, ensure_ascii=False).encode()).hexdigest()
    saved = source.analysis.get("comment_batches", {})
    batches = list(saved.get("batches", [])) if saved.get("input_hash") == digest else []
    for offset in range(len(batches) * 5, len(comments), 5):
        renew_job(db)
        batch = [{"index": i, "text": text} for i, text in enumerate(comments[offset : offset + 5], offset)]
        result = analyzer(
            db,
            "comments",
            {**content, "comments": "\n".join(c["text"] for c in batch), "indexed_comments": batch},
        )
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
        source.analysis = {**source.analysis, "comment_batches": {"input_hash": digest, "batches": batches}}
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
