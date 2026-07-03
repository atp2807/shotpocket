"""feed 라우터 — 공개(인증 없음). 세로 스와이프 무한 피드."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.features.feed.application.feed_service import FeedService
from src.features.meme.infrastructure.meme_repo import load_meme_extras
from src.presentation.schemas.feed.feed_schema import FeedResponse
from src.presentation.schemas.meme.meme_schema import MemeSummary

router = APIRouter(prefix="/api/feed", tags=["feed"])


@router.get("", response_model=FeedResponse)
def get_feed(
    cursor: str | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
    sort: str = Query(default="recommended"),
    db: Session = Depends(get_db),
) -> FeedResponse:
    items, next_cursor = FeedService(db).list_feed(
        cursor=cursor, limit=limit, sort=sort
    )
    extras = load_meme_extras(db, [m.id for m in items])  # 1회 일괄 로드 (N+1 금지)
    return FeedResponse(
        items=[MemeSummary.from_meme(m, extras.get(m.id)) for m in items],
        next_cursor=next_cursor,
    )
