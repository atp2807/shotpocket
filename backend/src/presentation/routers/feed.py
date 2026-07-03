"""feed 라우터 — 공개(인증 없음). 세로 스와이프 무한 피드."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.features.feed.application.feed_service import FeedService
from src.presentation.schemas.feed.feed_schema import FeedResponse
from src.presentation.schemas.meme.meme_schema import MemeSummary

router = APIRouter(prefix="/api/feed", tags=["feed"])


@router.get("", response_model=FeedResponse)
def get_feed(
    cursor: str | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> FeedResponse:
    items, next_cursor = FeedService(db).list_feed(cursor=cursor, limit=limit)
    return FeedResponse(
        items=[MemeSummary.model_validate(m) for m in items],
        next_cursor=next_cursor,
    )
