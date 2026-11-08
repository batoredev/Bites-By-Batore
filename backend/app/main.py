import hashlib
import json
import logging
import time
from types import SimpleNamespace
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, Depends, HTTPException, Request, UploadFile, File, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, delete, text
from sqlalchemy.exc import IntegrityError, OperationalError
from .config import settings, ROOT
from .db import (
    Session,
    get_db,
    migrate,
    Venue,
    Claim,
    Plan,
    Visit,
    SavedVenue,
    Submission,
    Job,
    Audit,
    Counter,
    now,
    SCHEMA_VERSION,
    DishEntry,
    is_database_busy,
)
from .auth import current_user, admin_user, is_admin, create_demo_session
from .schemas import (
    OutingRequest,
    ProfileUpdate,
    Feedback,
    SocialInput,
    ClaimInput,
    ReviewInput,
    VenueInput,
    VenueOperations,
    MapsIdentityReview,
    SavedPlaceInput,
)
from .seed import seed_demo
from .planner import build_plans, demo_leg, km, live_candidate_order
from .providers import (
    Unavailable,
    safe_social_url,
    media_payload,
    integration_status,
    route_matrix,
    google_details,
    google_search,
    opening_windows,
)
from .evidence import ingest_claim, apply_claim
from .jobs import enqueue, run_once, schedule
from .ingest import router as ingest_router
from .research_api import router as research_router
from .discovery import router as discovery_router
from .operations import router as operations_router
from .research import erase_cases, public_case
from .db import Investigation, ResearchCorrection, IdentifiedSpot
from .learning_api import router as learning_router, correction_dict
from .spots_api import router as spots_router
from .evaluation import router as evaluation_router
from .maintenance_api import router as maintenance_router
from .spots import spot_dict
from .experience_api import router as experience_router, published_venue
from .taste import rebuild_taste
from .menu import menu_view, text_matches

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app):
    c = settings()
    if c.app_mode == "demo":
        migrate()
        with Session() as db:
            seed_demo(db)
    elif c.app_mode == "local":
        if not c.database_url.startswith("sqlite"):
            raise RuntimeError("Local research requires a local SQLite database")
        migrate()
    else:
        if not all(
            [
                c.supabase_url.startswith("https://"),
                c.supabase_publishable_key,
                c.database_url.startswith("postgresql"),
            ]
        ):
            raise RuntimeError(
                "Live mode requires HTTPS Supabase Auth and a PostgreSQL database. See docs/SETUP.md"
            )
        with Session() as db:
            if (
                not db.get(Counter, "schema_version")
                or db.get(Counter, "schema_version").value != SCHEMA_VERSION
            ):
                raise RuntimeError("Run the database migration before starting live mode")
    yield


app = FastAPI(title="Bites by Batore", version="0.1.0", lifespan=lifespan)


@app.exception_handler(OperationalError)
async def database_operation_error(request: Request, exc: OperationalError):
    if is_database_busy(exc):
        return JSONResponse(
            status_code=503,
            headers={"Retry-After": "2"},
            content={"detail": "Local data updates are busy. Please retry shortly."},
        )
    logging.getLogger(__name__).error("Database operation failed; inspect database health")
    return JSONResponse(status_code=500, content={"detail": "Database operation unavailable"})


app.include_router(ingest_router)
app.include_router(research_router)
app.include_router(learning_router)
app.include_router(spots_router)
app.include_router(evaluation_router)
app.include_router(maintenance_router)

app.include_router(experience_router)
app.include_router(discovery_router)
app.include_router(operations_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings().web_origin],
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def boundaries(request: Request, call_next):
    import time

    started = time.perf_counter()
    if settings().app_mode == "local" and (
        not request.client
        or request.client.host not in {"127.0.0.1", "::1", "testclient"}
        or request.url.hostname not in {"localhost", "127.0.0.1", "::1", "testserver"}
    ):
        return JSONResponse({"detail": "Local research accepts loopback connections only"}, status_code=403)
    max_size = (settings().max_media_mb + 1) * 1024 * 1024
    if request.method in {"POST", "PUT", "PATCH"}:
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > max_size:
                return JSONResponse({"detail": "Request exceeds the upload limit"}, status_code=413)
        request._body = bytes(body)
    response = await call_next(request)
    if request.method == "POST" and request.url.path == "/api/plans":
        response.headers["Server-Timing"] = f"outing;dur={(time.perf_counter() - started) * 1000:.2f}"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Frame-Options"] = "DENY"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(Unavailable)
async def unavailable_handler(request, exc):
    return JSONResponse({"detail": str(exc)}, status_code=503)


def model_dict(row, omit=()):
    return {c.name: getattr(row, c.name) for c in row.__table__.columns if c.name not in omit}


def venue_dict(db, venue, user=None):
    result = model_dict(venue)
    claims = list(db.scalars(select(Claim).where(Claim.venue_id == venue.id)))
    result["evidence"] = [model_dict(c) for c in claims]
    accepted = [c for c in claims if c.status == "accepted"]
    result["freshness"] = (
        "demo"
        if venue.is_demo
        else (
            "needs checking"
            if any(c.expires_at < now() for c in accepted) or not accepted
            else "evidence on file"
        )
    )
    result["saved"] = bool(user and db.get(SavedVenue, (user.id, venue.id)))
    result["menu"] = menu_view(db, venue, user, claims)
    return result


def accessible_venue(db, venue_id):
    venue = db.get(Venue, venue_id)
    if not venue or venue.is_demo != (settings().app_mode == "demo"):
        raise HTTPException(404, "Venue not found")
    return venue


def own_plan(db, plan_id, user):
    p = db.get(Plan, plan_id)
    if not p or p.user_id != user.id:
        raise HTTPException(404, "Plan not found")
    return p


def plan_dict(db, p):
    result = model_dict(p)
    changed = any(
        not db.get(Venue, s["venue_id"]) or db.get(Venue, s["venue_id"]).revision != s["revision"]
        for s in p.result["stops"]
    )
    old = datetime.fromisoformat(p.created_at) < datetime.now(timezone.utc) - timedelta(hours=1)
    stop_ids = [s["venue_id"] for s in p.result["stops"]]
    expired = db.scalar(
        select(Claim.id)
        .where(
            Claim.venue_id.in_(stop_ids),
            Claim.field.in_(["price_per_person", "hours", "closed"]),
            Claim.status == "accepted",
            Claim.expires_at <= now(),
        )
        .limit(1)
    )
    result["needs_refresh"] = changed or old or bool(expired)
    return result


@app.get("/api/health")
def health(db=Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "mode": settings().app_mode, "time": now()}


@app.get("/api/config")
def config():
    c = settings()
    return {
        "mode": c.app_mode,
        "city": "Coimbatore",
        "currency": "INR",
        "interface_language": "en",
        "supabase_url": c.supabase_url if c.app_mode == "live" else "",
        "supabase_key": c.supabase_publishable_key if c.app_mode == "live" else "",
        "max_media_mb": c.max_media_mb,
    }


@app.post("/api/auth/demo")
def demo(request: Request, db=Depends(get_db)):
    if settings().app_mode != "demo":
        raise HTTPException(404, "Demo is disabled")
    if (
        not settings().demo_allow_network
        and request.client
        and request.client.host not in {"127.0.0.1", "::1", "testclient"}
    ):
        raise HTTPException(403, "Demo accounts are available only on this computer")
    return create_demo_session(db)


@app.post("/api/auth/local")
def local_session(request: Request, db=Depends(get_db)):
    if settings().app_mode != "local":
        raise HTTPException(404, "Local mode is disabled")
    if not request.client or request.client.host not in {"127.0.0.1", "::1", "testclient"}:
        raise HTTPException(403, "Local research is available only on this computer")
    if request.url.hostname not in {"127.0.0.1", "localhost", "::1", "testserver"}:
        raise HTTPException(403, "Local host required")
    origin = request.headers.get("origin")
    if origin and origin not in {
        str(request.base_url).rstrip("/"),
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    }:
        raise HTTPException(403, "Local origin required")
    return create_demo_session(db)


@app.get("/api/me")
def me(user=Depends(current_user)):
    return {**model_dict(user), "is_admin": is_admin(user), "mode": settings().app_mode}


@app.put("/api/me")
def update_me(data: ProfileUpdate, user=Depends(current_user), db=Depends(get_db)):
    user.name = data.name
    user.profile = {
        **user.profile,
        **data.model_dump(exclude={"name"}),
        "inferred": user.profile.get("inferred", {}),
    }
    rebuild_taste(db, user)
    db.commit()
    return {**model_dict(user), "is_admin": is_admin(user)}


@app.delete("/api/me/memory")
def clear_memory(user=Depends(current_user), db=Depends(get_db)):
    user.profile = {"learn_from_visits": True, "liked_tags": [], "avoided_tags": [], "inferred": {}}
    db.execute(delete(Visit).where(Visit.user_id == user.id))
    db.execute(delete(DishEntry).where(DishEntry.user_id == user.id))
    db.commit()
    return {"message": "Taste memory and confirmed visit history cleared"}


@app.get("/api/me/export")
def export_data(user=Depends(current_user), db=Depends(get_db)):
    from .performance import metrics_export

    return {
        "account": model_dict(user),
        "research_job_metrics": metrics_export(db, user.id),
        "duplicate_agent_runs": [
            model_dict(j)
            for j in db.scalars(
                select(Job).where(
                    Job.kind == "spot_deduplicate", Job.payload["user_id"].as_string() == user.id
                )
            )
        ],
        "identified_spots": [
            spot_dict(r) for r in db.scalars(select(IdentifiedSpot).where(IdentifiedSpot.user_id == user.id))
        ],
        "research_corrections": [
            correction_dict(r)
            for r in db.scalars(select(ResearchCorrection).where(ResearchCorrection.user_id == user.id))
        ],
        "investigations": [
            public_case(db, c)
            for c in db.scalars(select(Investigation).where(Investigation.user_id == user.id))
        ],
        "plans": [model_dict(x) for x in db.scalars(select(Plan).where(Plan.user_id == user.id))],
        "spot_reviews": [
            model_dict(x)
            for x in db.scalars(
                select(Audit).where(
                    Audit.actor == user.id,
                    Audit.action.in_(
                        [
                            "spot.merged",
                            "spot.prepared",
                            "spots.quality_cleanup",
                            "maintenance.alert_reviewed",
                            "maintenance.venue_held",
                            "maintenance.expired",
                        ]
                    ),
                )
            )
        ],
        "visits": [model_dict(x) for x in db.scalars(select(Visit).where(Visit.user_id == user.id))],
        "dish_diary": [
            model_dict(x) for x in db.scalars(select(DishEntry).where(DishEntry.user_id == user.id))
        ],
        "saved_venues": list(db.scalars(select(SavedVenue.venue_id).where(SavedVenue.user_id == user.id))),
        "submissions": [
            {**model_dict(x, ("content",)), "content": {k: v for k, v in x.content.items() if k != "media"}}
            for x in db.scalars(select(Submission).where(Submission.user_id == user.id))
        ],
    }


@app.delete("/api/me/data")
def clear_account_data(user=Depends(current_user), db=Depends(get_db)):
    submission_ids = list(db.scalars(select(Submission.id).where(Submission.user_id == user.id)))
    db.execute(delete(Job).where(Job.payload["submission_id"].as_string().in_(submission_ids)))
    erase_cases(db, user.id)
    if settings().app_mode == "local":
        paused = db.get(Counter, "research_paused") or Counter(key="research_paused")
        paused.value = 1
        db.add(paused)
    spot_ids = set(db.scalars(select(IdentifiedSpot.id).where(IdentifiedSpot.user_id == user.id)))
    db.execute(
        delete(Audit).where(
            Audit.actor == user.id,
            Audit.action.in_(
                [
                    "spot.merged",
                    "spot.prepared",
                    "spots.quality_cleanup",
                    "maintenance.alert_reviewed",
                    "maintenance.venue_held",
                    "maintenance.expired",
                ]
            ),
        )
    )
    for job in db.scalars(
        select(Job).where(
            Job.kind.in_(
                ["spot_inventory", "spot_enrich", "spot_refresh", "city_directory", "spot_deduplicate"]
            )
        )
    ):
        if job.payload.get("user_id") == user.id or job.payload.get("spot_id") in spot_ids:
            db.delete(job)
    for table in [Plan, Visit, DishEntry, SavedVenue, Submission, IdentifiedSpot]:
        db.execute(delete(table).where(table.user_id == user.id))
    user.profile = {}
    db.commit()
    return {"message": "Private application data erased. Your sign-in account remains available."}


@app.get("/api/venues")
def venues(
    category: str = "",
    q: str = Query(default="", max_length=150),
    area: str = "",
    cuisine: str = "",
    dining_format: str = "",
    vegetarian: bool = False,
    parking: bool = False,
    washroom: bool = False,
    max_price: float | None = Query(default=None, ge=0, le=100000, allow_inf_nan=False),
    limit: int = Query(default=300, ge=1, le=300),
    offset: int = Query(default=0, ge=0),
    user=Depends(current_user),
    db=Depends(get_db),
):
    query = select(Venue).where(Venue.is_demo == (settings().app_mode == "demo"), Venue.status == "published")
    if category:
        query = query.where(Venue.category == category)
    rows = list(db.scalars(query.order_by(Venue.name, Venue.id)))
    output = []
    for v in rows:
        if not v.is_demo and not (
            v.details.get("location_approval") and v.details.get("maps_identity", {}).get("confirmed_by")
        ):
            continue
        item = venue_dict(db, v, user)
        menu = item["menu"]
        place_matches = not q or any(text_matches(q, word) for word in [v.name, v.area, *v.tags])
        dishes = [
            d
            for d in menu["items"]
            if d["available"] is not False
            and (place_matches or text_matches(q, d["name"]) or text_matches(q, d["cuisine"]))
        ]
        if not place_matches and not dishes:
            continue
        if area and not text_matches(area, v.area):
            continue
        dishes = [
            d
            for d in dishes
            if (not cuisine or text_matches(cuisine, d["cuisine"]))
            and (not vegetarian or d["vegetarian"] is True)
            and (max_price is None or (d["price_inr"] is not None and d["price_inr"] <= max_price))
        ]
        if (cuisine or vegetarian or max_price is not None) and not dishes:
            continue
        if dining_format and menu["dining_format"] != dining_format:
            continue
        if (parking and menu["amenities"].get("parking") is not True) or (
            washroom and menu["amenities"].get("washroom") is not True
        ):
            continue
        output.append(item)
    return output[offset : offset + limit]


@app.get("/api/me/saved-venues")
def saved_venues(user=Depends(current_user), db=Depends(get_db)):
    rows = db.scalars(
        select(Venue)
        .join(SavedVenue, Venue.id == SavedVenue.venue_id)
        .where(
            SavedVenue.user_id == user.id,
            Venue.is_demo == (settings().app_mode == "demo"),
            Venue.status == "published",
        )
        .order_by(Venue.name, Venue.id)
    )
    return [
        venue_dict(db, v, user)
        for v in rows
        if v.is_demo
        or (v.details.get("location_approval") and v.details.get("maps_identity", {}).get("confirmed_by"))
    ]


@app.get("/api/venues/{venue_id}")
def venue_detail(venue_id: str, user=Depends(current_user), db=Depends(get_db)):
    v = accessible_venue(db, venue_id)
    if v.status != "published" and not is_admin(user):
        raise HTTPException(404, "Venue not published")
    return venue_dict(db, v, user)


@app.post("/api/venues/{venue_id}/save")
def save_venue(venue_id: str, user=Depends(current_user), db=Depends(get_db)):
    from .experience_api import published_venue

    published_venue(db, venue_id)
    row = db.get(SavedVenue, (user.id, venue_id))
    if row:
        db.delete(row)
    else:
        db.add(SavedVenue(user_id=user.id, venue_id=venue_id))
    db.commit()
    return {"saved": not bool(row)}


@app.put("/api/venues/{venue_id}/save")
def set_saved_venue(venue_id: str, data: SavedPlaceInput, user=Depends(current_user), db=Depends(get_db)):
    published_venue(db, venue_id)
    if data.saved:
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        insert = sqlite_insert if db.bind.dialect.name == "sqlite" else pg_insert
        db.execute(
            insert(SavedVenue)
            .values(user_id=user.id, venue_id=venue_id)
            .on_conflict_do_nothing(index_elements=["user_id", "venue_id"])
        )
    else:
        db.execute(delete(SavedVenue).where(SavedVenue.user_id == user.id, SavedVenue.venue_id == venue_id))
    db.commit()
    return {"saved": data.saved}


@app.post("/api/plans")
def create_plans(data: OutingRequest, user=Depends(current_user), db=Depends(get_db)):
    def investigate_gap():
        if not settings().autonomous_discovery or settings().app_mode == "demo":
            return None
        from .research import start_case

        query = data.query + " Coimbatore"
        existing = db.scalar(
            select(Investigation).where(
                Investigation.user_id == user.id,
                Investigation.query == query,
                Investigation.state.in_(["queued", "running"]),
            )
        )
        if existing:
            return existing.id
        day = datetime.now(timezone.utc).date().isoformat()
        from .collection_control import count_request, daily_limits

        if not count_request(db, f"research:{user.id}:{day}", daily_limits()["investigations"]):
            return None
        return start_case(db, user.id, query, {"planning_gap": True}).id

    if settings().app_mode == "live" and data.departure < datetime.now(timezone.utc) - timedelta(minutes=5):
        raise HTTPException(422, "Choose a future departure time")
    if km((data.lat, data.lng), (11.0168, 76.9558)) > 40:
        raise HTTPException(
            422, "The first release covers Coimbatore. Choose a starting point within 40 km of the city."
        )
    rows = list(
        db.scalars(
            select(Venue).where(Venue.is_demo == (settings().app_mode == "demo"), Venue.status == "published")
        )
    )
    claims = list(db.scalars(select(Claim).where(Claim.venue_id.in_([v.id for v in rows])))) if rows else []
    visited = set(db.scalars(select(Visit.venue_id).where(Visit.user_id == user.id)))
    warnings = []
    if settings().app_mode == "demo":
        route = lambda a, b, origin, destination: demo_leg(
            origin, destination, data.transport, data.party_size
        )
    else:
        if not rows:
            return {
                "options": [],
                "message": "No verified live venues have been published yet. The discovery and review queue needs real venue evidence.",
                "investigation_id": investigate_gap(),
                "excluded": {},
                "candidate_count": 0,
            }
        candidates = live_candidate_order(data, rows, claims)[:10]
        checked = []
        for v in candidates:
            try:
                place_id = v.details.get("google_place_id")
                if not place_id:
                    continue
                snapshot = google_details(db, place_id)
                if snapshot.get("businessStatus") != "OPERATIONAL":
                    continue
                # Google result used transiently, never overwrites merchant-owned evidence.
                windows = opening_windows(snapshot)
                if not windows:
                    warnings.append(f"Current opening windows unavailable for {v.name}")
                    continue
                checked.append(
                    SimpleNamespace(
                        **{**model_dict(v), "details": {**v.details, "provider_windows": windows}}
                    )
                )
            except Unavailable as exc:
                warnings.append(str(exc))
        rows = checked
        if not rows:
            return {
                "options": [],
                "message": "Current operating status could not be confirmed for eligible venues.",
                "excluded": {"live check unavailable": len(candidates)},
                "warnings": sorted(set(warnings)),
                "candidate_count": 0,
            }
        indexes = {"origin": 0, **{v.id: i + 1 for i, v in enumerate(rows)}}
        matrix = route_matrix(
            db, [(data.lat, data.lng)] + [(v.lat, v.lng) for v in rows], data.transport, data.departure
        )

        def route(a, b, origin, destination):
            leg = matrix.get((indexes[a], indexes[b]))
            if not leg:
                return None
            # Transport expense remains an explicit estimate, never a booking quote.
            estimate = demo_leg(origin, destination, data.transport, data.party_size)
            return {
                **leg,
                "cost": estimate["cost"],
                "basis": "Google Routes travel; estimated fuel/taxi cost",
            }

    result = build_plans(data, rows, claims, user.profile, visited, route)
    output = []
    for option in result["options"]:
        option["warnings"] += sorted(set(warnings))
        plan = Plan(user_id=user.id, request=data.model_dump(mode="json"), result=option)
        db.add(plan)
        db.flush()
        output.append(plan_dict(db, plan))
    db.commit()
    return {
        **result,
        "options": output,
        "investigation_id": investigate_gap() if not output and not result["candidate_count"] else None,
    }


@app.get("/api/plans")
def saved_plans(user=Depends(current_user), db=Depends(get_db)):
    return [
        plan_dict(db, p)
        for p in db.scalars(
            select(Plan).where(Plan.user_id == user.id, Plan.saved.is_(True)).order_by(Plan.created_at.desc())
        )
    ]


@app.get("/api/plans/{plan_id}")
def get_plan(plan_id: str, user=Depends(current_user), db=Depends(get_db)):
    return plan_dict(db, own_plan(db, plan_id, user))


@app.post("/api/plans/{plan_id}/save")
def save_plan(plan_id: str, user=Depends(current_user), db=Depends(get_db)):
    p = own_plan(db, plan_id, user)
    p.saved = not p.saved
    db.commit()
    return plan_dict(db, p)


@app.post("/api/visits")
def feedback(data: Feedback, user=Depends(current_user), db=Depends(get_db)):
    v = published_venue(db, data.venue_id)
    previous = db.scalar(
        select(Visit).where(
            Visit.user_id == user.id, Visit.venue_id == v.id, Visit.visited_on == data.visited_on.isoformat()
        )
    )
    if previous:
        raise HTTPException(409, "You already recorded a visit to this venue on that date")
    if v.status != "published":
        raise HTTPException(404, "Published venue not found")
    visit = Visit(
        user_id=user.id,
        **data.model_dump(mode="json"),
        experience={"tags": v.tags, "category": v.category, "venue_name": v.name},
    )
    db.add(visit)
    try:
        rebuild_taste(db, user)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "You already recorded a visit to this venue on that date")
    return model_dict(visit)


@app.get("/api/visits")
def visits(user=Depends(current_user), db=Depends(get_db)):
    return [
        model_dict(v)
        for v in db.scalars(select(Visit).where(Visit.user_id == user.id).order_by(Visit.visited_on.desc()))
    ]


@app.post("/api/submissions")
def submit(data: SocialInput, user=Depends(current_user), db=Depends(get_db)):
    try:
        safe_social_url(data.url)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    digest = hashlib.sha256(json.dumps(data.model_dump(), sort_keys=True).encode()).hexdigest()
    existing_job = db.scalar(select(Job).where(Job.key == f"analysis:{user.id}:{digest}"))
    if existing_job:
        existing = db.get(Submission, existing_job.payload["submission_id"])
        if existing:
            return model_dict(existing, ("content",))
    sub = Submission(user_id=user.id, url=data.url, content=data.model_dump(exclude={"url"}))
    db.add(sub)
    db.commit()
    enqueue(db, "analysis", {"submission_id": sub.id}, f"analysis:{user.id}:{digest}", priority=90)
    return model_dict(sub, ("content",))


@app.post("/api/submissions/{submission_id}/media")
async def upload_media(
    submission_id: str, file: UploadFile = File(...), user=Depends(current_user), db=Depends(get_db)
):
    sub = db.get(Submission, submission_id)
    if not sub or sub.user_id != user.id:
        raise HTTPException(404, "Submission not found")
    active_cases = list(
        db.scalars(
            select(Investigation).where(
                Investigation.user_id == user.id, Investigation.state.in_(["queued", "running"])
            )
        )
    )
    if any(c.context.get("submission_id") == sub.id for c in active_cases):
        raise HTTPException(409, "Cancel or finish this find's investigation before replacing its video")
    data = await file.read(settings().max_media_mb * 1024 * 1024 + 1)
    await file.close()
    if len(data) > settings().max_media_mb * 1024 * 1024:
        raise HTTPException(413, "Video exceeds the configured upload limit")
    try:
        media = media_payload(data, file.content_type)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    related = [
        j
        for j in db.scalars(select(Job).where(Job.kind == "analysis"))
        if j.payload.get("submission_id") == sub.id
    ]
    if any(j.state == "running" for j in related):
        raise HTTPException(409, "Analysis is running; wait for it to finish before adding media")
    media_key = f"media:{sub.id}:{hashlib.sha256(data).hexdigest()}"
    if any(j.key == media_key and j.state in {"queued", "done"} for j in related):
        return {"message": "This video has already been queued or analyzed"}
    for job in related:
        if job.state == "queued":
            job.state, job.completed_at = "cancelled", now()
            job.result = {"message": "Replaced by a submission with video"}
        if job.key == media_key and job.state == "failed":
            job.state, job.attempts, job.due_at, job.error = "queued", 0, now(), ""
    sub.content = {**sub.content, "media": media}
    sub.status = "queued"
    db.commit()
    enqueue(db, "analysis", {"submission_id": sub.id}, media_key, priority=90)
    return {"message": "Video queued; uploaded bytes are deleted after processing or after one day"}


@app.get("/api/submissions")
def submissions(user=Depends(current_user), db=Depends(get_db)):
    return [
        model_dict(s, ("content",))
        for s in db.scalars(
            select(Submission).where(Submission.user_id == user.id).order_by(Submission.created_at.desc())
        )
    ]


@app.delete("/api/submissions/{submission_id}")
def delete_submission(submission_id: str, user=Depends(current_user), db=Depends(get_db)):
    s = db.get(Submission, submission_id)
    if not s or s.user_id != user.id:
        raise HTTPException(404, "Submission not found")
    from .db import ResearchSource, ResearchTask, SourceAssessment

    related = [
        c.id
        for c in db.scalars(select(Investigation).where(Investigation.user_id == user.id))
        if c.context.get("submission_id") == s.id
    ]
    source_ids = list(db.scalars(select(ResearchSource.id).where(ResearchSource.case_id.in_(related))))
    db.execute(delete(SourceAssessment).where(SourceAssessment.source_id.in_(source_ids)))
    db.execute(delete(ResearchCorrection).where(ResearchCorrection.source_id.in_(source_ids)))
    for job in db.scalars(select(Job)):
        if (
            job.payload.get("case_id") in related
            or job.payload.get("source_id") in source_ids
            or job.payload.get("submission_id") == s.id
        ):
            db.delete(job)
    db.execute(delete(ResearchSource).where(ResearchSource.case_id.in_(related)))
    db.execute(delete(ResearchTask).where(ResearchTask.case_id.in_(related)))
    db.execute(delete(Investigation).where(Investigation.id.in_(related)))
    db.delete(s)
    db.commit()
    return {"message": "Submission and analysis erased"}


@app.post("/api/corrections")
def correction(data: ClaimInput, user=Depends(current_user), db=Depends(get_db)):
    accessible_venue(db, data.venue_id)
    try:
        claim = ingest_claim(db, data, user.id, trusted=is_admin(user))
        if claim.status == "review":
            enqueue(db, "refresh", {"venue_id": data.venue_id}, f"correction:{claim.id}", priority=85)
        return model_dict(claim)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get("/api/admin/overview")
def admin_overview(user=Depends(admin_user), db=Depends(get_db)):
    from .collection_control import daily_limits

    venues = list(db.scalars(select(Venue).where(Venue.is_demo == (settings().app_mode == "demo"))))
    claims = (
        list(db.scalars(select(Claim).where(Claim.venue_id.in_([v.id for v in venues])))) if venues else []
    )
    jobs = list(db.scalars(select(Job).order_by(Job.created_at.desc()).limit(100)))
    counts = {}
    for v in venues:
        counts[v.category] = counts.get(v.category, 0) + 1
    counter = db.get(Counter, "provider:" + datetime.now(timezone.utc).date().isoformat())
    heartbeat = db.get(Counter, "worker_heartbeat")
    return {
        "mode": settings().app_mode,
        "venues": [venue_dict(db, v) for v in venues],
        "review": [model_dict(c) for c in claims if c.status == "review"],
        "jobs": [model_dict(j) for j in jobs],
        "coverage": counts,
        "expired_claims": sum(c.status == "accepted" and c.expires_at < now() for c in claims),
        "integrations": integration_status(),
        "provider_calls_today": counter.value if counter else 0,
        "worker_heartbeat_age_seconds": max(0, int(time.time()) - heartbeat.value) if heartbeat else None,
        "provider_limit": daily_limits()["external"],
        "audit": [
            model_dict(a) for a in db.scalars(select(Audit).order_by(Audit.created_at.desc()).limit(40))
        ],
    }


@app.post("/api/admin/claims/{claim_id}/review")
def review_claim(claim_id: str, data: ReviewInput, user=Depends(admin_user), db=Depends(get_db)):
    claim = db.get(Claim, claim_id)
    if not claim:
        raise HTTPException(404, "Claim not found")
    accessible_venue(db, claim.venue_id)
    if claim.status != "review":
        raise HTTPException(409, "Claim is no longer waiting for review")
    if data.decision == "approve":
        if claim.expires_at <= now():
            raise HTTPException(422, "Expired evidence needs a new observation")
        apply_claim(db, claim, user.id)
    else:
        claim.status = "rejected"
    claim.reason = data.reason
    db.add(
        Audit(actor=user.id, action="claim." + data.decision, target=claim.id, detail={"reason": data.reason})
    )
    db.commit()
    return model_dict(claim)


@app.post("/api/admin/venues")
def add_venue(data: VenueInput, user=Depends(admin_user), db=Depends(get_db)):
    d = data.details
    if any(key in d for key in ["price_per_person", "hours", "closed", "vegetarian", "wheelchair"]):
        raise HTTPException(422, "Add critical facts through evidence after creating the venue")
    try:
        operations = VenueOperations.model_validate(d)
    except ValueError as exc:
        raise HTTPException(422, "Invalid planning details: " + str(exc)) from exc
    venue = Venue(
        **data.model_dump(exclude={"details"}),
        details=operations.model_dump(),
        status="pending",
        is_demo=settings().app_mode == "demo",
    )
    db.add(venue)
    db.commit()
    return venue_dict(db, venue)


@app.put("/api/admin/venues/{venue_id}/operations")
def venue_operations(venue_id: str, data: VenueOperations, user=Depends(admin_user), db=Depends(get_db)):
    venue = accessible_venue(db, venue_id)
    venue.details = {**venue.details, **data.model_dump(mode="json")}
    venue.revision += 1
    venue.updated_at = now()
    db.add(
        Audit(
            actor=user.id,
            action="venue.operations_updated",
            target=venue.id,
            detail={"branch_confirmed": data.branch_confirmed},
        )
    )
    db.commit()
    return venue_dict(db, venue)


@app.post("/api/admin/venues/{venue_id}/maps-identity")
def review_maps_identity(
    venue_id: str, data: MapsIdentityReview, user=Depends(admin_user), db=Depends(get_db)
):
    from .spot_identity import maps_reference, quality_issues, clean_name

    venue = accessible_venue(db, venue_id)
    if not data.checked or not venue.details.get("branch_confirmed"):
        raise HTTPException(422, "Check the branch, Maps place and matching location name")
    if km((venue.lat, venue.lng), (11.0168, 76.9558)) > 40:
        raise HTTPException(422, "The first inventory covers Coimbatore within 40 km")
    try:
        identity = maps_reference(data.maps_url)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    issues = quality_issues(data.name, venue.area, {"address": venue.address})
    identity["reviewed_warnings"] = issues
    for other in db.scalars(select(Venue).where(Venue.is_demo == venue.is_demo, Venue.id != venue.id)):
        if other.details.get("maps_identity", {}).get("place_key") == identity["place_key"]:
            raise HTTPException(409, "This exact Maps branch already has a venue record")
    previous = venue.name
    venue.name = clean_name(data.name)
    identity.update(
        {
            "name": venue.name,
            "confirmed_by": user.id,
            "confirmed_at": now(),
            "basis": "Operator independently checked name and exact Maps branch",
        }
    )
    venue.details = {
        **venue.details,
        "maps_identity": identity,
        "google_place_id": identity.get("place_id", ""),
    }
    if venue.status == "published":
        venue.status = "pending"
        venue.details = {k: v for k, v in venue.details.items() if k != "location_approval"}
    for spot in db.scalars(
        select(IdentifiedSpot).where(IdentifiedSpot.venue_id == venue.id, IdentifiedSpot.user_id == user.id)
    ):
        spot.data = {
            **spot.data,
            "maps_identity": identity,
            "name_status": "operator_maps_confirmed",
            "quality_issues": [],
            "aliases": list(dict.fromkeys([spot.name, *spot.data.get("aliases", [])])),
        }
        spot.name, spot.status, spot.updated_at = venue.name, "awaiting_approval", now()
    venue.revision += 1
    venue.updated_at = now()
    db.add(
        Audit(
            actor=user.id,
            action="venue.maps_identity_reviewed",
            target=venue.id,
            detail={"previous_name": previous, "reason": data.reason, "place_key": identity["place_key"]},
        )
    )
    db.commit()
    return venue_dict(db, venue)


@app.post("/api/admin/venues/{venue_id}/publish")
def publish_venue(venue_id: str, data: ReviewInput, user=Depends(admin_user), db=Depends(get_db)):
    venue = accessible_venue(db, venue_id)
    if data.decision == "approve":
        for spot in db.scalars(select(IdentifiedSpot).where(IdentifiedSpot.venue_id == venue_id)):
            if any(a["state"] == "open" for a in spot.data.get("maintenance_alerts", [])):
                raise HTTPException(422, "Review outstanding source-change/freshness alerts before approval")
        if not venue.details.get("branch_confirmed"):
            raise HTTPException(422, "Confirm the exact branch before approving this location")
        if not venue.is_demo and not venue.details.get("maps_identity", {}).get("confirmed_by"):
            raise HTTPException(422, "Confirm the location name and exact Google Maps place before approval")
        fields = set(
            db.scalars(
                select(Claim.field).where(
                    Claim.venue_id == venue_id, Claim.status == "accepted", Claim.expires_at > now()
                )
            )
        )
        if not {"price_per_person", "hours", "closed"}.issubset(fields):
            raise HTTPException(
                422, "Current accepted price, opening hours and operating status are required"
            )
        venue.status = "published"
        venue.details = {
            **venue.details,
            "location_approval": {"by": user.id, "at": now(), "reason": data.reason},
        }
        for spot in db.scalars(select(IdentifiedSpot).where(IdentifiedSpot.venue_id == venue.id)):
            spot.status, spot.updated_at = "approved", now()
    else:
        venue.status = "review"
    venue.revision += 1
    db.add(
        Audit(actor=user.id, action="venue." + venue.status, target=venue.id, detail={"reason": data.reason})
    )
    db.commit()
    return venue_dict(db, venue)


@app.post("/api/admin/refresh")
def refresh_all(user=Depends(admin_user)):
    schedule()
    return {"message": "Due refresh and discovery jobs queued; the worker processes them independently"}


@app.post("/api/admin/jobs/run")
def run_job(user=Depends(admin_user)):
    return {"processed": run_once()}


@app.post("/api/admin/jobs/{job_id}/retry")
def retry_job(job_id: str, user=Depends(admin_user), db=Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.state != "failed":
        raise HTTPException(409, "Only failed jobs can be retried manually")
    job.state, job.attempts, job.due_at, job.error = "queued", 0, now(), ""
    db.commit()
    return model_dict(job)


@app.post("/api/admin/discover")
def discover(data: dict, user=Depends(admin_user), db=Depends(get_db)):
    query = str(data.get("query", "Coimbatore food cafes entertainment"))[:300]
    key = hashlib.sha256(query.encode()).hexdigest() + ":" + datetime.now(timezone.utc).strftime("%Y%m%d%H")
    return model_dict(enqueue(db, "discovery", {"query": query}, "discovery:" + key))


@app.get("/api/admin/place-search")
def place_search(q: str, user=Depends(admin_user), db=Depends(get_db)):
    return {
        "places": google_search(db, q[:300] + " Coimbatore", 11.0168, 76.9558),
        "attribution": "Google Maps",
        "storage": "Search preview only; save place IDs and independently sourced venue facts",
    }


web_dist = ROOT / "web" / "dist"
if web_dist.exists():
    app.mount("/assets", StaticFiles(directory=web_dist / "assets"), name="assets")


@app.get("/{path:path}", include_in_schema=False)
def frontend(path: str):
    if path.startswith("api/"):
        raise HTTPException(404, "API route not found")
    target = (web_dist / path).resolve()
    if target.is_relative_to(web_dist.resolve()) and target.is_file():
        return FileResponse(target)
    if (web_dist / "index.html").exists():
        return FileResponse(web_dist / "index.html")
    return JSONResponse(
        {"message": "API ready. Run the web development server or build the web app.", "docs": "/docs"}
    )
