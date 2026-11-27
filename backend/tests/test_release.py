"""Publish rule (owner approves every place), release snapshot and the Approve places tab."""

import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app import release
from app.config import settings
from app.db import Audit, Claim, IdentifiedSpot, Session, Venue

NOW = datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc)
RECENT = (NOW - timedelta(days=10)).isoformat()
OLD = (NOW - timedelta(days=400)).isoformat()


def venue(**over):
    base = dict(status="published", is_demo=False, lat=11.01, lng=76.95, name="Cafe", category="cafe",
                area="RS Puram", address="", tags=[], details={"closed": False, "price_per_person": 300})
    base.update(over)
    return SimpleNamespace(**base)


def approved(place, decision="approve"):
    place.details = {**place.details, "owner_publish": {
        "decision": decision, "fingerprint": release.fact_fingerprint(place)}}
    return place


def sources(*kinds, when=RECENT):
    return {"sources": [{"type": k, "url": f"https://example.org/{k}", "collected_at": when} for k in kinds]}


def decide(place, data=None, verdict=None):
    return release.publish_decision(place, data or sources("overture"), verdict, NOW)


def test_nothing_reaches_customers_without_the_owners_approval():
    d = decide(venue(), sources("overture", "openstreetmap"))
    assert (d["state"], d["publish"]) == ("waiting", False)
    assert "waiting for the owner's approval" in d["reasons"]


def test_an_approved_place_is_published_even_with_one_source_and_the_hint_says_so():
    d = decide(approved(venue()), sources("overture"))
    assert (d["state"], d["publish"]) == ("approved", True)
    assert "Only one kind of source backs this place." in d["hints"]


def test_changing_a_fact_after_approval_sends_it_back_to_the_owner():
    place = approved(venue())
    place.details = {**place.details, "price_per_person": 900}
    d = decide(place)
    assert (d["state"], d["publish"]) == ("changed", False)


def test_only_owner_approved_places_reach_customers_or_the_planner():
    assert not release.customer_ready(venue())
    assert release.customer_ready(approved(venue()))
    assert not release.customer_ready(approved(venue(), "reject"))
    changed = approved(venue())
    changed.details = {**changed.details, "price_per_person": 900}
    assert not release.customer_ready(changed)
    closed = approved(venue())
    closed.details = {**closed.details, "closed": True}
    assert not release.customer_ready(closed)
    assert not release.customer_ready(approved(venue(status="review")))
    assert release.customer_ready(venue(is_demo=True))


def test_a_yes_in_the_sample_sheet_never_approves_a_place():
    # The Live places check teaches the collecting agents; only Approve places approves.
    d = decide(venue(), sources("overture", "openstreetmap"), verdict="yes")
    assert (d["state"], d["publish"]) == ("waiting", False)
    assert "You said yes to it in the Live places check." in d["hints"]
    assert not release.customer_ready(venue())


def test_adding_a_source_does_not_undo_an_approval():
    place = approved(venue())
    assert decide(place, sources("overture", "instagram", "web_candidate"))["state"] == "approved"


@pytest.mark.parametrize(
    "place, verdict, blocker",
    [
        (venue(details={"closed": True}), None, "marked closed"),
        (venue(lat=13.08, lng=80.27), None, "no map point inside Coimbatore"),
        (venue(lat=None), None, "no map point inside Coimbatore"),
        (venue(is_demo=True), None, "not a live place"),
        (venue(), "closed", "owner answered 'closed' in the Live places check"),
    ],
)
def test_safety_checks_block_even_an_approved_place(place, verdict, blocker):
    d = decide(approved(place), verdict=verdict)
    assert (d["state"], d["publish"]) == ("blocked", False)
    assert blocker in d["blockers"]


def test_rejected_stays_rejected_and_hints_cover_sources_and_freshness():
    d = decide(approved(venue(), "reject"), sources("overture", "openstreetmap", when=OLD), "yes")
    assert (d["state"], d["publish"]) == ("rejected", False)
    assert any("2 independent kinds of source" in h for h in d["hints"])
    assert any("last 180 days" in h for h in d["hints"])
    assert "You said yes to it in the Live places check." in d["hints"]


def _seed(db, owner="u1"):
    for key, kinds, price_source in [("two", ["overture", "openstreetmap"], "collected"),
                                     ("one", ["overture"], "test_estimate")]:
        data = sources(*kinds)
        data["sources"].append({"type": kinds[0], "url": "http://insecure.example/x", "collected_at": RECENT})
        data["observations"] = [{"comment": "private reel comment"}]
        db.add(IdentifiedSpot(id=f"s-{key}", user_id=owner, identity_key=key, name=key, status="approved", data=data))
        db.add(Venue(id=f"v-{key}", name=key.title(), category="food", area="RS Puram", address="", lat=11.0,
                     lng=76.95, tags=[], status="published", is_demo=False,
                     details={"identified_spot_id": f"s-{key}", "closed": False, "price_per_person": 300,
                              "hours": {"0": [[600, 1320]]}}))
        db.add(Claim(venue_id=f"v-{key}", field="price_per_person", value={"value": 300}, source_url="",
                     source_type=price_source, source_group="g", observed_at=RECENT, expires_at=RECENT,
                     status="accepted"))
    db.commit()
    for key in ("two", "one"):
        approved(db.get(Venue, f"v-{key}"))
    db.commit()


def _unapprove(db, venue_id):
    v = db.get(Venue, venue_id)
    v.details = {k: x for k, x in v.details.items() if k != "owner_publish"}


def test_snapshot_ships_only_approved_places_labels_estimates_and_keeps_private_data_out(client, tmp_path):
    with Session() as db:
        _seed(db)
        _unapprove(db, "v-one")
        db.commit()
        snap = release.build_snapshot(db, "u1", at=NOW, sheet=tmp_path / "none.csv")
    assert [p["id"] for p in snap["places"]] == ["v-two"]
    assert snap["counts"]["by_state"] == {"approved": 1, "waiting": 1}
    place = snap["places"][0]
    assert (place["price_basis"], place["hours_basis"]) == ("checked", "approx.")
    text = json.dumps(snap)
    assert "private reel comment" not in text and "http://insecure" not in text
    assert snap["rule"]["version"] == "owner-1"


def test_snapshot_file_verifies_detects_tampering_and_is_never_overwritten(client, tmp_path):
    with Session() as db:
        _seed(db)
        snap = release.build_snapshot(db, "u1", at=NOW, sheet=tmp_path / "none.csv")
        again = release.build_snapshot(db, "u1", at=NOW, sheet=tmp_path / "none.csv")
    assert len(snap["places"]) == 2 and snap["checksum"] == again["checksum"]
    path = release.write_snapshot(snap, tmp_path)
    assert release.verify_snapshot(path)["ok"] is True
    with pytest.raises(FileExistsError):
        release.write_snapshot(snap, tmp_path)
    tampered = json.loads(path.read_text(encoding="utf-8"))
    tampered["places"][0]["price_per_person"] = 1
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(tampered), encoding="utf-8")
    assert "checksum mismatch" in release.verify_snapshot(bad)["problems"]


@pytest.fixture
def owner(client, monkeypatch, tmp_path):
    monkeypatch.setenv("APP_MODE", "local")
    settings.cache_clear()
    monkeypatch.setattr(release, "LIVE_SHEET", tmp_path / "live.csv")
    token = client.post("/api/auth/local").json()["access_token"]
    auth = {"Authorization": "Bearer " + token}
    uid = client.get("/api/me", headers=auth).json()["id"]
    with Session() as db:
        _seed(db, uid)
        _unapprove(db, "v-one")
        _unapprove(db, "v-two")
        db.add(Venue(id="v-closed", name="Shut", category="cafe", area="", address="", lat=11.0, lng=76.95,
                     tags=[], status="published", is_demo=False, details={"closed": True}))
        db.commit()
    yield SimpleNamespace(client=client, auth=auth)
    settings.cache_clear()


def test_approve_places_tab_lists_counts_and_records_each_decision(owner):
    c, auth = owner.client, owner.auth
    body = c.get("/api/admin/publish/places", headers=auth).json()
    assert body["counts"]["waiting"] == 2 and body["counts"]["blocked"] == 1
    assert {i["id"] for i in body["items"]} == {"v-one", "v-two"}
    item = next(i for i in body["items"] if i["id"] == "v-one")
    assert item["embed"].startswith("https://maps.google.com/") and item["price_basis"] == "approx."

    done = c.post("/api/admin/publish/decide", headers=auth,
                  json={"venue_id": "v-one", "decision": "approve", "note": "been there"}).json()
    assert (done["state"], done["note"]) == ("approved", "been there")
    assert c.get("/api/admin/publish/places?state=approved", headers=auth).json()["matching"] == 1

    refused = c.post("/api/admin/publish/decide", headers=auth, json={"venue_id": "v-closed", "decision": "approve"})
    assert refused.status_code == 409 and "marked closed" in refused.json()["detail"]

    assert c.post("/api/admin/publish/decide", headers=auth,
                  json={"venue_id": "v-two", "decision": "reject"}).json()["state"] == "rejected"
    assert c.post("/api/admin/publish/decide", headers=auth,
                  json={"venue_id": "v-two", "decision": "clear"}).json()["state"] == "waiting"
    with Session() as db:
        actions = [a.action for a in db.query(Audit).filter(Audit.action.like("publish.%"))]
    assert sorted(actions) == sorted(["publish.approve", "publish.reject", "publish.clear"])


def test_a_fact_change_after_approval_shows_as_changed_in_the_tab(owner):
    c, auth = owner.client, owner.auth
    c.post("/api/admin/publish/decide", headers=auth, json={"venue_id": "v-two", "decision": "approve"})
    with Session() as db:
        v = db.get(Venue, "v-two")
        v.details = {**v.details, "hours": {"0": [[700, 1300]]}}
        db.commit()
    body = c.get("/api/admin/publish/places?state=changed", headers=auth).json()
    assert [i["id"] for i in body["items"]] == ["v-two"]


def test_the_tab_needs_an_admin(client):
    assert client.get("/api/admin/publish/places").status_code in (401, 403)
