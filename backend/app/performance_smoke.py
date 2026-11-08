"""Opt-in local model/controlled-browser measurements. Never inserts venue evidence."""

import argparse
import asyncio
import hashlib
import json
import subprocess
from pathlib import Path
import httpx
from sqlalchemy import select
from .config import ROOT, settings
from .performance import Trace, ACTIVE_TRACE


def local_placement():
    from .local_models import endpoint

    with httpx.Client(timeout=10, trust_env=False) as client:
        models = client.get(endpoint() + "/api/ps").json().get("models", [])
    return [
        {k: m.get(k) for k in ("name", "size", "size_vram", "context_length", "expires_at")} for m in models
    ]


def model_smoke():
    from .db import Session, ResearchSource, Investigation
    from .analysts import analyze

    before = local_placement()
    with Session() as db:
        source = next(
            (
                s
                for s in db.scalars(
                    select(ResearchSource)
                    .join(Investigation, ResearchSource.case_id == Investigation.id)
                    .where(Investigation.user_id == "local-operator")
                    .order_by(ResearchSource.created_at.desc())
                )
                if len(s.content.get("caption", "")) > 50
            ),
            None,
        )
        if not source:
            return {"unavailable": "No retained agent-collected caption; no fixture is substituted"}
        content = {"source_url": source.canonical_url, "caption": source.content["caption"]}
        identity = source.id
        digest = hashlib.sha256(source.content["caption"].encode()).hexdigest()
        trials = []
        for index in range(2):
            trace = Trace()
            token = ACTIVE_TRACE.set(trace)
            try:
                prediction = analyze(db, "caption", content)
            finally:
                ACTIVE_TRACE.reset(token)
            trials.append(
                {
                    "trial": index + 1,
                    "timing": trace.summary(),
                    "candidate_count": len(prediction.get("venue_candidates", [])),
                    "observation_count": len(prediction.get("observations", [])),
                    "placement": local_placement(),
                }
            )
    return {
        "source_id": identity,
        "input_sha256": digest,
        "placement_before": before,
        "trials": trials,
        "keep_alive": settings().ollama_keep_alive,
        "scope": "Two repeated real-caption calls, no gold labels, no database writes or accuracy/speedup claim. First trial is cold only if model was absent before it.",
    }


async def browser_smoke():
    """Real Chromium on intercepted offline fixtures, never the public Instagram network."""
    from playwright.async_api import async_playwright
    from .browser_sources import collect_in_browser

    cfg = settings()
    old_comments, old_expansions = cfg.browser_max_comments, cfg.browser_comment_expansions
    cfg.browser_max_comments, cfg.browser_comment_expansions = 2, 0
    contexts, durations, result_counts = [], [], []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)

        class FixtureBrowser:
            async def new_context(self, **kwargs):
                real = await browser.new_context(**kwargs)
                contexts.append({"cookies_at_creation": len(await real.cookies())})

                class Context:
                    async def new_page(self):
                        return await real.new_page()

                    async def route(self, pattern, ignored_handler):
                        async def fixture(route):
                            code = route.request.url.rstrip("/").split("/")[-1]
                            payload = {
                                "code": code,
                                "media_type": 2,
                                "caption": {"text": "Controlled offline cafe fixture " + code},
                                "video_versions": [{"url": "https://video.cdninstagram.com/fixture.mp4"}],
                                "comments_connection": {
                                    "edges": [
                                        {"node": {"pk": "1", "text": "Fixture comment one"}},
                                        {"node": {"pk": "2", "text": "Fixture comment two"}},
                                    ]
                                },
                            }
                            html = '<script type="application/json">' + json.dumps(payload) + "</script>"
                            html += '<script>document.cookie="fixture_only=1;path=/"</script><p>Fixture comment one Fixture comment two</p>'
                            await route.fulfill(status=200, content_type="text/html", body=html)

                        await real.route(pattern, fixture)

                    async def close(self):
                        contexts[-1]["cookies_before_close"] = len(await real.cookies())
                        await real.close()

                return Context()

        try:
            for code in ("offline_a", "offline_b"):
                trace = Trace()
                result = await collect_in_browser(
                    f"https://www.instagram.com/reel/{code}/", 20, reused_browser=FixtureBrowser()
                )
                assert result.get("caption", "").endswith(code)
                assert len(result.get("comment_texts", [])) == 2
                durations.append(trace.summary()["execution_seconds"])
                result_counts.append(
                    {
                        "caption_present": bool(result.get("caption")),
                        "comments": len(result["comment_texts"]),
                        "browser": result["browser"],
                    }
                )
            assert all(c["cookies_at_creation"] == 0 and c["cookies_before_close"] == 1 for c in contexts)
        finally:
            await browser.close()
            cfg.browser_max_comments, cfg.browser_comment_expansions = old_comments, old_expansions
    return {
        "contexts": contexts,
        "seconds": durations,
        "results": result_counts,
        "scope": "Controlled offline pages in one real Chromium process, two clean contexts. Not live Instagram coverage or a measured public-browser speedup.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", action="store_true")
    parser.add_argument("--browser", action="store_true")
    parser.add_argument("--keep-alive", choices=["2m", "5m", "10m"])
    parser.add_argument("--output", default=str(ROOT / "data" / "performance" / "smoke.json"))
    args = parser.parse_args()
    if settings().app_mode != "local":
        raise SystemExit("This opt-in smoke runs only in local mode")
    if args.keep_alive:
        settings().ollama_keep_alive = args.keep_alive
    result = {}
    if args.model:
        result["model"] = model_smoke()
        try:
            result["gpu"] = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,memory.total,memory.used,utilization.gpu",
                    "--format=csv,noheader",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            ).stdout.strip()
        except (OSError, subprocess.TimeoutExpired):
            result["gpu"] = "unavailable"
    if args.browser:
        result["browser"] = asyncio.run(browser_smoke())
    target = Path(args.output).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"receipt": str(target), "checks": list(result)}, indent=2))


if __name__ == "__main__":
    main()
