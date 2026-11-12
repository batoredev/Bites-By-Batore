"""Anonymous rendered-page collection. Only source-bound public page data is retained.

No login sessions, user browser profiles, hidden-API requests or challenge solving.
The browser executes ordinary page requests; downloaded video uses the existing
bounded CDN downloader. Public-page structures can change, so gaps stay explicit.
"""

import asyncio
import hashlib
import ipaddress
import json
import re
import socket
import subprocess
import sys
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from urllib.parse import urlparse
from xml.etree import ElementTree
from .config import settings
from .db import Counter, now
from .providers import Unavailable, DeferredCollection, reserve_browser_call
from .social import canonical_url

HOSTS = ("instagram.com", "cdninstagram.com", "fbcdn.net", "facebook.com", "facebook.net")


def browser_url_allowed(url):
    try:
        p = urlparse(url)
        return (
            p.scheme == "https"
            and not p.username
            and not p.password
            and p.port in (None, 443)
            and any(p.hostname == h or (p.hostname or "").endswith("." + h) for h in HOSTS)
        )
    except ValueError:
        return False


def shortcode(url):
    canonical = canonical_url(url)
    if urlparse(canonical).hostname != "www.instagram.com":
        raise ValueError("Browser collection requires an Instagram post or reel permalink")
    return canonical.rstrip("/").split("/")[-1]


def matched_nodes(payloads, code):
    """Ignore recommendations, other posts and unrelated comments in hydration data."""
    stack = list(payloads)
    visited = 0
    while stack and visited < 100000:
        node = stack.pop()
        visited += 1
        if isinstance(node, dict):
            if node.get("code") == code or node.get("shortcode") == code:
                yield node
            stack.extend(v for v in node.values() if isinstance(v, (dict, list)))
        elif isinstance(node, list):
            stack.extend(node)


def numeric(value):
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def public_audio_reference(manifest):
    """Read an unencrypted audio track from the target reel's delivered DASH manifest."""
    if not isinstance(manifest, str) or len(manifest) > 500000 or "<!" in manifest:
        return None
    try:
        root = ElementTree.fromstring(manifest)
    except ElementTree.ParseError:
        return None
    if root.find(".//{*}ContentProtection") is not None:
        return None
    for adaptation in root.findall(".//{*}AdaptationSet"):
        if not (
            adaptation.get("contentType") == "audio"
            or adaptation.get("mimeType", "").startswith("audio/")
            or any(
                r.get("mimeType", "").startswith("audio/") for r in adaptation.findall(".//{*}Representation")
            )
        ):
            continue
        for node in adaptation.findall(".//{*}BaseURL"):
            ref = node.text or ""
            host = urlparse(ref).hostname or ""
            if browser_url_allowed(ref) and any(
                host == h or host.endswith("." + h) for h in ("cdninstagram.com", "fbcdn.net")
            ):
                return ref
    return None


def public_video_references(manifest):
    """Video-only tracks from the reel's DASH manifest, highest bitrate first."""
    if not isinstance(manifest, str) or len(manifest) > 500000 or "<!" in manifest:
        return []
    try:
        root = ElementTree.fromstring(manifest)
    except ElementTree.ParseError:
        return []
    if root.find(".//{*}ContentProtection") is not None:
        return []
    found = []
    for node in root.findall(".//{*}Representation"):
        if not node.get("mimeType", "video/").startswith("video/") or node.get("width") is None:
            continue
        base = node.find("{*}BaseURL")
        ref = (base.text or "") if base is not None else ""
        host = urlparse(ref).hostname or ""
        if browser_url_allowed(ref) and any(
            host == h or host.endswith("." + h) for h in ("cdninstagram.com", "fbcdn.net")
        ):
            try:
                found.append((int(node.get("bandwidth", "0")), ref))
            except ValueError:
                continue
    return [ref for _, ref in sorted(found, reverse=True)]


def extract_public_data(payloads, code, visible_text, max_comments=30):
    output, comments, video_urls = {}, {}, []
    visible = " ".join(visible_text.split())
    matches, more = 0, False
    for item in matched_nodes(payloads, code):
        # Route configuration also contains a shortcode; it is not a media record.
        if not any(
            k in item
            for k in (
                "video_versions",
                "video_url",
                "comments_connection",
                "edge_media_to_parent_comment",
                "media_type",
                "edge_media_to_caption",
            )
        ):
            continue
        matches += 1
        if isinstance(item.get("has_audio"), bool):
            output["source_has_audio"] = item["has_audio"]
        caption = item.get("caption")
        if isinstance(caption, dict):
            caption = caption.get("text")
        if not isinstance(caption, str):
            edges = item.get("edge_media_to_caption", {}).get("edges", [])
            caption = edges[0].get("node", {}).get("text", "") if edges else ""
        if caption and len(caption) > len(output.get("caption", "")):
            output["caption"] = caption[:12000]
        owner = item.get("user") or item.get("owner") or {}
        if isinstance(owner, dict) and owner.get("username"):
            output["creator"] = str(owner["username"])[:100]
            output["creator_id"] = str(owner.get("pk") or owner.get("id") or "")[:100]
        for field, keys in {
            "likes": ["like_count"],
            "comments_count": ["comment_count"],
            "views": ["video_view_count", "play_count"],
        }.items():
            for key in keys:
                if numeric(item.get(key)) is not None:
                    output[field] = item[key]
        stamp = numeric(item.get("taken_at") or item.get("taken_at_timestamp"))
        if stamp:
            try:
                output["published_at"] = datetime.fromtimestamp(stamp, timezone.utc).isoformat()
            except (OverflowError, OSError, ValueError):
                pass
        versions = [v for v in item.get("video_versions", []) if isinstance(v, dict)]
        # Complete (video+audio) files first, largest first, then video-only tracks
        # that the collector joins with the separate audio track.
        versions.sort(key=lambda v: -(numeric(v.get("width")) or 0) * (numeric(v.get("height")) or 0))
        refs = [item.get("video_url")] + [v.get("url") for v in versions]
        refs += public_video_references(item.get("video_dash_manifest"))
        for ref in refs:
            if isinstance(ref, str) and browser_url_allowed(ref):
                host = urlparse(ref).hostname or ""
                if any(host == h or host.endswith("." + h) for h in ("cdninstagram.com", "fbcdn.net")):
                    video_urls.append(ref)
        audio = public_audio_reference(item.get("video_dash_manifest"))
        if audio:
            output["audio_url"] = audio
        place = item.get("location")
        if isinstance(place, dict) and isinstance(place.get("name"), str) and place["name"].strip():
            # The creator's own location tag: the strongest venue clue a reel carries.
            tag = {"name": " ".join(place["name"].split())[:150]}
            for key in ("lat", "lng"):
                value = place.get(key)
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    tag[key] = float(value)
            if place.get("pk") or place.get("id"):
                tag["id"] = str(place.get("pk") or place.get("id"))[:40]
            output["location_tag"] = tag
        for key in ("comments_connection", "edge_media_to_parent_comment", "edge_media_to_comment"):
            connection = item.get(key) or {}
            if not isinstance(connection, dict):
                continue
            more |= bool((connection.get("page_info") or {}).get("has_next_page"))
            edges = list(connection.get("edges", []))[:100]
            for edge in list(edges):
                parent = edge.get("node", {}) if isinstance(edge, dict) else {}
                for reply_key in ("edge_threaded_comments", "child_comments", "replies_connection"):
                    replies = parent.get(reply_key, {})
                    if isinstance(replies, dict):
                        edges.extend(replies.get("edges", [])[:100])
                        more |= bool(replies.get("page_info", {}).get("has_next_page"))
            for edge in edges[:200]:
                row = edge.get("node", {}) if isinstance(edge, dict) else {}
                text = row.get("text")
                if not isinstance(text, str) or not text.strip() or row.get("is_covered"):
                    continue
                # Retain only delivered comments that are also rendered on this page.
                if " ".join(text.split()) not in visible:
                    continue
                identity = str(row.get("pk") or row.get("id") or hashlib.sha256(text.encode()).hexdigest())
                comments[identity] = text[:1000]
    if video_urls:
        video_urls = list(dict.fromkeys(video_urls))
        output["media_url"] = video_urls[0]
        if video_urls[1:]:
            output["media_alternatives"] = video_urls[1:9]
    sample = list(comments.values())[:max_comments]
    if sample:
        output["comments"] = "\n".join(sample)
        output["comment_texts"] = sample
    if output.get("caption"):
        output["caption_coverage"] = (
            "Caption delivered in public rendered-page data; not independently verified"
        )
    output["comments_coverage"] = (
        f"{len(sample)} source-bound visible comments/replies; limited sample, further pages may be unavailable"
        if sample
        else "No source-bound visible comment text retrieved; not evidence of zero comments"
    )
    output["browser"] = {
        "status": "public_content" if output.get("caption") or sample or video_urls else "no_source_data",
        "source_bound_records": matches,
        "comment_sample_size": len(sample),
        "more_comments_available": more,
        "video_reference_found": bool(video_urls),
        "video_downloaded": False,
        "authenticated": False,
        "audio_reference_found": bool(output.get("audio_url")),
    }
    if output["browser"]["status"] == "public_content":
        output["collection_method"] = "public_browser"
    output["fetched_at"] = now()
    return output


async def read_public_snapshot(page):
    return await page.evaluate("""() => {
                    const text = (document.body?.innerText || '').slice(0, 60000);
                    const scripts = []; let bytes = 0;
                    for (const node of document.querySelectorAll('script[type="application/json"]')) {
                        const value = node.textContent || ''; bytes += value.length;
                        if (bytes > 3000000) break;
                        scripts.push(value);
                    }
                    const videos = [...document.querySelectorAll('video')];
                    const loaded = videos.some(v => v.readyState >= 2);
                    videos.forEach(v => v.pause());
                    return {text, scripts, loaded};
                }""")


async def expand_visible_comments(page, code, maximum):
    """Only ordinary comment/reply controls inside the exact post's article."""
    expanded = 0
    stop = "expansion_budget"
    for _ in range(maximum):
        if any(p in urlparse(page.url).path for p in ("/accounts/", "/challenge", "/checkpoint")):
            stop = "login_or_challenge"
            break
        article = page.locator("article").filter(
            has=page.locator(f'a[href*="/p/{code}/"], a[href*="/reel/{code}/"]')
        )
        if await article.count() != 1:
            stop = "exact_post_controls_unavailable"
            break
        buttons = article.get_by_role(
            "button",
            name=re.compile(
                r"^(?:Load more comments|View all \d+[,.\d]* comments|View (?:\d+ )?(?:more )?replies(?: \(\d+\))?)$",
                re.I,
            ),
        )
        if not await buttons.count():
            stop = "no_more_visible_controls"
            break
        try:
            await buttons.first.click(timeout=1200)
            expanded += 1
            await page.wait_for_timeout(500)
        except Exception:
            stop = "control_unavailable"
            break
    return {
        "expanded_controls": expanded,
        "stop_reason": stop,
        "coverage": "Only exposed public controls; login/challenges are not bypassed",
    }


@asynccontextmanager
async def browser_scope(reused=None):
    from playwright.async_api import async_playwright

    if reused is not None:
        yield reused
        return
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        try:
            yield browser
        finally:
            await browser.close()


async def wait_public_ready(page, code, maximum):
    """Exit early only after the configured bounded sample and video are present."""
    started = asyncio.get_running_loop().time()
    while asyncio.get_running_loop().time() - started < 4.5:
        snapshot = await read_public_snapshot(page)
        payloads = []
        for raw in snapshot["scripts"]:
            try:
                payloads.append(json.loads(raw))
            except (ValueError, RecursionError):
                pass
        result = extract_public_data(payloads, code, snapshot["text"], maximum)
        if (
            result.get("caption")
            and result.get("media_url")
            and len(result.get("comment_texts", [])) >= maximum
        ):
            return "configured_sample_ready"
        await page.wait_for_timeout(400)
    return "settle_window_elapsed"


async def collect_in_browser(url, seconds=35, reused_browser=None):
    from playwright.async_api import Error as BrowserError

    code = shortcode(url)
    async with browser_scope(reused_browser) as browser:
        context = None
        try:
            context = await browser.new_context(service_workers="block", accept_downloads=False)
            page = await context.new_page()
            requests, rejected = 0, 0
            hosts = {}

            async def route_request(route):
                nonlocal requests, rejected
                requests += 1
                target = route.request.url
                allowed = browser_url_allowed(target) and requests <= 160
                if allowed:
                    host = urlparse(target).hostname
                    if host not in hosts:
                        try:
                            addresses = await asyncio.get_running_loop().getaddrinfo(
                                host, 443, type=socket.SOCK_STREAM
                            )
                            hosts[host] = bool(addresses) and all(
                                ipaddress.ip_address(a[4][0]).is_global for a in addresses
                            )
                        except OSError:
                            hosts[host] = False
                    allowed = hosts[host]
                if allowed:
                    await route.continue_()
                else:
                    rejected += 1
                    await route.abort()

            await context.route("**/*", route_request)

            async def inspect_page():
                response = await page.goto(
                    f"https://www.instagram.com/reel/{code}/", wait_until="domcontentloaded", timeout=25000
                )
                status = response.status if response else 0
                if status != 200:
                    return {
                        "browser": {
                            "status": "rate_limited" if status == 429 else "page_unavailable",
                            "http_status": status,
                            "authenticated": False,
                        }
                    }
                readiness = await wait_public_ready(page, code, settings().browser_max_comments)
                path = urlparse(page.url).path
                if any(part in path for part in ("/accounts/login", "/challenge", "/checkpoint")):
                    return {
                        "browser": {
                            "status": "challenge" if "/accounts/login" not in path else "login_required",
                            "authenticated": False,
                        }
                    }
                # No clicks on account prompts or challenge pages; an optional sign-up
                # panel may coexist with publicly readable content.
                expansion = await expand_visible_comments(page, code, settings().browser_comment_expansions)
                snapshot = await read_public_snapshot(page)
                payloads = []
                for raw in snapshot["scripts"]:
                    try:
                        payloads.append(json.loads(raw))
                    except (ValueError, RecursionError):
                        continue
                result = extract_public_data(
                    payloads, code, snapshot["text"], settings().browser_max_comments
                )
                details = result["browser"]
                text = snapshot["text"].casefold()
                if details["status"] == "no_source_data":
                    if any(
                        x in text
                        for x in (
                            "confirm you're human",
                            "confirm you are human",
                            "unusual activity",
                            "automated behavior",
                        )
                    ):
                        details["status"] = "challenge"
                    elif "log in" in text or "sign up" in text:
                        details["status"] = "login_required"
                details.update(
                    http_status=status,
                    playable_video_seen=snapshot["loaded"],
                    request_count=requests,
                    blocked_requests=rejected,
                    comment_expansion=expansion,
                    readiness=readiness,
                )
                return result

            try:
                return await asyncio.wait_for(inspect_page(), timeout=seconds)
            except (TimeoutError, BrowserError):
                return {"browser": {"status": "timeout_or_navigation_failed", "authenticated": False}}
        finally:
            if context is not None:
                await context.close()


def browser_instagram(db, url):
    cfg = settings()
    if cfg.app_mode == "demo" or not cfg.instagram_browser_enabled:
        raise Unavailable("Direct browser collection is disabled")
    shortcode(url)
    cooldown = db.get(Counter, "instagram-browser-cooldown")
    if cooldown and cooldown.value > int(datetime.now(timezone.utc).timestamp()):
        raise DeferredCollection(
            "Instagram browser collection is cooling down after a challenge or rate limit"
        )
    reserve_browser_call(db)
    try:
        from .performance import span

        with span("browser_collection"):
            if cfg.browser_reuse_enabled:
                from .browser_host import HOST

                output = HOST.request(canonical_url(url), cfg.browser_timeout_seconds)
            else:
                result = subprocess.run(
                    [sys.executable, "-m", "app.browser_sources", canonical_url(url)],
                    capture_output=True,
                    encoding="utf-8",
                    timeout=cfg.browser_timeout_seconds + 20,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                if result.returncode or len(result.stdout) > 150000:
                    raise Unavailable(
                        "Browser collector failed; run scripts/setup-local.ps1 to install Chromium"
                    )
                output = json.loads(result.stdout)
            if not isinstance(output, dict) or not isinstance(output.get("browser"), dict):
                raise ValueError("Invalid browser contract")
    except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
        raise Unavailable("Browser collector unavailable or exceeded its time limit") from exc
    if output["browser"].get("status") in {"rate_limited", "challenge"}:
        cooldown = cooldown or Counter(key="instagram-browser-cooldown")
        cooldown.value = int(datetime.now(timezone.utc).timestamp()) + 3600
        db.add(cooldown)
        db.commit()
    return output


async def serve():
    async with browser_scope() as browser:
        while True:
            line = await asyncio.to_thread(sys.stdin.readline)
            if not line:
                return
            try:
                command = json.loads(line)
                result = await collect_in_browser(
                    command["url"], min(60, max(10, int(command["seconds"]))), reused_browser=browser
                )
            except Exception:
                result = {"browser": {"status": "runtime_unavailable", "authenticated": False}}
            print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        if sys.argv[1] == "--serve":
            asyncio.run(serve())
        else:
            print(
                json.dumps(
                    asyncio.run(collect_in_browser(sys.argv[1], settings().browser_timeout_seconds)),
                    ensure_ascii=False,
                )
            )
    except Exception:
        # Never write page data, signed URLs or browser traces to application logs.
        print(json.dumps({"browser": {"status": "runtime_unavailable", "authenticated": False}}))
