"""Quick review desk: shows spot-check rows with gathered evidence and writes answers back."""

import csv
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


def test_owner_can_correct_the_location_from_the_desk(desk):
    from app.db import Venue

    with Session() as db:
        venue = Venue(name="Test Cafe", category="cafe", area="RS Puram", address="", lat=11.0, lng=76.9,
                      tags=[], details={}, status="published", is_demo=False)
        db.add(venue)
        db.flush()
        row = IdentifiedSpot(user_id=desk.owner, identity_key="k:test-cafe", name="Test Cafe", category="cafe",
                             area="RS Puram", status="approved", venue_id=venue.id)
        row.data = {"coordinates": {"lat": 11.0, "lng": 76.9}}
        db.add(row)
        db.commit()
        spot_id, venue_id = row.id, venue.id

    def move(**kw):
        return desk.client.post("/api/admin/review-desk/location", headers=desk.auth,
                                json={"sheet": "overture", "row": 0, **kw})

    assert move(spot_id="someone-else", maps_url="11.02, 76.96").status_code == 409
    assert move(spot_id=spot_id, maps_url="13.08, 80.27").status_code == 422
    body = move(spot_id=spot_id, maps_url="11.0200, 76.9600").json()
    assert "11.02,76.96" in body["embed"] and "Location corrected by owner" in body["note"]
    with Session() as db:
        spot, venue = db.get(IdentifiedSpot, spot_id), db.get(Venue, venue_id)
        assert (venue.lat, venue.lng) == (11.02, 76.96)
        assert spot.data["coordinates"]["basis"] == "Coordinates supplied by the owner"
        assert spot.data["operator_edits"][-1]["from"] == "11.0,76.9"
    # Fixing it again does not repeat the note.
    assert move(spot_id=spot_id, maps_url="11.0210, 76.9610").json()["note"].count("Location corrected") == 1


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
    monkeypatch.setattr(review_desk, "_pinned_ip", lambda url: "93.184.216.34" if url.startswith("https://") else None)
    review_desk.PREVIEW_CACHE.clear()
    page = '<html><head><title>Raw</title><meta property="og:title" content="Test &amp; Cafe"><meta name="description" content="Coffee in RS Puram"></head></html>'

    seen = []

    def handler(request):
        seen.append((request.url.host, request.headers["host"], request.extensions.get("sni_hostname")))
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
    assert seen[0] == ("93.184.216.34", "a.example", "a.example")  # connects to the checked IP, verifies the real name
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


def test_public_ip_refuses_any_private_answer(monkeypatch):
    from app import page_shot
    answer = lambda *ips: (lambda *a, **k: [(2, 1, 6, "", (ip, 443)) for ip in ips])
    monkeypatch.setattr(page_shot.socket, "getaddrinfo", answer("93.184.216.34"))
    assert page_shot.public_ip("a.example") == "93.184.216.34"
    for ips in (("127.0.0.1",), ("93.184.216.34", "10.0.0.5"), ("169.254.169.254",), ()):
        monkeypatch.setattr(page_shot.socket, "getaddrinfo", answer(*ips))
        assert page_shot.public_ip("a.example") is None


def test_shot_proxy_refuses_private_and_non_tls_targets():
    import socket as so
    from app import page_shot
    proxy, port = page_shot.start_proxy()
    try:
        for target in ("127.0.0.1:443", "localhost:443", "169.254.169.254:443", "example.com:80"):
            with so.create_connection(("127.0.0.1", port), timeout=5) as c:
                c.sendall(f"CONNECT {target} HTTP/1.1\r\nHost: {target}\r\n\r\n".encode())
                assert c.recv(64).startswith(b"HTTP/1.1 403"), target
        with so.create_connection(("127.0.0.1", port), timeout=5) as c:
            c.sendall(b"GET http://127.0.0.1:8000/ HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n")
            assert c.recv(64).startswith(b"HTTP/1.1 403")
    finally:
        proxy.shutdown()


# ---- custom answers -------------------------------------------------------------------

from app import review_answers  # noqa: E402

ROW = {"title": "Test Cafe", "options": ["yes", "no", "closed"], "matches": [{"category": "cafe", "area": "RS Puram"}], "other": ""}


@pytest.mark.parametrize("said, verdict, edits", [
    ("no it's actually a bakery in Peelamedu", "no", [("category", "dessert"), ("area", "Peelamedu")]),
    ("it's closed now", "closed", []),
    ("not a real place, just a dish name", "no", [("reject", "not_a_venue")]),
    ("this is in Palakkad, not Coimbatore", "no", [("reject", "wrong_city")]),
    ("wrong, it is called Sree Annapoorna in Gandhipuram", "no", [("rename", "Sree Annapoorna"), ("area", "Gandhipuram")]),
    ("not a cafe, it's a restaurant", "no", [("category", "food")]),
    ("looks fine to me", "yes", []),
    ("yes", "yes", []),
])
def test_custom_answers_are_read_from_the_owners_words(said, verdict, edits):
    reading = review_answers.interpret(said, ROW)
    assert reading["verdict"] == verdict
    assert [(e["action"], e["value"]) for e in reading["edits"]] == edits
    assert reading["note"] == said


def test_model_readings_keep_only_what_was_said():
    said = "the owner told me they mostly sell sweets these days"
    invented = {"verdict": "no", "edits": [
        {"action": "rename", "value": "Krishna Sweets"},      # never said
        {"action": "area", "value": "Peelamedu"},            # never said
        {"action": "category", "value": "dessert"},          # "sweets" was said
        {"action": "reject", "value": "not_a_venue"},        # never said
    ]}
    kept = review_answers.validate(invented, said, ROW)
    assert [(e["action"], e["value"]) for e in kept["edits"]] == [("category", "dessert")]
    model_used = review_answers.interpret(said, ROW, ask_model=lambda t, i: invented)
    assert model_used["used_model"] and [e["action"] for e in model_used["edits"]] == ["category"]


def test_closed_is_not_offered_where_the_sheet_has_no_closed():
    row = {**ROW, "options": ["yes", "no"]}
    assert review_answers.interpret("it's closed now", row)["verdict"] == ""


def test_custom_answer_teaches_the_place_records_the_note_and_undoes(desk, monkeypatch):
    from app import learned
    monkeypatch.setattr(review_desk, "ask_model", lambda t, i: None)
    with Session() as db:
        spot = IdentifiedSpot(user_id=desk.owner, identity_key="k:test-cafe", name="Test Cafe", category="cafe", area="RS Puram")
        spot.data = {"sources": []}
        db.add(spot)
        db.commit()
        spot_id = spot.id
    post = lambda path, **kw: desk.client.post("/api/admin/review-desk/" + path, json=kw, headers=desk.auth)
    said = "no it's actually a bakery in Peelamedu"
    reading = post("custom/preview", sheet="overture", row=0, text=said).json()
    assert reading["verdict"] == "no" and reading["place"] is True
    # A client can't slip in something the owner didn't say.
    reading["edits"].append({"action": "rename", "value": "Evil Name"})
    done = post("custom/apply", sheet="overture", row=0, text=said, reading=reading).json()
    assert done["answer"] == "no" and len(done["applied"]) == 2 and not done["skipped"]
    with Session() as db:
        row = db.get(IdentifiedSpot, spot_id)
        assert (row.name, row.category, row.area) == ("Test Cafe", "dessert", "Peelamedu")
        assert learned.category_for(learned.load(db, desk.owner), "Test Cafe") == "dessert"
    sheet = (desk.dir / "spotcheck-overture-50.csv").read_text(encoding="utf-8-sig").splitlines()
    assert sheet[0].endswith(",owner_note")
    cells = next(csv.reader([sheet[1]]))
    assert cells[5] == "no" and cells[6] == said
    item = desk.client.get("/api/admin/review-desk/items", headers=desk.auth).json()["items"][2]
    assert item["answer"] == "no" and item["note"] == said
    assert post("custom/undo", sheet="overture", row=0, **done["undo"]).json()["records_restored"] >= 1
    with Session() as db:
        row = db.get(IdentifiedSpot, spot_id)
        assert (row.category, row.area) == ("cafe", "RS Puram")
    cells = next(csv.reader([(desk.dir / "spotcheck-overture-50.csv").read_text(encoding="utf-8-sig").splitlines()[1]]))
    assert cells[5] == "" and cells[6] == ""


def test_custom_answer_without_a_stored_place_keeps_the_note(desk, monkeypatch):
    monkeypatch.setattr(review_desk, "ask_model", lambda t, i: None)
    said = "no, it is a bakery"
    post = lambda path, **kw: desk.client.post("/api/admin/review-desk/" + path, json=kw, headers=desk.auth)
    reading = post("custom/preview", sheet="decisions", row=0, text=said).json()
    done = post("custom/apply", sheet="decisions", row=0, text=said, reading=reading).json()
    assert done["applied"] == [] and done["skipped"][0]["reason"].startswith("No stored place")
    cells = next(csv.reader([(desk.dir / "spotcheck-claude-decisions-50.csv").read_text(encoding="utf-8-sig").splitlines()[1]]))
    assert cells[5] == "no" and cells[6] == said


def test_a_model_yes_with_a_correction_becomes_no_unless_the_owner_said_yes():
    said = "the owner told me they mostly sell sweets these days"
    guess = {"verdict": "yes", "edits": [{"action": "category", "value": "dessert"}]}
    assert review_answers.validate(guess, said, ROW)["verdict"] == "no"
    assert review_answers.validate(guess, "yes, they mostly sell sweets now", ROW)["verdict"] == "yes"
    assert review_answers.interpret("it shut during covid I think", ROW, ask_model=lambda t, i: 1 / 0)["verdict"] == "closed"


def test_live_sheet_rows_appear_last_and_answers_are_stored(desk):
    import csv as _csv
    import io as _io

    with Session() as db:
        spot = IdentifiedSpot(user_id=desk.owner, identity_key="k:live-one", name="Live One", category="cafe",
                              area="Peelamedu", status="approved")
        spot.data = {"sources": [{"type": "overture", "url": "https://overturemaps.org/x"}]}
        db.add(spot)
        db.commit()
        spot_id = spot.id
    header = review_desk.LIVE_HEADER
    out = _io.StringIO()
    _csv.writer(out, lineterminator="\n").writerows(
        [header, ["Live One", "cafe", "Peelamedu", "overture", "https://www.google.com/maps/search/?api=1&query=Live+One", "", "", spot_id]])
    (desk.dir / "spotcheck-live-200.csv").write_text(out.getvalue(), encoding="utf-8-sig")
    items = desk.client.get("/api/admin/review-desk/items", headers=desk.auth).json()["items"]
    live = items[-1]
    assert live["sheet"] == "live" and live["title"] == "Live One"
    assert live["options"] == ["yes", "no", "closed"]
    assert live["matches"][0]["id"] == spot_id
    assert any("one source" in h for h in live["hints"]) and any("estimates" in h for h in live["hints"])
    r = desk.client.post("/api/admin/review-desk/answer", headers=desk.auth,
                         json={"sheet": "live", "row": 0, "answer": "closed"})
    assert r.status_code == 200
    saved = list(_csv.reader(_io.StringIO((desk.dir / "spotcheck-live-200.csv").read_text(encoding="utf-8-sig"))))
    assert saved[1][5] == "closed" and saved[1][7] == spot_id


def test_live_audit_sample_spreads_across_categories():
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "scripts" / "make_live_audit.py"
    spec = importlib.util.spec_from_file_location("make_live_audit", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    share = mod.allocate({"food": 900, "cafe": 300, "bowling": 6, "park": 2}, 200)
    assert sum(share.values()) == 200
    assert share["bowling"] == 4 and share["park"] == 2 and share["food"] > share["cafe"]
    spots = [SimpleNamespace(id=f"s{i}", category="food" if i % 3 else "cafe") for i in range(60)]
    first = [s.id for s in mod.sample(spots, 20, seed=1)]
    assert first == [s.id for s in mod.sample(spots, 20, seed=1)] and len(set(first)) == 20
