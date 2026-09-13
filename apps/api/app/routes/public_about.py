from __future__ import annotations

from fastapi import APIRouter

from ..about_page_service import (
    current_revision,
    default_about_content,
    get_about_page,
    parse_content,
)
from ..dependencies import DbSession
from ..schemas import AboutPageContent

router = APIRouter(prefix="/about-page", tags=["public about page"])


@router.get("", response_model=AboutPageContent)
def get_public_about_page(db: DbSession) -> AboutPageContent:
    page = get_about_page(db)
    revision = current_revision(db, page) if page is not None else None
    if revision is not None:
        return parse_content(revision.content_json)
    return default_about_content()
