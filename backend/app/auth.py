import hashlib
import secrets
from datetime import datetime, timedelta, timezone
import httpx
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .config import settings
from .db import User, SessionToken, Counter, get_db, now
from .providers import increment_bounded

bearer = HTTPBearer(auto_error=False)


def create_demo_session(db):
    user = User(name="Explorer", profile={"liked_tags": [], "avoided_tags": [], "learn_from_visits": True})
    if settings().app_mode == "local":
        user = db.get(User, "local-operator") or User(
            id="local-operator", name="Local researcher", profile={}
        )
    db.add(user)
    db.flush()
    token = secrets.token_urlsafe(40)
    db.add(
        SessionToken(
            token_hash=hashlib.sha256(token.encode()).hexdigest(),
            user_id=user.id,
            expires_at=(datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        )
    )
    db.commit()
    return {"access_token": token}


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db=Depends(get_db)):
    if not credentials:
        raise HTTPException(401, "Sign in to continue")
    cfg = settings()
    if cfg.app_mode in {"demo", "local"}:
        session = db.get(SessionToken, hashlib.sha256(credentials.credentials.encode()).hexdigest())
        if not session or session.expires_at < now():
            raise HTTPException(401, "Demo session expired; enter the demo again")
        user = db.get(User, session.user_id)
        if not user:
            raise HTTPException(401, "Account not found")
    else:
        try:
            r = httpx.get(
                cfg.supabase_url.rstrip("/") + "/auth/v1/user",
                headers={
                    "Authorization": "Bearer " + credentials.credentials,
                    "apikey": cfg.supabase_publishable_key,
                },
                timeout=10,
            )
            if r.status_code != 200:
                raise HTTPException(401, "Session invalid or expired")
            identity = r.json()
            user_id = identity["id"]
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            raise HTTPException(503, "Sign-in service is unavailable") from exc
        user = db.get(User, user_id)
        if not user:
            user = User(
                id=user_id,
                name=str(identity.get("user_metadata", {}).get("name", "Explorer"))[:60],
                profile={},
            )
            db.add(user)
            db.commit()
        if not is_admin(user):
            signed_off = db.get(Counter, "launch_data_approved")
            if cfg.release_stage == "internal" or not signed_off or not signed_off.value:
                raise HTTPException(
                    403, "Coimbatore data verification is in progress; test access has not opened"
                )
            if cfg.release_stage == "test" and user.id not in [
                x.strip() for x in cfg.test_user_ids.split(",")
            ]:
                raise HTTPException(403, "This release is open only to invited test users")
    minute = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
    if not increment_bounded(db, f"request:{user.id}:{minute}", 120):
        raise HTTPException(429, "Too many requests; please wait a minute")
    return user


def is_admin(user):
    return (
        settings().app_mode == "demo"
        or (settings().app_mode == "local" and user.id == "local-operator")
        or user.id in settings().admin_user_ids.split(",")
    )


def admin_user(user=Depends(current_user)):
    if not is_admin(user):
        raise HTTPException(403, "Administrator access required")
    return user
