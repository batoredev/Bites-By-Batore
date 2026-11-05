"""Local public-web enrichment of discovered spots; search hits never imply authority."""

import json
import subprocess
import sys
from urllib.parse import urlparse
from sqlalchemy.orm.attributes import flag_modified
from .db import IdentifiedSpot, now
from .providers import quota, Unavailable, DeferredCollection
from .spots import unique, INACTIVE
from .inventory import parse_document
from .web_evidence import read_official_html
from .resolver import normalized
from .recency import publication_date, recency_key


def enrich_spot(db, spot_id):
    row = db.get(IdentifiedSpot, spot_id)
    if not row:
        return {"removed": True}
    if row.status in INACTIVE:
        return {"skipped": row.status, "remaining": 0}
    data = dict(row.data)
    if "web_search_results" not in data:
        quota(db)
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "app.spot_search",
                    row.name + " " + row.area + " Coimbatore menu address",
                ],
                capture_output=True,
                encoding="utf-8",
                timeout=40,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if result.returncode or len(result.stdout) > 150000:
                raise ValueError("Invalid search response")
            results = json.loads(result.stdout)
            if not isinstance(results, list):
                raise ValueError("Invalid search response")
        except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
            raise Unavailable("Venue web search unavailable; retry its saved job") from exc
        data["web_search_results"] = [
            {
                "url": r.get("href", ""),
                "title": r.get("title", "")[:300],
                "search_published_at": publication_date(r.get("date")),
                "status": "pending",
            }
            for r in results
            if urlparse(r.get("href", "")).scheme == "https"
        ]
        data["web_search_results"] = sorted(unique(data["web_search_results"]), key=recency_key, reverse=True)
        row.data = data
        db.commit()
    pending = [r for r in data["web_search_results"] if r["status"] == "pending"]
    for item in pending[:2]:
        url = item["url"]
        # Social collection belongs to the reel pipeline; do not mistake its
        # login shell or a Maps UI for a fetched menu/official website.
        host = urlparse(url).hostname or ""
        if host.endswith(("instagram.com", "facebook.com", "youtube.com", "google.com")):
            item["status"] = "link_only"
            continue
        try:
            doc = parse_document(read_official_html(db, url, allow_unverified_host=True), url)
            text = normalized(doc["text"])
            tokens = [
                w
                for w in normalized(row.name).split()
                if len(w) > 3 and w not in {"restaurant", "coimbatore", "cafe", "japanese"}
            ]
            if (
                not tokens
                or not any(w in text.split() for w in tokens)
                or not any(w in text for w in ("coimbatore", "kovai"))
            ):
                item["status"] = "identity_unconfirmed"
                continue
            data["sources"] = unique(
                data.get("sources", [])
                + [
                    {
                        "url": url,
                        "type": "web_candidate",
                        "collected_at": now(),
                        "published_at": item.get("search_published_at"),
                        "basis": "Search-discovered page; authority, exact branch and freshness unverified",
                    }
                ]
            )
            doc["offerings"] = [
                {
                    **x,
                    "basis": "Search-discovered menu; branch, authority, taxes and current availability unverified",
                }
                for x in doc["offerings"]
            ]
            for field in ("maps_links", "menu_links", "offerings"):
                data[field] = unique(data.get(field, []) + doc[field])
            if doc.get("coordinates"):
                doc["coordinates"]["basis"] = (
                    "Direction link on a search-discovered page; branch and authority unverified"
                )
                data["coordinate_candidates"] = unique(
                    data.get("coordinate_candidates", []) + [doc["coordinates"]]
                )
            item["status"] = "collected_unverified"
        except DeferredCollection:
            row.data = dict(data)
            flag_modified(row, "data")
            db.commit()
            raise
        except Unavailable as exc:
            item["status"], item["gap"] = "unavailable", str(exc)
        row.data = dict(data)
        flag_modified(row, "data")
        row.updated_at = now()
        db.commit()
    row.data = dict(data)
    flag_modified(row, "data")
    row.updated_at = now()
    db.commit()
    remaining = sum(x["status"] == "pending" for x in data["web_search_results"])
    return {
        "spot_id": row.id,
        "remaining": remaining,
        "found": len(data["web_search_results"]),
        "published": False,
    }


if __name__ == "__main__":
    from ddgs import DDGS

    sys.stdout.reconfigure(encoding="utf-8")
    try:
        rows = DDGS(timeout=12).text(sys.argv[1], max_results=12, timelimit="y")
        if not rows:
            rows = DDGS(timeout=12).text(sys.argv[1], max_results=12)
        print(json.dumps(rows, ensure_ascii=False))
    except Exception:
        sys.exit(1)
