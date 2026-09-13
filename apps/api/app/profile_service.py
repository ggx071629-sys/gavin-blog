from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from .models import Profile
from .schemas import ProfileAdmin, ProfilePublic

PROFILE_SINGLETON_ID = 1
DEFAULT_NAME = "Gavin"
DEFAULT_TITLE = "后端工程师 / AI 应用开发者"
DEFAULT_BIO = "这里记录工程实践、问题排查与项目复盘，只留下持续校准过的技术笔记。"


def default_profile() -> Profile:
    """Transient default profile used when no row has been persisted yet."""
    return Profile(
        id=PROFILE_SINGLETON_ID,
        name=DEFAULT_NAME,
        title=DEFAULT_TITLE,
        bio=DEFAULT_BIO,
        skills_json="[]",
        avatar_url=None,
        city=None,
        city_visible=False,
        github_url=None,
        website_url=None,
        email=None,
        email_visible=False,
        resume_url=None,
        version=1,
    )


def get_profile(db: Session) -> Profile | None:
    return db.get(Profile, PROFILE_SINGLETON_ID)


def get_or_create_profile(db: Session) -> Profile:
    """Return the singleton row, persisting defaults on first admin access."""
    profile = get_profile(db)
    if profile is None:
        profile = default_profile()
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def parse_skills(skills_json: str | None) -> list[str]:
    try:
        value: Any = json.loads(skills_json) if skills_json else []
    except (TypeError, ValueError):
        return []
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def public_payload(profile: Profile) -> ProfilePublic:
    """Build the public response, stripping hidden or unset optional fields."""
    city = profile.city if profile.city_visible and profile.city else None
    email = profile.email if profile.email_visible and profile.email else None
    return ProfilePublic(
        name=profile.name,
        title=profile.title,
        bio=profile.bio,
        skills=parse_skills(profile.skills_json),
        avatar_url=profile.avatar_url,
        github_url=profile.github_url,
        website_url=profile.website_url,
        resume_url=profile.resume_url,
        city=city,
        email=email,
    )


def admin_payload(profile: Profile) -> ProfileAdmin:
    return ProfileAdmin(
        id=profile.id,
        name=profile.name,
        title=profile.title,
        bio=profile.bio,
        skills=parse_skills(profile.skills_json),
        avatar_url=profile.avatar_url,
        city=profile.city,
        city_visible=profile.city_visible,
        github_url=profile.github_url,
        website_url=profile.website_url,
        email=profile.email,
        email_visible=profile.email_visible,
        resume_url=profile.resume_url,
        version=profile.version,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )
