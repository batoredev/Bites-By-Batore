import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.config import settings
from app.db import Base, engine, Session, Venue, ResearchSource, ResearchCorrection, Investigation
from app.main import app
from app.research import start_case, source_add
from app.learning import relevant_examples
from app.providers import Unavailable


@pytest.fixture
def local_client(monkeypatch):
    Base.metadata.drop_all(engine)
    cfg = settings()
    monkeypatch.setattr(cfg, "app_mode", "local")
    monkeypatch.setattr(cfg, "local_search_enabled", True)
    monkeypatch.setattr(cfg, "autonomous_discovery", False)
    with TestClient(app) as client:
        token = client.post("/api/auth/local").json()["access_token"]
        client.headers["Authorization"] = "Bearer " + token
        yield client


def test_local_persistent_operator_no_fixtures_no_supabase(local_client):
    first = local_client.get("/api/me").json()
    token = local_client.post("/api/auth/local").json()["access_token"]
    second = local_client.get("/api/me", headers={"Authorization": "Bearer " + token}).json()
    assert first["id"] == second["id"] == "local-operator"
    assert first["is_admin"]
    with Session() as db:
        assert not list(db.scalars(select(Venue)))
    assert local_client.get("/api/config").json()["supabase_url"] == ""
    assert local_client.post("/api/auth/demo").status_code == 404
    assert local_client.post("/api/auth/local", headers={"Origin": "https://evil.example"}).status_code == 403
    assert local_client.get("/api/me", headers={"Host": "evil.example"}).status_code == 403


def add_source():
    with Session() as db:
        case = start_case(db, "local-operator", "Coimbatore sushi")
        source = source_add(
            db,
            case,
            {
                "url": "https://www.instagram.com/reel/test123/",
                "platform": "instagram",
                "caption": "Yukiira Peelamedu sushi",
            },
        )
        db.commit()
        return source.id


def test_correction_retrieval_scope_revoke_and_erasure(local_client):
    source_id = add_source()
    response = local_client.post(
        f"/api/admin/research-sources/{source_id}/corrections",
        json={
            "role": "caption",
            "scope": "Yukiira",
            "original": "Rs 500 per person",
            "corrected": "Rs 500 is the price of one dish, not per person",
            "reason": "The menu labels this as a single sushi roll serving.",
        },
    )
    assert response.status_code == 200
    correction_id = response.json()["id"]
    with Session() as db:
        source = db.get(ResearchSource, source_id)
        assert relevant_examples(db, "local-operator", source, "caption")[0]["correction_id"] == correction_id
        assert relevant_examples(db, "other-user", source, "caption") == []
        assert relevant_examples(db, "local-operator", source, "video") == []
        source.content = {"caption": "Unrelated sushi cafe"}
        assert relevant_examples(db, "local-operator", source, "caption") == []
    assert len(local_client.get("/api/me/export").json()["research_corrections"]) == 1
    assert local_client.delete(f"/api/admin/research-corrections/{correction_id}").status_code == 200
    with Session() as db:
        assert relevant_examples(db, "local-operator", db.get(ResearchSource, source_id), "caption") == []
    assert local_client.delete("/api/me/data").status_code == 200
    with Session() as db:
        assert not list(db.scalars(select(ResearchCorrection)))


def test_autonomous_frontier_no_examples_dedup_pause(local_client):
    response = local_client.post("/api/admin/research-next")
    assert response.status_code == 200
    first = response.json()
    assert "Coimbatore" in first["query"]
    assert local_client.post("/api/admin/research-next").json()["id"] == first["id"]
    with Session() as db:
        db.get(Investigation, first["id"]).state = "review"
        db.commit()
    second = local_client.post("/api/admin/research-next").json()
    assert second["query"] != first["query"]
    assert local_client.post("/api/admin/research-control", json={"paused": True}).status_code == 200
    assert local_client.post("/api/admin/research-next").status_code == 409


def test_local_model_never_calls_hosted_provider(local_client, monkeypatch):
    from app.analysts import analyze, AnalystResult
    import app.analysts as analysts
    import app.local_models as models

    monkeypatch.setattr(analysts, "call", lambda *a, **kw: pytest.fail("Hosted AI called"))
    monkeypatch.setattr(
        models, "local_chat", lambda *a, **kw: AnalystResult(summary="Local result").model_dump_json()
    )
    with Session() as db:
        result = analyze(db, "caption", {"caption": "Test"})
    assert result["execution"] == "local"
    assert not result["video_analyzed"]
    with pytest.raises(Unavailable, match="video bytes"):
        analyze(None, "video", {}, video_url="https://www.youtube.com/watch?v=12345678901")
    monkeypatch.setattr(settings(), "ollama_url", "https://cloud.example")
    with pytest.raises(Unavailable, match="loopback"):
        models.endpoint()


def test_local_evidence_drops_commenter_candidates_and_non_prices(local_client, monkeypatch):
    from app.analysts import analyze
    import app.local_models as models

    result = {
        "observations": [{"text": "Caption names a restaurant", "basis": "caption"}] * 2,
        "venue_candidates": [
            {"name": "Fixture Cafe", "price_claim": "Fresh flavours"},
            {"name": "Unknown Venue"},
        ],
    }
    monkeypatch.setattr(models, "local_chat", lambda *a: json.dumps(result))
    with Session() as db:
        actual = analyze(db, "caption", {"caption": "Fixture Cafe has fresh flavours"})
        assert len(actual["observations"]) == 1
        assert len(actual["venue_candidates"]) == 1
        assert actual["venue_candidates"][0]["price_claim"] == ""
        result["observations"] = []
        actual = analyze(db, "comments", {"comments": "@friend sushi venu"})
        assert actual["venue_candidates"] == []


def test_text_schema_has_no_invented_clip_timestamps(local_client, monkeypatch):
    import app.local_models as models

    captured = []

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"done_reason": "stop", "message": {"content": "{}"}}

    class Client:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, url, **kwargs):
            captured.append(kwargs["json"])
            return Response()

    monkeypatch.setattr(models.httpx, "Client", Client)
    models.local_chat("Read comments", {"comments": "Location?"}, {})
    properties = captured[0]["format"]["properties"]
    assert properties["observations"]["items"]["properties"]["timestamp_seconds"] == {"type": "null"}
    assert properties["venue_candidates"]["maxItems"] == 0


def test_public_search_remains_lead_until_collected(local_client, monkeypatch):
    from app.jobs import run_once
    import app.public_sources as public
    import app.local_models as models
    from app.analysts import AnalystResult

    monkeypatch.setattr(
        public,
        "public_search",
        lambda db, query: [
            {
                "url": "https://www.instagram.com/reel/test123/",
                "platform": "instagram",
                "search_preview": "A sushi restaurant in Coimbatore",
                "snippet_is_not_caption": True,
            }
        ],
    )
    monkeypatch.setattr(
        public,
        "public_instagram",
        lambda db, url: {"caption": "Yukiira Peelamedu sushi", "comments_coverage": "unavailable"},
    )
    calls = []

    def chat(prompt, content, schema, frames=None):
        calls.append(content)
        return AnalystResult(summary="Caption mentions a sushi restaurant").model_dump_json()

    monkeypatch.setattr(models, "local_chat", chat)
    case = local_client.post("/api/admin/research-next").json()
    for _ in range(10):
        run_once()
    detail = local_client.get(f"/api/investigations/{case['id']}").json()
    assert detail["sources"][0]["analysis"]["caption"]["execution"] == "local"
    assert detail["sources"][0]["analysis"]["video"]["status"] == "unavailable"
    assert calls and "reviewed_examples" in calls[0]
    with Session() as db:
        assert not list(db.scalars(select(Venue)))


def test_no_speech_claim_when_local_audio_unavailable(local_client, monkeypatch):
    from app.analysts import analyze
    import app.local_models as models
    import app.media as media

    monkeypatch.setattr(media, "extract_frames", lambda *a: [{"seconds": 0, "base64": "image"}])

    def no_audio(_):
        raise Unavailable("No audio")

    monkeypatch.setattr(models, "transcribe", no_audio)
    monkeypatch.setattr(
        models,
        "local_chat",
        lambda *a: json.dumps({"observations": [{"text": "Spoken address", "basis": "speech"}]}),
    )
    with pytest.raises(Unavailable, match="modality"):
        analyze(None, "video", {}, media={"mime": "video/mp4", "base64": "test"})


def test_engagement_is_not_price_and_duplicates_collapse(local_client, monkeypatch):
    from app.analysts import analyze
    import app.local_models as models

    candidate = {
        "name": "Test Cafe",
        "address_clues": ["Coimbatore"],
        "price_claim": "2,310 likes, 293 comments",
    }
    monkeypatch.setattr(
        models, "local_chat", lambda *a: json.dumps({"venue_candidates": [candidate, candidate]})
    )
    result = analyze(None, "caption", {"caption": "Test Cafe"})
    assert len(result["venue_candidates"]) == 1
    assert result["venue_candidates"][0]["price_claim"] == ""
    assert any("engagement" in x for x in result["unknowns"])


def test_public_metadata_counts_are_exact_and_unknowns_stay_unknown():
    from app.public_sources import metadata_details

    result = metadata_details('2,310 likes, 293 comments - cafe_test on August 10, 2026: "Sushi"')
    assert result["likes"] == 2310 and result["creator"] == "cafe_test"
    assert metadata_details("10K likes - cafe_test") == {}


def test_frames_do_not_seek_past_real_duration(tmp_path, monkeypatch):
    import base64
    import subprocess
    from imageio_ffmpeg import get_ffmpeg_exe
    from app.media import extract_frames

    target = tmp_path / "short.mp4"
    subprocess.run(
        [
            get_ffmpeg_exe(),
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=red:s=160x120:d=1",
            "-y",
            str(target),
        ],
        check=True,
        timeout=20,
    )
    monkeypatch.setattr(settings(), "media_max_frames", 4)
    frames = extract_frames({"base64": base64.b64encode(target.read_bytes()).decode()}, [0, 0.5, 15, 30])
    assert [f["seconds"] for f in frames] == [0, 0.5]


def test_public_caption_does_not_block_configured_full_collection(local_client, monkeypatch):
    import app.research as research
    from app.social import normalize_item

    monkeypatch.setattr(settings(), "instagram_provider", "apify")
    starts = []

    def start(*args):
        starts.append(True)
        return {"id": "mock-run"}

    monkeypatch.setattr(research, "apify_start", start)
    monkeypatch.setattr(
        research,
        "apify_poll",
        lambda *a: [
            normalize_item(
                {
                    "url": "https://www.instagram.com/reel/test123/",
                    "caption": "Provider caption",
                    "latestComments": [{"text": "A firsthand comment"}],
                }
            )
        ],
    )
    source_id = add_source()
    with Session() as db:
        source = db.get(ResearchSource, source_id)
        case = db.get(Investigation, source.case_id)
        research.collect_stage(db, case, None)
        assert source.content["comments"] == "A firsthand comment"
        source.state = "lead"
        db.commit()
        research.collect_stage(db, case, None)
    assert len(starts) == 1
