from __future__ import annotations

from fastapi import APIRouter, Query

from ..dependencies import DbSession
from ..pagination import PageOffset, SearchLimit
from ..schemas import SearchResult
from ..search import search

router = APIRouter(prefix="/search", tags=["public search"])


@router.get("", response_model=list[SearchResult])
def search_site(
    db: DbSession,
    q: str = Query(min_length=1, max_length=120),
    limit: SearchLimit = 20,
    offset: PageOffset = 0,
) -> list[SearchResult]:
    return search(db, q.strip(), limit, offset)
