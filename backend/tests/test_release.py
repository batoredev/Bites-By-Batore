"""Publish rule and release snapshot (week 1 items 1.8 and 1.9)."""

import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app import release
from app.db import Claim, IdentifiedSpot, Session, Venue

NOW = datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc)
RECENT = (NOW - timedelta(days=10)).isoformat()
OLD = (NOW - timedelta(days=400)).isoformat()


def venue(**over):
    base = dict(status="published", is_demo=False, lat=11.01, lng=76.95, details={"closed": "False"})
    base.update(over)
    return SimpleNamespace(**base)


def sources(*kinds, when=RECENT):
    return {"sources": [{"type": k, "url": f"https://example.org/{k}", "collected_at": when} for k in kinds]}


@pytest.mark.parametrize(
    "place, data, verdict, publish, reason",
    [
        (venue(), sources("overture", "openstreetmap"), None, True, None),
        (venue(), sources("overture", "web_candidate"), None, True, None),
        (venue(), sources("overture"), None, False, "only one kind of source and no owner OK"),
        # Two web pages are one kind of source, not two.
        (venue(), sources("web_candidate", "monitored_page"), None, False, "only one kind of source and no owner OK"),
        (venue(), sources("overture"), "yes", True, None),
        (venue(), sources("overture", "openstreetmap"), "closed", False, "owner answered 'closed'"),
        (venue(), sources("overture", "openstreetmap"), "no", False, "owner answered 'no'"),
        (venue(), sources("overture", "openstreetmap", when=OLD), None, False, "no source seen in the last 180 days"),
        (venue(lat=13.08, lng=80.27), sources("overture", "openstreetmap"), None, False, "no map point inside Coimbatore"),
        (venue(lat=None), sources("overture", "openstreetmap"), None, False, "no map point inside Coimbatore"),
        (venue(details={"closed": "True"}), sources("overture", "openstreetmap"), None, False, "marked closed"),
        (venue(is_demo=True), sources("overture", "openstreetmap"), None, False, "not a live place"),
        (
            venue(details={"maps_identity": {"confirmed_by": "local-operator"}}),
            sources("overture"), None, True, None,
        ),
        # The bulk agent's own confirmation is not the owner's OK.
        (
            venue(details={"maps_identity": {"confirmed_by": "agent:test-inventory"}}),
            sources("overture"), None, False, "only one kind of source and no owner OK",
        ),
    ],
)
def test_publish_rule(place, data, verdict, publish, reason):
    decision = release.publish_decision(place, data, verdict, NOW)
    assert decision["publish"] is publish
    if reason:
        assert reason in decision["reasons"]


def _seed(db):
    rows = [
        ("two", ["overture", "openstreetmap"], "collected"),
        ("one", ["overture"], "test_estimate"),
        ("owner", ["instagram"], "test_estimate"),
    ]
    for key, kinds, price_source in rows:
        data = sources(*kinds)
        data["sources"].append({"type": kinds[0], "url": "http://insecure.example/x", "collected_at": RECENT})
        data["observations"] = [{"comment": "private reel comment"}]
        db.add(IdentifiedSpot(id=f"s-{key}", user_id="u1", identity_key=key, name=key, status="approved", data=data))
        db.add(Venue(id=f"v-{key}", name=key.title(), category="food", area="RS Puram", address="", lat=11.0,
                     lng=76.95, tags=[], status="published", is_demo=False,
                     details={"identified_spot_id": f"s-{key}", "closed": "False", "price_per_person": 300,
                              "hours": {"0": [[600, 1320]]}}))
        db.add(Claim(venue_id=f"v-{key}", field="price_per_person", value={"value": 300}, source_url="",
                     source_type=price_source, source_group="g", observed_at=RECENT, expires_at=RECENT,
                     status="accepted"))
    db.commit()


def test_snapshot_holds_single_source_places_labels_estimates_and_keeps_private_data_out(client, tmp_path):
    sheet = tmp_path / "live.csv"
    sheet.write_text(
        "place_name,category,area,sources,google_maps_link,you_agree (yes/no/closed),owner_note,spot_id\n"
        "Owner,food,,instagram,link,yes,,s-owner\n",
        encoding="utf-8",
    )
    with Session() as db:
        _seed(db)
        snap = release.build_snapshot(db, "u1", at=NOW, sheet=sheet)
    ids = {p["id"] for p in snap["places"]}
    assert {"v-two", "v-owner"} <= ids and "v-one" not in ids
    assert snap["counts"]["held_reasons"]["only one kind of source and no owner OK"] >= 1
    by_id = {p["id"]: p for p in snap["places"]}
    assert by_id["v-two"]["price_basis"] == "checked"
    assert by_id["v-owner"]["price_basis"] == "approx."
    assert by_id["v-two"]["hours_basis"] == "approx."
    text = json.dumps(snap)
    assert "private reel comment" not in text and "http://insecure" not in text
    assert snap["rule"]["approved_by_owner"] is False


def test_snapshot_file_verifies_and_detects_tampering_and_is_never_overwritten(client, tmp_path):
    with Session() as db:
        _seed(db)
        snap = release.build_snapshot(db, "u1", at=NOW, sheet=tmp_path / "none.csv")
    path = release.write_snapshot(snap, tmp_path)
    assert release.verify_snapshot(path)["ok"] is True
    with pytest.raises(FileExistsError):
        release.write_snapshot(snap, tmp_path)
    tampered = json.loads(path.read_text(encoding="utf-8"))
    tampered["places"][0]["price_per_person"] = 1
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(tampered), encoding="utf-8")
    assert "checksum mismatch" in release.verify_snapshot(bad)["problems"]


def test_same_data_gives_same_checksum(client, tmp_path):
    with Session() as db:
        _seed(db)
        a = release.build_snapshot(db, "u1", at=NOW, sheet=tmp_path / "none.csv")
        b = release.build_snapshot(db, "u1", at=NOW, sheet=tmp_path / "none.csv")
    assert a["checksum"] == b["checksum"]
