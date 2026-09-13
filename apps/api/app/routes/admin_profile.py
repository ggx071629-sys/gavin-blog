from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response

from ..assistant_index.outbox import enqueue_profile
from ..assistant_resume.queue import RefreshConflict, RefreshCooldown, refresh, sync_binding
from ..assistant_resume.schemas import ResumeRefresh, ResumeStatus, status_view
from ..dependencies import DbSession, require_admin, require_session_csrf
from ..models import AdminSession
from ..profile_service import admin_payload, get_or_create_profile
from ..schemas import ProfileAdmin, ProfileUpdate
from ..time_utils import utc_now

router = APIRouter(prefix="/admin/profile", tags=["admin profile"])


@router.get("", response_model=ProfileAdmin)
def get_admin_profile(
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_admin)],
) -> ProfileAdmin:
    return admin_payload(get_or_create_profile(db))


@router.patch("", response_model=ProfileAdmin)
def update_admin_profile(
    payload: ProfileUpdate,
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_session_csrf)],
) -> ProfileAdmin:
    profile = get_or_create_profile(db)
    if profile.version != payload.version:
        raise HTTPException(status_code=409, detail="profile was updated elsewhere")

    profile.name = payload.name
    profile.title = payload.title
    profile.bio = payload.bio
    profile.skills_json = json.dumps(payload.skills, ensure_ascii=False)
    profile.avatar_url = str(payload.avatar_url) if payload.avatar_url else None
    profile.city = payload.city or None
    profile.city_visible = payload.city_visible
    profile.github_url = str(payload.github_url) if payload.github_url else None
    profile.website_url = str(payload.website_url) if payload.website_url else None
    profile.email = payload.email or None
    profile.email_visible = payload.email_visible
    profile.resume_url = str(payload.resume_url) if payload.resume_url else None
    profile.version += 1
    profile.updated_at = utc_now()
    enqueue_profile(db, profile)
    sync_binding(db, profile.resume_url)

    db.commit()
    db.refresh(profile)
    return admin_payload(profile)


@router.get("/resume", response_model=ResumeStatus)
def get_resume_status(
    response: Response,
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_admin)],
) -> ResumeStatus:
    response.headers["Cache-Control"] = "no-store"
    return status_view(db)


@router.post("/resume/refresh", response_model=ResumeStatus, status_code=202)
def refresh_resume(
    payload: ResumeRefresh,
    response: Response,
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_session_csrf)],
) -> ResumeStatus:
    response.headers["Cache-Control"] = "no-store"
    try:
        refresh(db, payload.binding_epoch)
    except RefreshConflict as exc:
        raise HTTPException(409, str(exc), headers={"Cache-Control": "no-store"}) from None
    except RefreshCooldown as exc:
        raise HTTPException(
            429,
            "resume_refresh_cooldown",
            headers={
                "Retry-After": str(exc.seconds),
                "Cache-Control": "no-store",
            },
        ) from None
    db.commit()
    return status_view(db)
