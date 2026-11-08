"""Explicit source contracts: discovery, collection, and bounded public media.

Connectors never accept login passwords or silently switch providers. Apify uses
an operator-configured saved task, whose actor input/output must be smoke tested.
"""

import ipaddress
import re
import socket
from urllib.parse import urlparse, urlunparse
import httpx
from .config import settings
from .providers import call, require, Unavailable, safe_social_url, media_payload, quota, youtube_id


def canonical_url(url):
    p = urlparse(safe_social_url(url))
    host = (p.hostname or "").removeprefix("www.")
    video_id = youtube_id(url)
    if video_id:
        return "https://www.youtube.com/watch?v=" + video_id
    if host == "instagram.com":
        match = re.fullmatch(r"/(?:reel|reels|p|tv)/([A-Za-z0-9_-]+)/?", p.path)
        if not match:
            raise ValueError("Use an Instagram reel or post permalink")
        return f"https://www.instagram.com/p/{match[1]}/"
    return urlunparse(("https", host, p.path, "", p.query, ""))


def hashtags(query):
    words = re.findall(r"[^\W_]+", query.casefold(), re.UNICODE)
    terms = [w for w in words if w not in {"in", "near", "the", "and", "find", "me"}]
    return list(dict.fromkeys(["".join(terms), *terms]))[:3]


def meta_get(db, path, params):
    c = settings()
    require(c.meta_access_token, "Meta token")
    require(c.meta_instagram_account_id, "Meta professional account ID")
    if not re.fullmatch(r"v\d+\.\d+", c.meta_graph_version):
        raise Unavailable("Set META_GRAPH_VERSION to the API version enabled for your Meta app")
    if not re.fullmatch(r"[A-Za-z0-9_/-]+", path):
        raise Unavailable("Invalid Meta resource identifier")
    result = call(
        db,
        "GET",
        f"https://graph.facebook.com/{c.meta_graph_version}/{path}",
        headers={"Authorization": f"Bearer {c.meta_access_token}"},
        params=params,
    )
    if result.get("error"):
        raise Unavailable("Meta did not grant access to this resource")
    return result


def normalize_item(item):
    url = item.get("permalink") or item.get("url") or ""
    if not url and item.get("shortCode"):
        url = f"https://www.instagram.com/p/{item['shortCode']}/"
    try:
        url = canonical_url(url)
    except (ValueError, TypeError):
        return None
    comments = item.get("latestComments", item.get("comments", []))
    if isinstance(comments, dict):
        comments = comments.get("data", [])
    if not isinstance(comments, list):
        comments = []
    return {
        "url": url,
        "platform": "instagram",
        "external_id": str(item.get("id", ""))[:100],
        "caption": str(item.get("caption") or "")[:10000],
        "creator": str(item.get("ownerUsername") or item.get("username") or "")[:100],
        "creator_id": str(item.get("ownerId") or "")[:100],
        "published_at": item.get("timestamp"),
        "comments": "\n".join(str(x.get("text", ""))[:1000] for x in comments[:50] if isinstance(x, dict)),
        "comments_coverage": "Available sample only; missing comments are not negative feedback",
        "likes": item.get("likesCount", item.get("like_count")),
        "views": item.get("videoViewCount"),
        "dislikes": None,
        "media_url": item.get("videoUrl")
        or (item.get("media_url") if item.get("media_type") == "VIDEO" else None),
        "access": "provider_sample",
        "provider_collected": True,
        "collection_method": "configured_provider",
    }


def instagram_discover(db, query, state=None):
    """Read one official recent-media page; caller persists the cursor between jobs."""
    c = settings()
    if c.instagram_provider != "meta":
        raise Unavailable("Optional Meta discovery is not configured; public discovery is independent")
    progress = state if state is not None else {}
    tags = hashtags(query)
    index = int(progress.get("tag_index", 0))
    if index >= len(tags):
        progress["done"] = True
        return []
    if not progress.get("hashtag_id"):
        ids = meta_get(
            db, "ig_hashtag_search", {"user_id": c.meta_instagram_account_id, "q": tags[index]}
        ).get("data", [])
        if not ids:
            progress.update(tag_index=index + 1, done=index + 1 >= len(tags))
            return []
        progress["hashtag_id"] = str(ids[0]["id"])
    params = {
        "user_id": c.meta_instagram_account_id,
        "limit": 50,
        "fields": "id,caption,media_type,media_url,permalink,timestamp,like_count,comments_count",
    }
    if progress.get("after"):
        params["after"] = progress["after"]
    data = meta_get(db, progress["hashtag_id"] + "/recent_media", params)
    rows = [x for item in data.get("data", []) if (x := normalize_item(item))]
    paging = data.get("paging") or {}
    after = (paging.get("cursors") or {}).get("after") if paging.get("next") else None
    if after:
        if after == progress.get("after"):
            raise Unavailable("Meta repeated its discovery cursor; inspect coverage before retrying")
        progress["after"] = after
    else:
        progress.update(tag_index=index + 1, done=index + 1 >= len(tags))
        progress.pop("after", None)
        progress.pop("hashtag_id", None)
    return rows


def apify_start(db, query, urls=None):
    c = settings()
    require(c.apify_api_token, "Apify token")
    if not re.fullmatch(r"[A-Za-z0-9_~-]+", c.apify_instagram_task_id):
        raise Unavailable("Set a tested APIFY_INSTAGRAM_TASK_ID")
    # Saved task owns actor-specific defaults. Overrides match Instagram Scraper's contract.
    body = {"resultsLimit": 1000}
    if urls:
        body["directUrls"] = [safe_social_url(u) for u in urls[:5]]
    else:
        body.update(search=query, searchType="hashtag", searchLimit=3)
    result = call(
        db,
        "POST",
        f"https://api.apify.com/v2/actor-tasks/{c.apify_instagram_task_id}/runs",
        headers={"Authorization": f"Bearer {c.apify_api_token}"},
        params={"maxTotalChargeUsd": min(max(c.apify_max_charge_usd, 0.01), 10), "timeout": 180},
        json=body,
    )
    run_id = result.get("data", {}).get("id", "")
    if not re.fullmatch(r"[A-Za-z0-9]+", run_id):
        raise Unavailable("Data provider returned no run ID")
    return run_id


def apify_poll(db, run_id):
    if not re.fullmatch(r"[A-Za-z0-9]+", run_id):
        raise Unavailable("Invalid data-provider run ID")
    headers = {"Authorization": f"Bearer {settings().apify_api_token}"}
    run = call(db, "GET", f"https://api.apify.com/v2/actor-runs/{run_id}", headers=headers).get("data", {})
    if run.get("status") in {"READY", "RUNNING", "TIMING-OUT", "ABORTING"}:
        return None
    if run.get("status") != "SUCCEEDED":
        raise Unavailable("Instagram provider run failed or timed out; inspect its dashboard")
    dataset = run.get("defaultDatasetId", "")
    if not re.fullmatch(r"[A-Za-z0-9]+", dataset):
        raise Unavailable("Instagram provider dataset missing")
    rows = call(
        db,
        "GET",
        f"https://api.apify.com/v2/datasets/{dataset}/items",
        headers=headers,
        params={"clean": "true", "limit": 1000},
    )
    if not isinstance(rows, list):
        raise Unavailable("Instagram provider returned an invalid dataset")
    return [x for item in rows if isinstance(item, dict) and (x := normalize_item(item))]


def collect_meta_comments(db, item):
    if not re.fullmatch(r"\d+", item.get("external_id", "")):
        return item
    try:
        comments = meta_get(db, item["external_id"] + "/comments", {"fields": "text,timestamp", "limit": 50})
        return {
            **item,
            "comments": "\n".join(x.get("text", "") for x in comments.get("data", [])[:50]),
            "comments_coverage": "Up to 50 permitted comments; partial sample",
        }
    except Unavailable:
        return {**item, "comments_coverage": "Comments unavailable with configured permissions"}


def allowed_media_url(url):
    p = urlparse(url)
    host = p.hostname or ""
    if p.scheme != "https" or p.username or p.password or p.port not in (None, 443):
        raise Unavailable("Media URL must be public HTTPS")
    if not any(host == d or host.endswith("." + d) for d in ("cdninstagram.com", "fbcdn.net")):
        raise Unavailable("Media host is outside the supported Instagram CDN allowlist")
    try:
        addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(x[4][0]).is_global for x in addresses):
            raise Unavailable("Media host did not resolve to public addresses")
    except OSError as exc:
        raise Unavailable("Media host could not be resolved") from exc
    return url


from .performance import measured


@measured("video_download")
def download_media(db, url):
    quota(db)
    maximum = min(settings().max_media_mb, 20) * 1024 * 1024
    try:
        with httpx.Client(timeout=30, follow_redirects=False, trust_env=False) as client:
            # No redirects: an expired CDN link must be collected again.
            with client.stream("GET", allowed_media_url(url)) as response:
                if response.status_code != 200:
                    raise Unavailable(
                        "Media download unavailable; recollect the source or upload permitted media"
                    )
                chunks = bytearray()
                for chunk in response.iter_bytes():
                    chunks.extend(chunk)
                    if len(chunks) > maximum:
                        raise Unavailable("Source video exceeds the configured download limit")
                return media_payload(
                    bytes(chunks), response.headers.get("content-type", "video/mp4").split(";")[0]
                )
    except (httpx.HTTPError, ValueError) as exc:
        raise Unavailable("Media could not be downloaded as a supported video") from exc
