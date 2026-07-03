"""search 라우터 — 공개(인증 없음)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.features.meme.infrastructure.meme_repo import load_meme_extras
from src.features.search.application.search_service import SearchService
from src.presentation.deps import get_ip_hash
from src.presentation.schemas.meme.meme_schema import MemeSummary
from src.presentation.schemas.search.search_schema import SearchResponse

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("", response_model=SearchResponse)
def search(
    request: Request,
    q: str = Query(default="", description="검색어"),
    page: int = Query(default=1, ge=1),
    db: Session = Depends(get_db),
) -> SearchResponse:
    items, total, page_out, page_size = SearchService(db).search(
        q=q, page=page, ip_hash=get_ip_hash(request)
    )
    extras = load_meme_extras(db, [m.id for m in items])  # 1회 일괄 로드 (N+1 금지)
    return SearchResponse(
        items=[MemeSummary.from_meme(m, extras.get(m.id)) for m in items],
        total=total,
        page=page_out,
        page_size=page_size,
    )
