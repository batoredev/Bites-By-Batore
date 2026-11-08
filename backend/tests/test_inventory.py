from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import select
from app.config import settings
from app.db import Session, ResearchTask, IdentifiedSpot, Venue, Claim, now
from app.providers import DeferredCollection
from app import research
from app.spots import upsert_spot
from app.inventory import parse_document
from app.recency import recency_key, publication_date


def test_recency_uses_publication_not_fetch_time_or_popularity():
    rows = [
        {"id": "old", "published_at": "2020-01-01T00:00:00Z", "likes": 999999},
        {"id": "undated", "fetched_at": now()},
        {"id": "new", "published_at": "2025-12-01T00:00:00Z"},
    ]
    assert [r["id"] for r in sorted(rows, key=recency_key, reverse=True)] == ["new", "old", "undated"]
    assert publication_date("2099-01-01") is None
    assert publication_date("July 12, 2024").startswith("2024-07-12")


def test_discovery_retains_every_found_source_in_latest_order(client, auth, monkeypatch):
    import app.public_sources as public

    user = client.get("/api/me", headers=auth).json()["id"]
    monkeypatch.setattr(settings(), "app_mode", "local")
    monkeypatch.setattr(settings(), "local_search_enabled", True)
    monkeypatch.setattr(settings(), "research_max_sources", 2)
    monkeypatch.setattr(
        public,
        "public_search",
        lambda *a: [
            {
                "platform": "instagram",
                "url": f"https://www.instagram.com/reel/source{i}/",
                "published_at": f"2025-01-0{i}T00:00:00Z",
                "title": "Coimbatore sushi",
            }
            for i in range(1, 7)
        ],
    )
    with Session() as db:
        case = research.start_case(db, user, "Coimbatore sushi")
        task = db.scalar(
            select(ResearchTask).where(ResearchTask.case_id == case.id, ResearchTask.role == "discovery")
        )
        result = research.discover_stage(db, case, task)
        assert result["source_count"] == 6
        assert [s.canonical_url.split("/")[-2] for s in research.case_sources(db, case)] == [
            f"source{i}" for i in range(6, 0, -1)
        ]


def test_streaming_batches_all_sources_and_saves_spots_without_publication(client, auth, monkeypatch):
    user = client.get("/api/me", headers=auth).json()["id"]
    monkeypatch.setattr(settings(), "app_mode", "local")
    monkeypatch.setattr(settings(), "research_streaming", True)
    monkeypatch.setattr(settings(), "research_max_sources", 2)
    monkeypatch.setattr(
        research,
        "analyze",
        lambda db, role, content, *a, **k: {
            "status": "observations_only",
            "venue_candidates": [
                {"name": content["caption"], "address_clues": ["Peelamedu"], "dish_or_activity": "Sushi"}
            ],
            "observations": [],
        },
    )
    with Session() as db:
        case = research.start_case(
            db,
            user,
            "Coimbatore sushi",
            seed_sources=[
                {
                    "platform": "instagram",
                    "url": f"https://www.instagram.com/reel/source{i}/",
                    "caption": f"Fixture cafe {i}",
                }
                for i in range(5)
            ],
        )
        for _ in range(2):
            with pytest.raises(research.PendingSource):
                research.collect_stage(db, case, None)
        research.collect_stage(db, case, None)
        rows = research.case_sources(db, case)
        assert len(rows) == 5 and all(s.content.get("streamed") for s in rows)
        assert len(list(db.scalars(select(IdentifiedSpot).where(IdentifiedSpot.user_id == user)))) == 5
        assert not list(db.scalars(select(Venue).where(Venue.is_demo.is_(False))))
        research.collect_stage(db, case, None)
        assert len(list(db.scalars(select(IdentifiedSpot).where(IdentifiedSpot.user_id == user)))) == 5


def test_daily_limit_preserves_pending_source(client, auth, monkeypatch):
    import app.browser_sources as browser

    user = client.get("/api/me", headers=auth).json()["id"]
    monkeypatch.setattr(settings(), "app_mode", "local")
    monkeypatch.setattr(settings(), "instagram_browser_enabled", True)
    monkeypatch.setattr(
        browser, "browser_instagram", lambda *a: (_ for _ in ()).throw(DeferredCollection("Daily cap", 3600))
    )
    with Session() as db:
        case = research.start_case(
            db,
            user,
            "Coimbatore sushi",
            seed_sources=[
                {
                    "platform": "instagram",
                    "url": "https://www.instagram.com/reel/waiting/",
                    "caption": "Fixture source",
                }
            ],
        )
        with pytest.raises(research.PendingSource) as error:
            research.collect_stage(db, case, None)
        assert error.value.retry_seconds == 3600
        source = research.case_sources(db, case)[0]
        assert source.state == "lead"
        assert source.content["deferred_reason"] == "Daily cap"
        assert "collection_error" not in source.content


def test_official_menu_and_directions_are_proposals_not_per_person_cost():
    html = '<span data-hook="item.name">Fixture soup</span><span data-hook="item.price">₹240</span><a href="https://www.google.com/maps/dir//11.01,76.96">Directions</a><a href="/menu">Menu</a>'
    result = parse_document(html, "https://official.example/")
    assert result["offerings"][0]["price_inr"] == 240
    assert result["offerings"][0]["unit"] == "item"
    assert result["coordinates"]["lat"] == 11.01
    assert result["menu_links"] == ["https://official.example/menu"]
    assert "price_per_person" not in result


def test_spot_ownership_export_erasure_and_no_venue_creation(client, auth):
    from app.db import Job

    user = client.get("/api/me", headers=auth).json()["id"]
    with Session() as db:
        owned = upsert_spot(
            db,
            user,
            "Fixture spot",
            area="Peelamedu",
            data={"sources": [{"url": "https://official.example", "basis": "Test only"}]},
        )
        upsert_spot(db, "another-owner", "Private other spot")
        db.add(Job(key="owned-enrich", kind="spot_enrich", payload={"spot_id": owned.id}))
        db.add(Job(key="other-inventory", kind="spot_inventory", payload={"user_id": "another-owner"}))
        db.commit()
    result = client.get("/api/admin/spots", headers=auth).json()
    assert result["total"] == 1 and result["spots"][0]["name"] == "Fixture spot"
    assert len(client.get("/api/me/export", headers=auth).json()["identified_spots"]) == 1
    assert client.delete("/api/me/data", headers=auth).status_code == 200
    with Session() as db:
        assert not list(db.scalars(select(IdentifiedSpot).where(IdentifiedSpot.user_id == user)))
        assert (
            len(list(db.scalars(select(IdentifiedSpot).where(IdentifiedSpot.user_id == "another-owner"))))
            == 1
        )
        assert not db.scalar(select(Job).where(Job.key == "owned-enrich"))
        assert db.scalar(select(Job).where(Job.key == "other-inventory"))


def test_complete_facts_do_not_publish_without_explicit_location_approval(client, auth):
    from app.evidence import apply_claim

    with Session() as db:
        venue = Venue(
            name="Fixture pending",
            category="food",
            area="Peelamedu",
            address="Test-only address",
            lat=11,
            lng=77,
            is_demo=True,
            status="pending",
            details={"branch_confirmed": True},
        )
        db.add(venue)
        db.flush()
        for field, value in [("price_per_person", 500), ("hours", {"0": [[600, 1200]]}), ("closed", False)]:
            claim = Claim(
                venue_id=venue.id,
                field=field,
                value={"value": value},
                source_url="https://official.example",
                source_type="official",
                source_group="fixture",
                observed_at=now(),
                expires_at=(datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
            )
            db.add(claim)
            db.flush()
            apply_claim(db, claim, "trusted-feed")
        db.commit()
        venue_id = venue.id
        assert venue.status == "pending"
    response = client.post(
        f"/api/admin/venues/{venue_id}/publish",
        headers=auth,
        json={"decision": "approve", "reason": "Operator checked this exact location and essential evidence"},
    )
    assert response.status_code == 200, response.text
    with Session() as db:
        venue = db.get(Venue, venue_id)
        assert venue.status == "published" and venue.details["location_approval"]["by"]


def test_meta_cursor_continues_without_top_three_cutoff(client, monkeypatch):
    from app import social

    monkeypatch.setattr(settings(), "instagram_provider", "meta")
    monkeypatch.setattr(social, "hashtags", lambda query: ["coimbatorefood"])
    calls = []

    def response(db, path, params):
        calls.append((path, dict(params)))
        if path == "ig_hashtag_search":
            return {"data": [{"id": "123"}]}
        start = 4 if params.get("after") else 0
        return {
            "data": [
                {
                    "id": str(i),
                    "permalink": f"https://www.instagram.com/reel/code{i}/",
                    "timestamp": "2025-01-01T00:00:00Z",
                }
                for i in range(start, start + 4)
            ],
            "paging": {}
            if start
            else {"next": "https://graph.facebook.com/ignored", "cursors": {"after": "cursor-a"}},
        }

    monkeypatch.setattr(social, "meta_get", response)
    state = {}
    first = social.instagram_discover(None, "food", state)
    assert len(first) == 4 and state["after"] == "cursor-a"
    second = social.instagram_discover(None, "food", state)
    assert len(second) == 4 and state["done"]
    assert calls[-1][1]["after"] == "cursor-a"


def test_date_probes_resume_without_dropping_sources_or_researching(client, auth, monkeypatch):
    import app.public_sources as public

    user = client.get("/api/me", headers=auth).json()["id"]
    monkeypatch.setattr(settings(), "app_mode", "local")
    monkeypatch.setattr(settings(), "local_search_enabled", True)
    searched = []
    monkeypatch.setattr(
        public,
        "public_search",
        lambda *a: (
            searched.append(True)
            or [
                {"platform": "instagram", "url": f"https://www.instagram.com/reel/probe{i}/"}
                for i in range(10)
            ]
        ),
    )

    def metadata(db, url):
        i = int(url.split("probe")[1].split("/")[0])
        return {"published_at": f"2025-01-{i + 1:02}T00:00:00Z", "caption": "Coimbatore cafe"}

    monkeypatch.setattr(public, "public_instagram", metadata)
    with Session() as db:
        case = research.start_case(db, user, "Coimbatore cafe")
        task = db.scalar(
            select(ResearchTask).where(ResearchTask.case_id == case.id, ResearchTask.role == "discovery")
        )
        with pytest.raises(research.PendingSource):
            research.discover_stage(db, case, task)
        result = research.discover_stage(db, case, task)
        assert result["source_count"] == 10 and len(searched) == 1
        assert research.case_sources(db, case)[0].canonical_url.endswith("/probe9/")


def test_local_video_inspects_every_frame_group(client, monkeypatch):
    import json
    import app.local_models as models
    import app.media as media
    from app.analysts import analyze

    monkeypatch.setattr(settings(), "app_mode", "local")
    frames = [{"seconds": float(i), "mime": "image/jpeg", "base64": "fixture"} for i in range(8)]
    monkeypatch.setattr(media, "extract_frames", lambda *a: frames)
    monkeypatch.setattr(models, "transcribe", lambda *a: {"text": "", "segments": []})
    seen = []

    def chat(prompt, content, schema, group):
        seen.extend(f["seconds"] for f in group)
        return json.dumps(
            {
                "observations": [
                    {
                        "text": f"Frame group begins at {group[0]['seconds']}",
                        "basis": "visual",
                        "timestamp_seconds": group[0]["seconds"],
                    }
                ]
            }
        )

    monkeypatch.setattr(models, "local_chat", chat)
    result = analyze(None, "video", {}, media={"base64": "fixture", "mime": "video/mp4"})
    assert seen == list(map(float, range(8)))
    assert len(result["observations"]) == 2
    assert result["sampling"] == seen


def test_actual_scene_transition_is_sampled(tmp_path, monkeypatch):
    import base64
    import subprocess
    from imageio_ffmpeg import get_ffmpeg_exe
    from app.media import extract_frames

    monkeypatch.setattr(settings(), "media_max_frames", 4)
    video = tmp_path / "scene-fixture.mp4"
    subprocess.run(
        [
            get_ffmpeg_exe(),
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=red:s=160x120:d=1",
            "-f",
            "lavfi",
            "-i",
            "color=blue:s=160x120:d=1",
            "-filter_complex",
            "[0:v][1:v]concat=n=2:v=1:a=0[v]",
            "-map",
            "[v]",
            "-y",
            str(video),
        ],
        check=True,
        timeout=20,
    )
    frames = extract_frames({"base64": base64.b64encode(video.read_bytes()).decode(), "mime": "video/mp4"})
    assert any(abs(f["seconds"] - 1) < 0.08 for f in frames)
    assert len(frames) <= 4 and frames[0]["seconds"] == 0


def test_prepared_spot_is_pending_and_cannot_enter_suggestions(client, auth):
    user = client.get("/api/me", headers=auth).json()["id"]
    with Session() as db:
        row = upsert_spot(db, user, "Fixture new location", area="Peelamedu")
        db.commit()
        spot_id = row.id
    body = {
        "venue": {
            "name": "Fixture new location",
            "category": "cafe",
            "area": "Peelamedu",
            "address": "Test-only street address",
            "lat": 11.01,
            "lng": 76.96,
            "details": {"branch_confirmed": True},
        },
        "evidence_url": "https://official.example/branch",
        "reason": "Explicit test operator branch confirmation",
    }
    first = client.post(f"/api/admin/spots/{spot_id}/prepare", headers=auth, json=body)
    assert first.status_code == 200, first.text
    venue_id = first.json()["venue_id"]
    assert (
        client.post(f"/api/admin/spots/{spot_id}/prepare", headers=auth, json=body).json()["venue_id"]
        == venue_id
    )
    with Session() as db:
        assert db.get(Venue, venue_id).status == "pending"
    assert venue_id not in [v["id"] for v in client.get("/api/venues", headers=auth).json()]
    assert (
        client.post(
            f"/api/admin/venues/{venue_id}/publish",
            headers=auth,
            json={"decision": "approve", "reason": "Test still lacks essential facts"},
        ).status_code
        == 422
    )


def test_web_enrichment_does_not_promote_search_pages_to_official(client, auth, monkeypatch):
    import json
    from types import SimpleNamespace
    import app.spot_search as module

    user = client.get("/api/me", headers=auth).json()["id"]
    monkeypatch.setattr(module, "quota", lambda db, **kwargs: None)
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *a, **k: SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                [{"href": "https://directory.example/fixture", "title": "Fixture Coimbatore menu"}]
            ),
        ),
    )
    monkeypatch.setattr(
        module,
        "read_official_html",
        lambda *a, **k: (
            '<p>Fixture restaurant Coimbatore</p><span data-hook="item.name">Soup</span><span data-hook="item.price">₹100</span>'
        ),
    )
    with Session() as db:
        row = upsert_spot(db, user, "Fixture restaurant")
        db.commit()
        result = module.enrich_spot(db, row.id)
        assert result["remaining"] == 0
        db.expire(row)
        assert row.data["web_search_results"][0]["status"] == "collected_unverified"
        assert row.data["sources"][0]["type"] == "web_candidate"
        assert "unverified" in row.data["offerings"][0]["basis"]
        assert row.status == "identified" and not row.venue_id
