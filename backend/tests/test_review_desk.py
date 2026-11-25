"""Quick review desk: shows spot-check rows with gathered evidence and writes answers back."""

from types import SimpleNamespace

import pytest

from app import review_desk
from app.config import settings
from app.db import IdentifiedSpot, Session

DECISIONS = (
    "﻿decision,place_name_before,detail,my_note,google_maps_link,you_agree (yes/no)\n"
    "reject,New Biryani place,not_a_venue,,https://maps.example/a,\n"
    "same_as,Dosa Corner RS Puram,Dosa Corner,,https://maps.example/b,\n"
)
OVERTURE = (
    "﻿name,category,area,overture_confidence,google_maps_link,exists_and_correct (yes/no/closed)\n"
    "Test Cafe,cafe,RS Puram,0.92,https://maps.example/c,\n"
)


@pytest.fixture
def desk(client, monkeypatch, tmp_path):
    monkeypatch.setenv("APP_MODE", "local")
    settings.cache_clear()
    (tmp_path / "spotcheck-claude-decisions-50.csv").write_text(DECISIONS, encoding="utf-8")
    (tmp_path / "spotcheck-overture-50.csv").write_text(OVERTURE, encoding="utf-8")
    monkeypatch.setattr(review_desk, "SHEET_DIR", tmp_path)
    token = client.post("/api/auth/local").json()["access_token"]
    auth = {"Authorization": "Bearer " + token}
    owner = client.get("/api/me", headers=auth).json()["id"]
    yield SimpleNamespace(client=client, auth=auth, owner=owner, dir=tmp_path)
    settings.cache_clear()


def test_items_explain_each_row_and_attach_evidence(desk):
    with Session() as db:
        row = IdentifiedSpot(user_id=desk.owner, identity_key="k:test-cafe", name="Test Cafe", category="cafe", area="RS Puram")
        row.data = {"coordinates": {"lat": 11.01, "lng": 76.95}, "corroboration": "multi_source", "sources": [{"kind": "osm"}]}
        db.add(row)
        db.commit()
    body = desk.client.get("/api/admin/review-desk/items", headers=desk.auth).json()
    assert body["total"] == 3 and body["done"] == 0
    first, second, third = body["items"]
    assert "isn't one specific place" in first["claim"] and first["options"] == ["yes", "no"]
    assert "merged this into “Dosa Corner”" in second["claim"]
    assert third["options"] == ["yes", "no", "closed"]
    assert "11.01,76.95" in third["embed"]
    assert third["matches"][0]["sources"] == ["osm"]
    assert "Another source agrees it exists." in third["hints"]


def test_answer_is_written_to_the_sheet_and_can_be_changed(desk):
    post = lambda **kw: desk.client.post("/api/admin/review-desk/answer", json=kw, headers=desk.auth)
    assert post(sheet="decisions", row=1, answer="Yes").status_code == 200
    assert post(sheet="overture", row=0, answer="closed").status_code == 200
    text = (desk.dir / "spotcheck-claude-decisions-50.csv").read_text(encoding="utf-8")
    assert text.startswith("﻿")
    assert text.splitlines()[2].endswith(",yes")
    assert (desk.dir / "spotcheck-overture-50.csv").read_text(encoding="utf-8-sig").splitlines()[1].endswith(",closed")
    assert post(sheet="decisions", row=1, answer="no").status_code == 200
    assert desk.client.get("/api/admin/review-desk/items", headers=desk.auth).json()["done"] == 2


@pytest.mark.parametrize("payload", [
    {"sheet": "decisions", "row": 0, "answer": "closed"},
    {"sheet": "overture", "row": 0, "answer": "maybe"},
    {"sheet": "nope", "row": 0, "answer": "yes"},
])
def test_rejects_unsupported_answers(desk, payload):
    assert desk.client.post("/api/admin/review-desk/answer", json=payload, headers=desk.auth).status_code == 400


def test_unknown_row_is_404(desk):
    r = desk.client.post("/api/admin/review-desk/answer", json={"sheet": "decisions", "row": 9, "answer": "yes"}, headers=desk.auth)
    assert r.status_code == 404


def test_items_list_source_links_instagram_first_with_frames(desk):
    with Session() as db:
        row = IdentifiedSpot(user_id=desk.owner, identity_key="k:test-cafe", name="Test Cafe", category="cafe", area="RS Puram")
        row.data = {"sources": [
            {"type": "web_candidate", "url": "https://www.zomato.com/coimbatore/test-cafe"},
            {"type": "instagram", "url": "https://www.instagram.com/p/AbC_12-x/"},
            {"type": "overture", "url": "https://www.facebook.com/305126859349544"},
            {"type": "web_candidate", "url": "https://www.zomato.com/coimbatore/test-cafe"},
            {"type": "web", "url": "http://insecure.example/page"},
        ], "website_candidates": ["https://testcafe.example"]}
        db.add(row)
        db.commit()
    third = desk.client.get("/api/admin/review-desk/items", headers=desk.auth).json()["items"][2]
    links = third["links"]
    assert [l["kind"] for l in links] == ["instagram", "web_candidate", "overture", "website"]
    assert links[0]["embed"] == "https://www.instagram.com/p/AbC_12-x/embed/"
    assert links[0]["label"] == "Instagram post · instagram.com"
    assert links[1]["embed"] == "" and links[1]["label"] == "Web page · zomato.com"
    assert links[2]["embed"].startswith("https://www.facebook.com/plugins/page.php?href=https%3A%2F%2Fwww.facebook.com%2F305126859349544")


def _mock(handler):
    import httpx
    return httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False)


def test_preview_reads_frame_rules_and_page_summary(monkeypatch):
    import httpx
    monkeypatch.setattr(review_desk, "_public_https", lambda url: url.startswith("https://"))
    review_desk.PREVIEW_CACHE.clear()
    page = '<html><head><title>Raw</title><meta property="og:title" content="Test &amp; Cafe"><meta name="description" content="Coffee in RS Puram"></head></html>'

    def handler(request):
        if request.url.path == "/blocked":
            return httpx.Response(200, headers={"content-type": "text/html", "x-frame-options": "SAMEORIGIN"}, text=page)
        if request.url.path == "/csp":
            return httpx.Response(200, headers={"content-type": "text/html", "content-security-policy": "default-src 'self'; frame-ancestors 'self'"}, text=page)
        if request.url.path == "/hop":
            return httpx.Response(301, headers={"location": "/open"})
        if request.url.path == "/downgrade":
            return httpx.Response(302, headers={"location": "http://a.example/open"})
        return httpx.Response(200, headers={"content-type": "text/html; charset=utf-8"}, text=page)

    blocked = review_desk.page_preview("https://a.example/blocked", fetch=_mock(handler))
    assert blocked["frameable"] is False and blocked["title"] == "Test & Cafe" and blocked["description"] == "Coffee in RS Puram"
    assert review_desk.page_preview("https://a.example/csp", fetch=_mock(handler))["frameable"] is False
    hop = review_desk.page_preview("https://a.example/hop", fetch=_mock(handler))
    assert hop["frameable"] is True and hop["url"] == "https://a.example/open"
    down = review_desk.page_preview("https://a.example/downgrade", fetch=_mock(handler))
    assert down["frameable"] is False and "public https" in down["error"]
    insta = review_desk.page_preview("https://www.instagram.com/p/AbC/", fetch=_mock(handler))
    assert insta["embed"] == "https://www.instagram.com/p/AbC/embed/" and insta["frameable"] is True


def test_preview_rejects_non_https(desk):
    r = desk.client.get("/api/admin/review-desk/preview", params={"url": "http://a.example"}, headers=desk.auth)
    assert r.status_code == 400


def test_page_shot_renders_once_then_serves_from_cache(monkeypatch, tmp_path):
    monkeypatch.setattr(review_desk, "SHOT_DIR", tmp_path)
    monkeypatch.setattr(review_desk, "_public_https", lambda url: True)
    calls = []

    def fake_run(cmd, **kw):
        calls.append(cmd)
        open(cmd[-1], "wb").write(b"\xff\xd8jpeg")

    first = review_desk.page_shot_path("https://a.example/menu", run=fake_run)
    again = review_desk.page_shot_path("https://a.example/menu", run=fake_run)
    assert first == again and first.read_bytes().startswith(b"\xff\xd8")
    assert len(calls) == 1 and calls[0][1:4] == ["-m", "app.page_shot", "https://a.example/menu"]


def test_page_shot_refuses_private_addresses(monkeypatch, tmp_path):
    monkeypatch.setattr(review_desk, "SHOT_DIR", tmp_path)
    assert review_desk.page_shot_path("https://localhost/admin", run=lambda *a, **k: None) is None


def test_page_shot_remembers_pages_that_render_nothing(monkeypatch, tmp_path):
    monkeypatch.setattr(review_desk, "SHOT_DIR", tmp_path)
    monkeypatch.setattr(review_desk, "_public_https", lambda url: True)
    calls = []
    assert review_desk.page_shot_path("https://blank.example/", run=lambda cmd, **kw: calls.append(cmd)) is None
    assert review_desk.page_shot_path("https://blank.example/", run=lambda cmd, **kw: calls.append(cmd)) is None
    assert len(calls) == 1
