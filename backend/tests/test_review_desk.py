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
