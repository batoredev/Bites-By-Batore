"""Claude teaching on the owner's behalf, through the owner's own controls.

Every decision goes through the same endpoint the owner would use, so the agent
learns from it in exactly the same way. Each one is tagged with the teacher
actor, and a snapshot of every record it can touch is saved first, so all the
teaching can be listed, spot-checked and undone in one step.
"""

import json
from types import SimpleNamespace

from fastapi import HTTPException
from sqlalchemy import select

from . import spots_api
from .db import Audit, IdentifiedSpot, Venue, now
from .learned import TEACHER, TEACHER_ACTOR
from .spot_identity import name_key

ACTIONS = {"real", "reject", "category", "rename", "area", "maps", "same_as", "distinct", "cart"}
VENUE_FIELDS = ("name", "category", "area", "lat", "lng", "status", "revision")


def _snap(row):
    return {
        "id": row.id,
        "name": row.name,
        "category": row.category,
        "area": row.area,
        "status": row.status,
        "venue_id": row.venue_id,
        "data": row.data,
    }


def _touched(db, owner, decision):
    """Every record a decision might change, including same-name records a rejection holds."""
    ids = {decision["id"], decision.get("target"), decision.get("other")} - {None}
    rows = {r.id: r for r in db.scalars(select(IdentifiedSpot).where(IdentifiedSpot.id.in_(ids)))}
    if decision["action"] == "reject" and decision["id"] in rows:
        key = name_key(rows[decision["id"]].name)
        for row in db.scalars(select(IdentifiedSpot).where(IdentifiedSpot.user_id == owner)):
            if name_key(row.name) == key:
                rows[row.id] = row
    return list(rows.values())


def _apply(db, owner, decision):
    user = SimpleNamespace(id=owner)
    ident, action = decision["id"], decision["action"]
    if action == "real":
        return spots_api.edit_spot(ident, spots_api.SpotEdit(release=True), user, db)
    if action == "category":
        return spots_api.edit_spot(ident, spots_api.SpotEdit(category=decision["category"]), user, db)
    if action == "rename":
        return spots_api.edit_spot(ident, spots_api.SpotEdit(name=decision["name"]), user, db)
    if action == "area":
        return spots_api.edit_spot(ident, spots_api.SpotEdit(area=decision["area"]), user, db)
    if action == "maps":
        return spots_api.edit_spot(ident, spots_api.SpotEdit(maps_url=decision["maps_url"]), user, db)
    if action == "reject":
        body = spots_api.SpotRejection(
            kind=decision["kind"],
            block_creator=decision.get("block_creator", False),
            reason=decision.get("note", "")[:500],
        )
        return spots_api.reject_spot(ident, body, user, db)
    if action == "same_as":
        return spots_api.same_as(ident, spots_api.SameAs(target_id=decision["target"]), user, db)
    if action == "distinct":
        body = spots_api.KeepApart(other_id=decision["other"], chain=decision.get("chain", False))
        return spots_api.keep_apart(ident, body, user, db)
    if action == "cart":
        row = db.get(IdentifiedSpot, ident)
        if not row or row.user_id != owner:
            raise HTTPException(404, "Place not found")
        if row.venue_id:
            spots_api._drop_test_venue(db, row)
        from .scope import CART_REASON

        row.data = spots_api._tag(
            {
                **row.data,
                "scope_hold": "street_cart",
                "quality_issues": [CART_REASON],
                "previous_status": row.status,
            }
        )
        row.status, row.updated_at = "quarantined", now()
        db.commit()
        return {"id": row.id, "status": row.status}
    raise ValueError("Unknown action " + action)


def apply(db, owner, decisions):
    """Apply decisions in order. Each is logged with a before-snapshot for undo."""
    done, failed = [], []
    seq = len(list(db.scalars(select(Audit.id).where(Audit.actor == TEACHER_ACTOR))))
    for decision in decisions:
        if decision.get("action") not in ACTIONS or not decision.get("id"):
            failed.append({"decision": decision, "error": "Unknown action or missing id"})
            continue
        before = _touched(db, owner, decision)
        venues = [db.get(Venue, r.venue_id) for r in before if r.venue_id]
        snapshot = {
            "rows": [_snap(r) for r in before],
            "venues": [{"id": v.id, **{k: getattr(v, k) for k in VENUE_FIELDS}} for v in venues if v],
        }
        snapshot = json.loads(json.dumps(snapshot, default=str))
        token = TEACHER.set(TEACHER_ACTOR)
        try:
            result = _apply(db, owner, decision)
        except (HTTPException, ValueError) as exc:
            db.rollback()
            failed.append({"decision": decision, "error": str(getattr(exc, "detail", exc))})
            continue
        finally:
            TEACHER.reset(token)
        seq += 1
        db.add(
            Audit(
                actor=TEACHER_ACTOR,
                action="teach." + decision["action"],
                target=decision["id"],
                detail={"seq": seq, "decision": decision, "before": snapshot},
            )
        )
        db.commit()
        done.append(result)
    return {"applied": len(done), "failed": failed}


def undo(db, owner):
    """Restore every record to its state before Claude's teaching, newest decision first."""
    from . import test_inventory

    logs = sorted(
        db.scalars(select(Audit).where(Audit.actor == TEACHER_ACTOR, Audit.action.like("teach.%"))),
        key=lambda log: (log.created_at, log.detail.get("seq", 0)),
        reverse=True,
    )
    restored = 0
    for log in logs:
        for snap in log.detail["before"]["rows"]:
            row = db.get(IdentifiedSpot, snap["id"])
            if not row or row.user_id != owner:
                continue
            row.name, row.category, row.area = snap["name"], snap["category"], snap["area"]
            row.status, row.data, row.updated_at = snap["status"], snap["data"], now()
            kept = snap["venue_id"] and db.get(Venue, snap["venue_id"])
            row.venue_id = snap["venue_id"] if kept else ""
            if snap["venue_id"] and not kept and row.status == "approved":
                row.status = "identified"  # Its test venue was removed; republished below.
            restored += 1
        for item in log.detail["before"]["venues"]:
            venue = db.get(Venue, item["id"])
            if venue:
                for key in VENUE_FIELDS:
                    setattr(venue, key, item[key])
        log.action = "undone." + log.action
    db.flush()
    republished = test_inventory.publish(db, owner)["published"]
    db.add(Audit(actor=owner, action="teach.undo_all", target=owner, detail={"decisions": len(logs)}))
    db.commit()
    return {"decisions_undone": len(logs), "records_restored": restored, "republished": republished}


def report(db, owner):
    """What Claude taught, for the owner's spot-check."""
    logs = list(db.scalars(select(Audit).where(Audit.actor == TEACHER_ACTOR, Audit.action.like("teach.%"))))
    by_action = {}
    for log in logs:
        by_action[log.action] = by_action.get(log.action, 0) + 1
    return {"decisions": len(logs), "by_action": by_action}
