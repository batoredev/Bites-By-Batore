"""Split oversized evidence without silently dropping its tail or original offsets."""

import copy
import json
from .providers import Unavailable


class AnalysisLimit(Unavailable):
    pass


def split_evidence(content, target=6000):
    if len(json.dumps(content, ensure_ascii=False)) <= target:
        return [content]
    base = copy.deepcopy(content)
    parent = base.pop("evidence_segment", {})
    fields = []
    for key in ("caption", "transcript", "comments"):
        value = base.pop(key, None)
        if isinstance(value, str) and value:
            fields.append((key, value))
        elif value is not None:
            base[key] = value
    if isinstance(base.get("audio"), dict):
        audio = base["audio"]
        text = audio.pop("text", "")
        # Segment text is already represented, in order, by the full transcript.
        if text:
            fields.append(("audio.text", text))
            audio.pop("segments", None)
    overhead = len(json.dumps(base, ensure_ascii=False)) + 350
    width = target - overhead
    if not fields or width < 256:
        raise AnalysisLimit("Evidence metadata exceeds the bounded context; no text was discarded")
    chunks = []
    for field, text in fields:
        offset = 0
        while offset < len(text):
            end = min(len(text), offset + width)
            # Prefer a complete line/word, keeping overlap for boundary context.
            if end < len(text):
                boundary = max(
                    text.rfind("\n", offset + width // 2, end), text.rfind(" ", offset + width // 2, end)
                )
                if boundary > offset:
                    end = boundary
            chunk = copy.deepcopy(base)
            if field == "audio.text":
                chunk.setdefault("audio", {})["text"] = text[offset:end]
            else:
                chunk[field] = text[offset:end]
            origin = parent.get("start", 0) if parent.get("field") == field else 0
            total = parent.get("total", len(text)) if parent.get("field") == field else len(text)
            chunk["evidence_segment"] = {
                "field": field,
                "start": origin + offset,
                "end": origin + end,
                "total": total,
            }
            chunks.append(chunk)
            if end == len(text):
                break
            offset = max(offset + 1, end - min(200, width // 5))
    return chunks
