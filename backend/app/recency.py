"""Publication recency, never fetch time or popularity, determines source ordering."""

import re
from datetime import datetime, timezone


def publication_date(value):
    if not isinstance(value, str) or not value.strip():
        return None
    value = value.strip()
    try:
        date = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        date = None
        for pattern in ("%B %d, %Y", "%b %d, %Y", "%d %B %Y"):
            try:
                date = datetime.strptime(value, pattern)
                break
            except ValueError:
                continue
    if date is None:
        return None
    date = date.replace(tzinfo=timezone.utc) if date.tzinfo is None else date.astimezone(timezone.utc)
    if date > datetime.now(timezone.utc) or date.year < 2000:
        return None
    return date.isoformat()


def snippet_publication(text):
    # Only an explicit post-date phrase, not a crawler date or an arbitrary year.
    match = re.search(r"\bon ([A-Z][a-z]+ \d{1,2}, \d{4})\b", text)
    return publication_date(match[1]) if match else None


def recency_key(content):
    value = publication_date(content.get("published_at")) or publication_date(
        content.get("search_published_at")
    )
    return (bool(value), value or "")
