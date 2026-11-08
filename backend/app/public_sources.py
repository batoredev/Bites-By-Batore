"""Key-free public discovery and bounded public Instagram metadata collection.

No account cookies, login automation, challenge solving or hidden endpoints.
Search previews remain leads even if the original page cannot be read.
"""

import json
import re
import subprocess
import sys
from html.parser import HTMLParser
from urllib.parse import urlparse
import httpx
from .db import now
from .providers import Unavailable, quota
from .collection_control import backoff, success
from .social import canonical_url
from .recency import publication_date, snippet_publication, recency_key


def public_search(db, query):
    quota(db, host="public-search")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "app.public_sources", query],
            capture_output=True,
            encoding="utf-8",
            timeout=55,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode:
            backoff(db, "public-search")
        rows = json.loads(result.stdout)
    except (OSError, subprocess.TimeoutExpired, ValueError):
        backoff(db, "public-search")
    success(db, "public-search")
    output = []
    for row in rows:
        url = row.get("href", "")
        if urlparse(url).hostname not in {"instagram.com", "www.instagram.com"}:
            continue
        try:
            url = canonical_url(url)
        except ValueError:
            continue
        output.append(
            {
                "url": url,
                "platform": "instagram",
                "title": row.get("title", "")[:500],
                "search_preview": row.get("body", "")[:2000],
                "snippet_is_not_caption": True,
                "access": "public_search_lead",
                "discovered_at": now(),
                "search_published_at": publication_date(row.get("published_at") or row.get("date"))
                or snippet_publication(row.get("body", "")),
                "search_window": row.get("search_window", "unknown"),
                "date_basis": "Search-reported date; confirm against source",
            }
        )
    return sorted(output, key=recency_key, reverse=True)


class PublicMetadata(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta = {}

    def handle_starttag(self, tag, attrs):
        if tag == "meta":
            data = dict(attrs)
            key = data.get("property") or data.get("name")
            if key and data.get("content"):
                self.meta[key] = data["content"]


def metadata_details(description):
    match = re.match(
        r"([\d,]+) likes, ([\d,]+) comments - ([\w.]+) on ([A-Za-z]+ \d{1,2}, \d{4}):", description
    )
    if not match:
        return {}
    return {
        "likes": int(match[1].replace(",", "")),
        "comments_count": int(match[2].replace(",", "")),
        "creator": match[3],
        "published_date_text": match[4],
        "published_at": publication_date(match[4]),
        "engagement_coverage": "Public metadata snapshot; counts may be stale",
    }


from .performance import measured


@measured("public_metadata")
def public_instagram(db, url):
    url = canonical_url(url)
    if urlparse(url).hostname != "www.instagram.com":
        raise Unavailable("Public collector supports Instagram permalinks only")
    quota(db, host="www.instagram.com")
    try:
        with httpx.Client(timeout=25, trust_env=False, follow_redirects=False) as client:
            with client.stream("GET", url, headers={"User-Agent": "BatoreResearch/0.3"}) as response:
                if response.status_code in {429, 503, 504}:
                    backoff(db, "www.instagram.com", headers=response.headers)
                if response.status_code != 200:
                    raise Unavailable(
                        f"Instagram public page returned HTTP {response.status_code}; source access required"
                    )
                raw = bytearray()
                for chunk in response.iter_bytes():
                    raw.extend(chunk)
                    if len(raw) > 3 * 1024 * 1024:
                        raise Unavailable("Instagram page exceeded collection size limit")
        parser = PublicMetadata()
        parser.feed(raw.decode("utf-8", errors="replace"))
        description = parser.meta.get("og:description", "")
        if len(description) < 40 or any(
            x in description.casefold()
            for x in ["log in to instagram", "sign up to see", "create an account"]
        ):
            raise Unavailable("Instagram exposed no usable public caption; login/challenge was not bypassed")
        return {
            **metadata_details(description),
            "caption": description[:12000],
            "caption_coverage": "Public page metadata; may be truncated",
            "media_url": parser.meta.get("og:video:secure_url") or parser.meta.get("og:video", ""),
            "comments_coverage": "Comments not available from public metadata",
            "fetched_at": now(),
            "collection_method": "public_html_metadata",
        }
    except (httpx.HTTPError, OSError) as exc:
        raise Unavailable("Instagram public page could not be fetched") from exc


if __name__ == "__main__":
    from ddgs import DDGS

    sys.stdout.reconfigure(encoding="utf-8")
    try:
        # Disable optional distributed search; query only public search backends.
        query = sys.argv[1]
        focus = next(
            (
                word
                for word in [
                    "sushi",
                    "cafes",
                    "bowling",
                    "gaming",
                    "karting",
                    "parks",
                    "cinema",
                    "vegetarian",
                ]
                if word in query.lower()
            ),
            "",
        )
        aliases = {
            "cafes": ["cafe", "café", "coffee"],
            "parks": ["park"],
            "cinema": ["cinema", "inox", "pvr", "movie", "theatre"],
        }

        def relevant(items):
            if not focus:
                return items
            return [
                r
                for r in items
                if any(
                    term in (r.get("title", "") + " " + r.get("body", "")).lower()
                    for term in aliases.get(focus, [focus])
                )
            ]

        rows = []
        seen = set()
        for window in ("m", "y", None):
            try:
                found = relevant(
                    DDGS(timeout=10).text(
                        query + " site:instagram.com/reel/", max_results=30, backend="auto", timelimit=window
                    )
                )
                for row in found:
                    if row.get("href") not in seen:
                        rows.append({**row, "search_window": window or "all_time_fallback"})
                        seen.add(row.get("href"))
            except Exception:
                continue
        if not rows:
            from .frontier import AREAS

            for area in AREAS:
                query = query.replace(area, "")
            query = "Coimbatore " + focus if focus else query.strip()
            rows = [
                {**r, "search_window": "broader_city_fallback"}
                for r in relevant(
                    DDGS(timeout=10).text(
                        query + " site:instagram.com/reel/", max_results=30, backend="auto", timelimit="y"
                    )
                )
            ]
        print(json.dumps(rows, ensure_ascii=False))
    except Exception:
        sys.exit(1)
