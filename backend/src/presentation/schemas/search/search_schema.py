"""search 응답 스키마 — pydantic v2. 목록 표준 {items, total, page, page_size}."""
from __future__ import annotations

from pydantic import BaseModel

from src.presentation.schemas.meme.meme_schema import MemeSummary


class SearchResponse(BaseModel):
    items: list[MemeSummary]
    total: int
    page: int
    page_size: int
