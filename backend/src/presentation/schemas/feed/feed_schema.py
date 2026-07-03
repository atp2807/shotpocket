"""feed 응답 스키마 — pydantic v2. 피드만 커서 {items, next_cursor}."""
from __future__ import annotations

from pydantic import BaseModel

from src.presentation.schemas.meme.meme_schema import MemeSummary


class FeedResponse(BaseModel):
    items: list[MemeSummary]
    next_cursor: str | None = None
