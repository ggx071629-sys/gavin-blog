from __future__ import annotations

from fastapi import APIRouter

from ..dependencies import DbSession
from ..profile_service import default_profile, get_profile, public_payload
from ..schemas import ProfilePublic

router = APIRouter(prefix="/profile", tags=["public profile"])


@router.get("", response_model=ProfilePublic, response_model_exclude_none=True)
def get_public_profile(db: DbSession) -> ProfilePublic:
    profile = get_profile(db)
    if profile is None:
        profile = default_profile()
    return public_payload(profile)
