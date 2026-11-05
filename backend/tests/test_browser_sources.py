import asyncio
import base64
import json
import subprocess
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import pytest
from app.browser_sources import extract_public_data, browser_url_allowed, shortcode, public_audio_reference
from app.config import settings
from app.db import Session, Counter
from app.providers import Unavailable
from app.research import start_case, source_add, collect_stage, public_case, purge_expired_sources


def payload(code="target"):
    return {
        "code": code,
        "media_type": 2,
        "caption": {"text": "Fixture Cafe in Coimbatore"},
        "user": {"username": "fixture_publisher", "id": "publisher-id"},
        "like_count": 12,
        "comment_count": 80,
        "video_versions": [{"url": "https://video.cdninstagram.com/public.mp4"}],
        "comments_connection": {
            "edges": [
                {"node": {"pk": "1", "text": "Good food", "user": {"username": "never_store_me"}}},
                {"node": {"pk": "2", "text": "Hidden comment"}},
                {"node": {"pk": "3", "text": "Covered comment", "is_covered": True}},
            ],
            "page_info": {"has_next_page": True},
        },
    }


def test_only_target_media_and_visible_comments_are_retained():
    other = payload("recommendation")
    other["caption"]["text"] = "Unrelated venue"
    result = extract_public_data([{"data": [payload(), other]}], "target", "Good food Covered comment")
    assert result["caption"] == "Fixture Cafe in Coimbatore"
    assert result["comments"] == "Good food"
    assert result["browser"]["comment_sample_size"] == 1
    assert result["browser"]["more_comments_available"]
    assert not result["browser"]["video_downloaded"]
    assert "never_store_me" not in json.dumps(result)
    assert "Unrelated venue" not in json.dumps(result)


def test_missing_comments_are_unknown_and_duplicate_payloads_do_not_inflate_sample():
    source = payload()
    result = extract_public_data([source, source], "target", "Good food")
    assert result["browser"]["comment_sample_size"] == 1
    empty = extract_public_data([{"shortcode": "target", "caption": None}], "target", "Log in")
    assert empty["browser"]["status"] == "no_source_data"
    assert "comments" not in empty and "not evidence of zero" in empty["comments_coverage"]


@pytest.mark.parametrize(
    "url",
    [
        "http://www.instagram.com/reel/x/",
        "https://instagram.com.evil.test/x",
        "https://127.0.0.1/",
        "https://user:password@www.instagram.com/",
        "https://www.instagram.com:8000/",
        "file:///C:/secret",
    ],
)
def test_browser_network_rejects_unrelated_or_local_urls(url):
    assert not browser_url_allowed(url)


def test_permalink_and_media_url_boundaries():
    assert shortcode("https://www.instagram.com/reel/Target_123/") == "Target_123"
    with pytest.raises(ValueError):
        shortcode("https://www.instagram.com/some_profile/")
    row = payload()
    row["video_versions"] = [
        {"url": "https://attacker.test/video.mp4"},
        {"url": "https://www.instagram.com/accounts/login/"},
    ]
    result = extract_public_data([row], "target", "Good food")
    assert "media_url" not in result


def test_audio_manifest_only_accepts_clear_source_cdn_track():
    manifest = '<MPD xmlns="urn:mpeg:dash:schema:mpd:2011"><Period><AdaptationSet mimeType="audio/mp4"><Representation><BaseURL>https://video.fbcdn.net/audio.mp4</BaseURL></Representation></AdaptationSet></Period></MPD>'
    assert public_audio_reference(manifest) == "https://video.fbcdn.net/audio.mp4"
    assert public_audio_reference(manifest.replace("video.fbcdn.net", "127.0.0.1")) is None
    assert (
        public_audio_reference(manifest.replace("<Representation>", "<Representation><ContentProtection/>"))
        is None
    )
    assert public_audio_reference('<!DOCTYPE x [<!ENTITY secret SYSTEM "file:///x">]>' + manifest) is None


def test_rendered_page_snapshot_uses_real_browser_without_network():
    from playwright.async_api import async_playwright
    from app.browser_sources import read_public_snapshot

    async def run():
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            try:
                page = await browser.new_page()
                await page.route("**/*", lambda route: route.abort())
                await page.set_content(
                    '<div id="comments"></div><script type="application/json">'
                    + json.dumps(payload())
                    + '</script><script>document.getElementById("comments").textContent="Good food"</script>'
                )
                snap = await read_public_snapshot(page)
                return extract_public_data([json.loads(x) for x in snap["scripts"]], "target", snap["text"])
            finally:
                await browser.close()

    result = asyncio.run(run())
    assert result["comments"] == "Good food" and result["caption"] == "Fixture Cafe in Coimbatore"


def test_challenge_sets_cooldown_and_demo_never_launches_browser(client, monkeypatch):
    import app.browser_sources as module

    cfg = settings()
    monkeypatch.setattr(cfg, "instagram_browser_enabled", True)
    calls = []

    def run(*args, **kwargs):
        calls.append(True)
        return SimpleNamespace(returncode=0, stdout=json.dumps({"browser": {"status": "challenge"}}))

    monkeypatch.setattr(module.subprocess, "run", run)
    with Session() as db:
        with pytest.raises(Unavailable, match="disabled"):
            module.browser_instagram(db, "https://www.instagram.com/reel/target/")
        assert not calls
        monkeypatch.setattr(cfg, "app_mode", "local")
        assert (
            module.browser_instagram(db, "https://www.instagram.com/reel/target/")["browser"]["status"]
            == "challenge"
        )
        assert db.get(Counter, "instagram-browser-cooldown").value > datetime.now(timezone.utc).timestamp()
        with pytest.raises(Unavailable, match="cooling down"):
            module.browser_instagram(db, "https://www.instagram.com/reel/target/")
        assert len(calls) == 1


def test_browser_visit_limit_is_durable(client, monkeypatch):
    import app.browser_sources as module

    monkeypatch.setattr(settings(), "app_mode", "local")
    monkeypatch.setattr(settings(), "instagram_browser_enabled", True)
    monkeypatch.setattr(settings(), "browser_daily_limit", 1)
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *a, **k: SimpleNamespace(returncode=0, stdout='{"browser":{"status":"login_required"}}'),
    )
    with Session() as db:
        module.browser_instagram(db, "https://www.instagram.com/reel/target/")
        with pytest.raises(Unavailable, match="Daily"):
            module.browser_instagram(db, "https://www.instagram.com/reel/other/")


def test_browser_collection_receipt_and_private_media_are_not_exported(client, auth, monkeypatch):
    import app.browser_sources as module
    import app.research as research

    user = client.get("/api/me", headers=auth).json()["id"]
    monkeypatch.setattr(settings(), "app_mode", "local")
    monkeypatch.setattr(settings(), "instagram_browser_enabled", True)
    monkeypatch.setattr(
        module, "browser_instagram", lambda *a: extract_public_data([payload()], "target", "Good food")
    )
    monkeypatch.setattr(
        research,
        "download_media",
        lambda *a: {"mime": "video/mp4", "base64": base64.b64encode(b"test-video-bytes").decode()},
    )
    with Session() as db:
        case = start_case(db, user, "Coimbatore fixture")
        source = source_add(
            db, case, {"platform": "instagram", "url": "https://www.instagram.com/reel/target/"}
        )
        db.commit()
        collect_stage(db, case, None)
        assert source.content["browser"]["video_downloaded"]
        assert source.content["media_receipt"]["bytes"] == 16
        source.content = {
            **source.content,
            "audio_url": "https://video.fbcdn.net/private-signed-url",
            "speech_segments": [{"text": "raw transcript"}],
        }
        exported = public_case(db, case)["sources"][0]["content"]
        assert not {"media", "media_url", "audio_url"} & exported.keys()
        source.created_at = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        source.content = {**source.content, "fetched_at": source.created_at}
        purge_expired_sources(db)
        assert not {"media", "audio_url", "comments", "speech_segments"} & source.content.keys()
        assert source.content["media_receipt"]["bytes"] == 16


def test_failed_browser_keeps_public_caption(client, auth, monkeypatch):
    import app.browser_sources as module

    user = client.get("/api/me", headers=auth).json()["id"]
    monkeypatch.setattr(settings(), "app_mode", "local")
    monkeypatch.setattr(settings(), "instagram_browser_enabled", True)
    monkeypatch.setattr(module, "browser_instagram", lambda *a: {"browser": {"status": "login_required"}})
    with Session() as db:
        case = start_case(db, user, "Coimbatore fixture")
        source = source_add(
            db,
            case,
            {
                "platform": "instagram",
                "url": "https://www.instagram.com/reel/target/",
                "caption": "Previously fetched public caption",
            },
        )
        db.commit()
        collect_stage(db, case, None)
        assert source.content["caption"] == "Previously fetched public caption"
        assert source.content["browser"]["status"] == "login_required"


def test_local_track_join_produces_video_and_audio(tmp_path):
    from imageio_ffmpeg import get_ffmpeg_exe
    from app.browser_media import join_tracks

    video, audio = tmp_path / "video.mp4", tmp_path / "audio.mp4"
    subprocess.run(
        [
            get_ffmpeg_exe(),
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=160x120:d=1",
            "-y",
            str(video),
        ],
        check=True,
        timeout=15,
    )
    subprocess.run(
        [
            get_ffmpeg_exe(),
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=1",
            "-c:a",
            "aac",
            "-y",
            str(audio),
        ],
        check=True,
        timeout=15,
    )
    result = join_tracks({"base64": base64.b64encode(video.read_bytes()).decode()}, audio.read_bytes())
    joined = tmp_path / "joined.mp4"
    joined.write_bytes(base64.b64decode(result["base64"]))
    probe = subprocess.run(
        [get_ffmpeg_exe(), "-hide_banner", "-i", str(joined)], capture_output=True, timeout=15
    )
    assert b"Video:" in probe.stderr and b"Audio:" in probe.stderr


def test_speech_gap_and_transcript_storage(client, auth, monkeypatch):
    import app.research as research

    user = client.get("/api/me", headers=auth).json()["id"]
    monkeypatch.setattr(settings(), "app_mode", "local")
    monkeypatch.setattr(
        research,
        "analyze",
        lambda *a: {
            "status": "observations_only",
            "video_analyzed": True,
            "audio_gap": "",
            "_transcription": {
                "text": "Machine speech",
                "language": "ta",
                "segments": [{"start": 1, "end": 2, "text": "Machine speech"}],
                "model": "base",
            },
        },
    )
    with Session() as db:
        case = start_case(db, user, "Coimbatore test")
        source = source_add(
            db, case, {"platform": "instagram", "url": "https://www.instagram.com/reel/target/"}
        )
        source.content = {"media": {"base64": "test"}, "source_has_audio": True}
        db.commit()
        research.analysis_stage(db, case, SimpleNamespace(role="video"))
        assert source.content["speech_language"] == "ta"
        assert source.content["machine_transcript"]
        assert "_transcription" not in source.analysis["video"]
        source.analysis = {"video": {"status": "observations_only", "audio_gap": "Decode failed"}}
        result = research.verification_stage(db, case, None)
        assert any("Speech unavailable" in str(g) for g in result["gaps"])
        assert "media" not in source.content
        source.content = {**source.content, "source_has_audio": False}
        result = research.verification_stage(db, case, None)
        assert not any("Speech unavailable" in str(g) for g in result["gaps"])


def test_local_model_checks_cancel_and_renews_lease_without_external_quota(client, auth, monkeypatch):
    from app.db import Job
    from app.providers import ACTIVE_JOB
    from app.analysts import analyze
    import app.local_models as models

    user = client.get("/api/me", headers=auth).json()["id"]
    monkeypatch.setattr(settings(), "app_mode", "local")
    calls = []
    monkeypatch.setattr(models, "local_chat", lambda *a: calls.append(True) or "{}")
    with Session() as db:
        case = start_case(db, user, "Coimbatore test")
        job = Job(key="lease-test", kind="investigation", payload={"case_id": case.id})
        db.add(job)
        db.commit()
        token = ACTIVE_JOB.set(job.id)
        try:
            analyze(db, "caption", {"caption": "Test"})
            assert datetime.fromisoformat(job.lease_until) > datetime.now(timezone.utc)
            assert not db.get(Counter, "provider:" + datetime.now(timezone.utc).date().isoformat())
            case.state = "cancelled"
            db.commit()
            with pytest.raises(Unavailable, match="cancelled"):
                analyze(db, "caption", {"caption": "Test"})
            assert len(calls) == 1
        finally:
            ACTIVE_JOB.reset(token)


def test_comment_boundaries_and_distinct_emoji_are_preserved():
    from app.analysts import comment_sample

    result = comment_sample(["Two lines\nOne comment", "\U0001f525", "\u2764", "\U0001f525"])
    assert result["sample_size"] == 4
    assert result["distinct_texts"] == 3
    assert result["repeated_texts"] == 1
