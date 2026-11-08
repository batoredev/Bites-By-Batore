"""Isolated fixtures: no venue or reviewer decision is written to the real inventory."""

import json
from types import SimpleNamespace
import pytest
from sqlalchemy import select
from app.db import Session, Venue, Claim, Job, IdentifiedSpot, ResearchCorrection, now
from app import maintenance as m, research
from app.providers import DeferredCollection, Unavailable
from app.config import settings
from app.spots import upsert_spot


def fixture(db, owner="owner", pages=1):
    row = upsert_spot(
        db,
        owner,
        "Zircon Cafe",
        "cafe",
        "RS Puram",
        {"sources": [{"url": f"https://fixture.example/{i}", "type": "official_menu"} for i in range(pages)]},
    )
    db.commit()
    return row


def page(price=100):
    return f'<p>Zircon Cafe Coimbatore</p><span data-hook="item.name">Rice</span><span data-hook="item.price">₹{price}</span>'


def venue(db, row):
    v = Venue(
        name=row.name,
        category="cafe",
        area=row.area,
        address="14 Fixture Road, Coimbatore",
        lat=11.01,
        lng=76.96,
        status="published",
        is_demo=False,
        details={"location_approval": {"by": row.user_id}, "branch_confirmed": True},
    )
    db.add(v)
    db.flush()
    row.venue_id = v.id
    db.commit()
    return v


def due(row):
    row.data = {
        **row.data,
        "page_checks": {
            url: {**p, "next_check_at": "2000-01-01"} for url, p in row.data.get("page_checks", {}).items()
        },
    }


def test_monitor_changes_hold_published_venue_and_invalidate_revision(client, monkeypatch):
    with Session() as db:
        row = fixture(db)
        v = venue(db, row)
        monkeypatch.setattr(m, "read_official_html", lambda *a, **k: page())
        m.refresh_spot(db, row.id, row.user_id)
        assert not row.data.get("maintenance_alerts")
        assert v.status == "published"  # baseline fetch does not invent a change
        due(row)
        db.commit()
        monkeypatch.setattr(m, "read_official_html", lambda *a, **k: page(150))
        m.refresh_spot(db, row.id, row.user_id)
        assert v.status == "review" and v.revision == 2
        assert "location_approval" not in v.details
        assert row.data["maintenance_alerts"][0]["kind"] == "source_changed"
        snapshot = next(iter(row.data["page_checks"].values()))
        assert snapshot["observed_fields"]["offerings"][0]["price_inr"] == 150
        assert snapshot["previous_values"]["offerings"][0]["price_inr"] == 100
        assert snapshot["verified"] is False
        due(row)
        db.commit()
        m.refresh_spot(db, row.id, row.user_id)
        assert len(row.data["maintenance_alerts"]) == 1 and v.revision == 2


def test_refresh_checkpoints_before_quota_deferral_and_resumes(client, monkeypatch):
    calls = []

    def fetch(db, url, **kwargs):
        calls.append(url)
        if len(calls) == 2:
            raise DeferredCollection("fixture quota")
        return page()

    monkeypatch.setattr(m, "read_official_html", fetch)
    with Session() as db:
        row = fixture(db, pages=3)
        with pytest.raises(DeferredCollection):
            m.refresh_spot(db, row.id, row.user_id)
        assert len(row.data["page_checks"]) == 1
        result = m.refresh_spot(db, row.id, row.user_id)
        assert result["remaining"] == 0 and calls == [
            "https://fixture.example/0",
            "https://fixture.example/1",
            "https://fixture.example/1",
            "https://fixture.example/2",
        ]


def test_outage_keeps_last_success_and_reports_after_three_failures(client, monkeypatch):
    with Session() as db:
        row = fixture(db)
        monkeypatch.setattr(m, "read_official_html", lambda *a, **k: page())
        m.refresh_spot(db, row.id, row.user_id)
        before = next(iter(row.data["page_checks"].values()))["last_success_at"]

        def unavailable(*a, **k):
            raise Unavailable("fixture unavailable")

        monkeypatch.setattr(m, "read_official_html", unavailable)
        for i in range(3):
            due(row)
            db.commit()
            m.refresh_spot(db, row.id, row.user_id)
        snapshot = next(iter(row.data["page_checks"].values()))
        assert snapshot["last_success_at"] == before and snapshot["failures"] == 3
        assert row.data["maintenance_alerts"][0]["kind"] == "source_unavailable"


def test_wrong_owner_or_held_record_never_fetches(client, monkeypatch):
    def forbidden(*a, **k):
        raise AssertionError("must not fetch")

    monkeypatch.setattr(m, "read_official_html", forbidden)
    with Session() as db:
        row = fixture(db)
        assert m.refresh_spot(db, row.id, "other")["removed_or_inactive"]
        row.status = "quarantined"
        db.commit()
        assert m.refresh_spot(db, row.id, row.user_id)["removed_or_inactive"]


def test_expired_critical_facts_hold_location_only_once(client):
    with Session() as db:
        row = fixture(db)
        v = venue(db, row)
        assert m.expire_critical_facts(db) == [v.id]
        assert m.expire_critical_facts(db) == []
        assert v.status == "review" and v.revision == 2
        assert not v.details.get("location_approval")
        assert not m.approval_packet(db, row)["ready_for_final_approval"]


def test_current_critical_facts_are_not_expired_by_scheduler(client):
    with Session() as db:
        row = fixture(db)
        v = venue(db, row)
        for field in ["price_per_person", "hours", "closed"]:
            db.add(
                Claim(
                    venue_id=v.id,
                    field=field,
                    value={"value": 1},
                    source_url="https://fixture.example",
                    source_type="official",
                    source_group="fixture",
                    observed_at=now(),
                    expires_at=m.after(2),
                    status="accepted",
                )
            )
        db.commit()
        assert m.expire_critical_facts(db) == [] and v.status == "published"


def test_schedule_maintenance_is_idempotent_and_respects_reel_budget(client, monkeypatch):
    monkeypatch.setattr(settings(), "source_watch_daily_limit", 1)
    with Session() as db:
        fixture(db)
        for i in range(2):
            c = research.start_case(
                db,
                "owner",
                "cafes",
                seed_sources=[{"platform": "instagram", "url": f"https://www.instagram.com/p/watch{i}/"}],
            )
            c.state = "review"
        db.commit()
        m.schedule_maintenance(db, "owner")
        m.schedule_maintenance(db, "owner")
        assert len(list(db.scalars(select(Job).where(Job.kind == "spot_refresh")))) == 1
        assert len(list(db.scalars(select(Job).where(Job.kind == "source_watch")))) == 1


def test_source_watch_detects_caption_change_without_relabelling_old_analysis(client, monkeypatch):
    from app import browser_sources

    with Session() as db:
        c = research.start_case(
            db,
            "owner",
            "cafes",
            seed_sources=[
                {
                    "platform": "instagram",
                    "url": "https://www.instagram.com/p/watch/",
                    "caption": "Old caption",
                }
            ],
        )
        source = research.case_sources(db, c)[0]
        source.content = {"caption": "Old caption"}
        source.analysis = {"caption": {"status": "observations_only", "summary": "Old output"}}
        row = fixture(db)
        row.data = {**row.data, "source_ids": [source.id]}
        v = venue(db, row)
        monkeypatch.setattr(
            browser_sources,
            "browser_instagram",
            lambda *a: {
                "browser": {"status": "public_content"},
                "caption": "New caption",
                "media_url": "https://signed.example/private",
            },
        )
        result = m.watch_source(db, source.id, "owner")
        assert result["caption_changed"] and v.status == "review"
        from app.db import Investigation

        followup = db.get(Investigation, result["reinvestigation_case_id"])
        assert followup.user_id == "owner" and followup.context["url"] == source.canonical_url
        count = len(list(db.scalars(select(Investigation))))
        m.watch_source(db, source.id, "owner")
        assert len(list(db.scalars(select(Investigation)))) == count
        assert source.content["caption"] == "Old caption"
        assert "signed.example" not in json.dumps(source.analysis)


def test_review_packets_and_alerts_are_private_exportable_erasable(client, auth):
    owner = client.get("/api/me", headers=auth).json()["id"]
    with Session() as db:
        row = fixture(db, owner)
        other = fixture(db, "other")
        m.alert(row, "source_changed", "https://fixture.example/0", {"fields": ["hours"]})
        db.add(Job(key="refresh-fixture", kind="spot_refresh", payload={"spot_id": row.id, "user_id": owner}))
        db.commit()
        sid, oid = row.id, other.id
        aid = row.data["maintenance_alerts"][0]["id"]
    endpoint = f"/api/admin/maintenance/packets/{sid}"
    assert client.get(f"/api/admin/maintenance/packets/{oid}", headers=auth).status_code == 404
    result = client.get(endpoint, headers=auth).json()
    assert result["blockers"] and not result["ready_for_final_approval"]
    label = {
        "checked_original": False,
        "reason": "Fixture evidence independently checked",
        "evidence_url": "https://fixture.example/0",
    }
    assert client.post(endpoint + f"/alerts/{aid}/resolve", headers=auth, json=label).status_code == 422
    label["checked_original"] = True
    assert (
        client.post(endpoint + f"/alerts/{aid}/resolve", headers=auth, json=label).json()["published"]
        is False
    )
    assert "maintenance_alerts" in json.dumps(client.get("/api/me/export", headers=auth).json())
    assert client.delete("/api/me/data", headers=auth).status_code == 200
    with Session() as db:
        assert not db.get(IdentifiedSpot, sid) and db.get(IdentifiedSpot, oid)
        assert not db.scalar(select(Job).where(Job.key == "refresh-fixture"))


def test_holdout_corrections_do_not_leak_into_other_evaluation_sources(client):
    from app.learning import relevant_examples

    with Session() as db:
        c = research.start_case(
            db,
            "owner",
            "cafes",
            seed_sources=[{"platform": "instagram", "url": "https://www.instagram.com/p/train/"}],
        )
        source = research.case_sources(db, c)[0]
        source.analysis = {"evaluation_labels": {"caption": {"split": "holdout"}}}
        db.add(
            ResearchCorrection(
                user_id="owner",
                source_id=source.id,
                role="caption",
                scope="Zircon Cafe",
                original="Wrong",
                corrected="Right",
                reason="Fixture correction",
            )
        )
        db.commit()
        target = SimpleNamespace(content={"caption": "Zircon Cafe Coimbatore"})
        assert relevant_examples(db, "owner", target, "caption") == []


def test_frontier_covers_more_topics_and_areas():
    from app.frontier import AREAS, CATEGORIES

    assert len(AREAS) * len(CATEGORIES) == 168
    assert not any(t in " ".join(CATEGORIES) for t in ["events", "scenic drives"])


def test_provisional_metrics_require_labels_even_after_fetch(client):
    from app.evaluation import report

    with Session() as db:
        fixture(db)
        assert report(db, "owner")["name_precision"] is None


def test_crossreferenced_first_party_sources_merge_without_losing_conflicts(client):
    from app.inventory import save_target

    with Session() as db:
        row = fixture(db)
        row.data = {**row.data, "hours": "09:00-23:00"}
        seed = {
            "name": row.name,
            "area": row.area,
            "category": row.category,
            "target_source_url": "https://fixture.example/0",
        }
        incoming = {
            "hours": "11:00-22:00",
            "sources": [{"url": "https://second.example/branch", "type": "official"}],
        }
        for _ in range(2):
            result = save_target(db, row.user_id, seed, incoming)
            db.commit()
            assert result.id == row.id
        assert len(list(db.scalars(select(IdentifiedSpot)))) == 1
        assert len(row.data["sources"]) == 2
        assert row.data["hours"] == "09:00-23:00"
        assert len(row.data["conflicts"]) == 1
        assert not row.data.get("maps_identity") and not row.venue_id


def test_prepared_branch_must_match_publication_gate(client):
    with Session() as db:
        row = fixture(db)
        v = venue(db, row)
        row.data = {**row.data, "maps_identity": {"confirmed_by": row.user_id}}
        v.details = {"branch_confirmed": True}
        db.commit()
        packet = m.approval_packet(db, row)
        assert any("prepared venue" in b for b in packet["blockers"])
        assert not packet["ready_for_final_approval"]


def test_older_completed_search_enters_recurring_schedule(client):
    with Session() as db:
        row = fixture(db)
        row.data = {
            **row.data,
            "web_search_results": [{"url": "https://fixture.example/0", "status": "collected_unverified"}],
        }
        db.commit()
        m.schedule_maintenance(db, row.user_id)
        assert row.data["web_search_next_at"] > now()
        row.data = {**row.data, "web_search_next_at": "2000-01-01"}
        db.commit()
        m.schedule_maintenance(db, row.user_id)
        m.schedule_maintenance(db, row.user_id)
        assert len(list(db.scalars(select(Job).where(Job.kind == "spot_enrich")))) == 1


def test_anonymous_activity_descriptions_are_held_but_named_clubs_remain_candidates():
    from app.spot_identity import quality_issues

    assert quality_issues("a club in Coimbatore")
    assert quality_issues("Car Race Coimbatore")
    assert not quality_issues("Zircon Club")


def test_expiry_audit_follows_owner_export_and_erasure(client, auth):
    from app.db import Audit

    owner = client.get("/api/me", headers=auth).json()["id"]
    with Session() as db:
        row = fixture(db, owner)
        venue(db, row)
        m.expire_critical_facts(db)
        aid = db.scalar(select(Audit.id).where(Audit.action == "maintenance.expired"))
        assert db.get(Audit, aid).actor == owner
    exported = client.get("/api/me/export", headers=auth).json()
    assert any(a["id"] == aid for a in exported["spot_reviews"])
    client.delete("/api/me/data", headers=auth)
    with Session() as db:
        assert db.get(Audit, aid) is None


def test_watched_caption_uses_its_own_retention_clock(client):
    with Session() as db:
        case = research.start_case(
            db,
            "owner",
            "cafes",
            seed_sources=[{"platform": "instagram", "url": "https://www.instagram.com/p/retentionwatch/"}],
        )
        source = research.case_sources(db, case)[0]
        source.content = {"caption": "fresh original", "fetched_at": now()}
        source.analysis = {
            "source_watch": {
                "observed_caption": "old watch",
                "checked_at": "2000-01-01T00:00:00+00:00",
                "caption_hash": "preserve",
            }
        }
        db.commit()
        research.purge_expired_sources(db)
        assert "observed_caption" not in source.analysis["source_watch"]
        assert source.analysis["source_watch"]["caption_hash"] == "preserve"
        assert source.content["caption"] == "fresh original"
        source.analysis = {"source_watch": {"observed_caption": "fresh watch", "checked_at": now()}}
        source.content = {"caption": "old original", "fetched_at": "2000-01-01T00:00:00+00:00"}
        db.commit()
        research.purge_expired_sources(db)
        assert source.analysis["source_watch"]["observed_caption"] == "fresh watch"
        assert "caption" not in source.content
