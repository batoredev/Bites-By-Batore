"""Initial-fill regressions use isolated fixtures; no remote requests or labels."""

from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
import pytest
from sqlalchemy import select
from app import collection_control as cc, providers, jobs, frontier
from app.config import settings
from app.db import Session, Counter, Job, Investigation, IdentifiedSpot
from app.providers import DeferredCollection, Unavailable
from app.spots import upsert_spot


@pytest.fixture
def bulk(client, monkeypatch):
    monkeypatch.setattr(settings(), "app_mode", "local")
    monkeypatch.setattr(settings(), "local_bulk_collection", True)
    return client


def test_exhausted_daily_counter_continues_and_counts_are_preserved(bulk):
    day = datetime.now(timezone.utc).date().isoformat()
    with Session() as db:
        db.add(Counter(key="provider:" + day, value=300))
        db.commit()
        for _ in range(20):
            providers.quota(db)
        assert db.get(Counter, "provider:" + day).value == 320
        assert db.get(Counter, "collection-free:" + day).value == 20
        assert cc.daily_limits() == {"external": 0, "browser": 0, "investigations": 0}


def test_bulk_is_local_only_and_switching_off_restores_normal_caps(bulk, monkeypatch):
    monkeypatch.setattr(settings(), "app_mode", "live")
    assert not cc.bulk_enabled() and cc.daily_limits()["external"] > 0
    monkeypatch.setattr(settings(), "app_mode", "local")
    monkeypatch.setattr(settings(), "local_bulk_collection", False)
    assert not cc.bulk_enabled() and cc.daily_limits()["external"] > 0


def test_browser_has_no_daily_cap_but_host_spacing_is_retained(bulk, monkeypatch):
    stamp = [1800000000]
    monkeypatch.setattr(cc, "time", SimpleNamespace(time=lambda: stamp[0]))
    day = datetime.now(timezone.utc).date().isoformat()
    with Session() as db:
        db.add(Counter(key="provider:" + day, value=300))
        db.add(Counter(key="instagram-browser:" + day, value=30))
        db.commit()
        providers.reserve_browser_call(db)
        with pytest.raises(DeferredCollection) as error:
            providers.reserve_browser_call(db)
        assert error.value.reason == "source_pacing"
        stamp[0] += 3
        providers.reserve_browser_call(db)
        assert db.get(Counter, "provider:" + day).value == 302
        assert db.get(Counter, "instagram-browser:" + day).value == 32


def test_free_collection_still_works_with_zero_paid_budget_but_paid_http_is_blocked(bulk, monkeypatch):
    monkeypatch.setattr(settings(), "monthly_budget_inr", 0)
    monkeypatch.setattr(providers.httpx, "Client", lambda *a, **k: pytest.fail("No paid HTTP permitted"))
    with Session() as db:
        providers.quota(db)
        with pytest.raises(Unavailable, match="Monthly provider spending"):
            providers.call(db, "GET", "https://places.googleapis.com/v1/places")
        month = datetime.now(timezone.utc).strftime("%Y-%m")
        assert db.get(Counter, "budget-reserved:" + month).value == 0


def test_source_retry_after_is_durable_and_not_a_daily_limit(bulk, monkeypatch):
    stamp = [1800000000]
    monkeypatch.setattr(cc, "time", SimpleNamespace(time=lambda: stamp[0]))
    with Session() as db:
        with pytest.raises(DeferredCollection) as error:
            cc.backoff(db, "fixture.example", headers={"Retry-After": "600"})
        assert error.value.retry_seconds == 600
        assert error.value.reason == "source_cooldown"
    with Session() as db:
        with pytest.raises(DeferredCollection):
            cc.pace(db, "fixture.example")
        stamp[0] += 601
        cc.pace(db, "fixture.example")
        assert db.get(Counter, "source-next:fixture.example").value < 2**31


def test_http_429_schedules_source_retry_and_second_read_does_not_request_again(bulk, monkeypatch):
    from contextlib import contextmanager
    import httpx
    from app import web_evidence

    requests = []
    monkeypatch.setattr(
        web_evidence.socket, "getaddrinfo", lambda *a, **k: [(2, 1, 6, "", ("93.184.216.34", 443))]
    )

    @contextmanager
    def stream(*args, **kwargs):
        requests.append(args)
        yield httpx.Response(429, headers={"Retry-After": "900"}, content=b"fixture limited")

    @contextmanager
    def client(*args, **kwargs):
        yield SimpleNamespace(stream=stream)

    monkeypatch.setattr(web_evidence.httpx, "Client", client)
    with Session() as db:
        with pytest.raises(DeferredCollection) as error:
            web_evidence.read_official_html(db, "https://fixture.example/menu", allow_unverified_host=True)
        assert error.value.retry_seconds == 900 and error.value.reason == "source_cooldown"
        with pytest.raises(DeferredCollection):
            web_evidence.read_official_html(db, "https://fixture.example/menu", allow_unverified_host=True)
        assert len(requests) == 1


def test_fair_queue_services_enrichment_between_high_priority_discovery_jobs(bulk):
    with Session() as db:
        for n in range(8):
            jobs.enqueue(db, "investigation", {}, "discovery-fixture:" + str(n), priority=90)
        jobs.enqueue(db, "spot_enrich", {}, "enrichment-fixture", priority=25)
        jobs.enqueue(db, "spot_refresh", {}, "refresh-fixture", priority=85)
        selected = []
        for _ in range(7):
            job = jobs.claim_job(db)
            selected.append(job.kind)
            job.state = "done"
            db.commit()
        assert "investigation" in selected and "spot_enrich" in selected and "spot_refresh" in selected


def test_host_deferral_does_not_exhaust_retry_attempts(bulk, monkeypatch):
    def temporary(*args):
        raise DeferredCollection("fixture busy", 600, reason="source_cooldown")

    monkeypatch.setattr(jobs, "execute_job", temporary)
    with Session() as db:
        job = jobs.enqueue(db, "spot_enrich", {}, "transient-fixture")
        ident = job.id
    assert jobs.run_once()
    with Session() as db:
        job = db.get(Job, ident)
        assert job.state == "queued" and job.attempts == 0
        assert job.result["_performance"]["last"]["wait_reason"] == "source_cooldown"


def test_resume_wakes_only_owned_old_app_limit_waits_and_retains_cooldowns(bulk):
    with Session() as db:
        upsert_spot(db, "owner", "Zircon Cafe", "cafe")
        db.commit()
        for owner, reason in [
            ("owner", "local_daily_limit"),
            ("other", "local_daily_limit"),
            ("owner", "source_cooldown"),
        ]:
            job = jobs.enqueue(db, "spot_enrich", {"user_id": owner}, owner + reason)
            job.due_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
            job.result = {"_performance": {"last": {"wait_reason": reason}}}
        db.add(Counter(key="source-cooldown:fixture.example", value=2000000000))
        db.commit()
        assert cc.resume_bulk(db, "owner")["resumed_jobs"] == 1
        assert db.get(Counter, "source-cooldown:fixture.example").value == 2000000000
        assert len(list(db.scalars(select(IdentifiedSpot)))) == 1


def test_bulk_frontier_has_no_daily_case_cap_and_bounds_only_active_work(bulk, monkeypatch):
    monkeypatch.setattr(settings(), "research_daily_limit", 1)
    with Session() as db:
        for _ in range(5):
            case = frontier.start_next(db, "owner", scheduled=True)
            assert case
            case.state = "review"
            db.commit()
        for _ in range(settings().bulk_active_case_limit):
            assert frontier.start_next(db, "owner", scheduled=True)
        count = len(list(db.scalars(select(Investigation))))
        assert frontier.start_next(db, "owner", scheduled=True)
        assert len(list(db.scalars(select(Investigation)))) == count


def test_structured_menu_saves_explicit_inr_hours_and_amenities_without_guessing():
    import json
    from app.inventory import parse_document

    data = {
        "@context": "https://schema.org",
        "@type": "Restaurant",
        "name": "Zircon Cafe",
        "openingHours": "Mo-Fr 10:00-18:00",
        "hasMenu": "/menu",
        "amenityFeature": [{"name": "Outdoor seating", "value": True}, {"name": "Rooftop", "value": False}],
        "hasMenuSection": {
            "@type": "MenuSection",
            "hasMenuItem": [
                {"@type": "MenuItem", "name": "Coffee", "offers": {"price": "120", "priceCurrency": "INR"}},
                {"@type": "MenuItem", "name": "Unknown", "offers": {"price": "20", "priceCurrency": "USD"}},
                {"@type": "MenuItem", "name": "No price"},
            ],
        },
    }
    doc = parse_document(
        '<script type="application/ld+json">' + json.dumps(data) + "</script>", "https://fixture.example/"
    )
    assert [(x["name"], x["price_inr"]) for x in doc["offerings"]] == [("Coffee", 120)]
    assert doc["hours_candidates"][0]["value"] == "Mo-Fr 10:00-18:00"
    assert [v["tag"] for v in doc["vibes"]] == ["outdoor"]
    assert doc["menu_links"] == ["https://fixture.example/menu"]
    assert not doc.get("hours") and "unverified" in doc["offerings"][0]["basis"]


def test_multiple_businesses_on_page_keep_menu_unassigned(bulk, monkeypatch):
    import json
    from app import spot_search

    html = (
        '<p>Zircon Cafe Coimbatore</p><script type="application/ld+json">'
        + json.dumps(
            {
                "@graph": [
                    {"@type": "Restaurant", "name": "Zircon Cafe", "address": "Fixture Street"},
                    {"@type": "Restaurant", "name": "Another Cafe", "address": "Other Street"},
                    {
                        "@type": "MenuItem",
                        "name": "Coffee",
                        "offers": {"price": "120", "priceCurrency": "INR"},
                    },
                ]
            }
        )
        + "</script>"
    )
    monkeypatch.setattr(spot_search, "read_official_html", lambda *a, **k: html)
    with Session() as db:
        row = upsert_spot(
            db,
            "owner",
            "Zircon Cafe",
            data={"web_search_results": [{"url": "https://fixture.example/", "status": "pending"}]},
        )
        db.commit()
        spot_search.enrich_spot(db, row.id)
        assert not row.data.get("offerings")
        assert row.data["unassigned_menu_pages"][0]["offerings"][0]["name"] == "Coffee"
        assert row.data["web_search_results"][0]["status"] == "multiple_branches_unassigned"
