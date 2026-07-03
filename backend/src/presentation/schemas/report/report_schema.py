"""report 요청/응답 스키마 — pydantic v2."""
from __future__ import annotations

import datetime as dt
import uuid

from pydantic import BaseModel, ConfigDict, Field


class ReportCreateRequest(BaseModel):
    """신고 접수 요청. 계정이 없으므로 신고자 식별 없음(선택 contact 만)."""

    meme_id: uuid.UUID
    # 사유코드 정본 6값: COPYRIGHT | PORTRAIT_RIGHT | NSFW | HATE | SPAM | ETC
    reason_cd: str = Field(min_length=1, max_length=32)
    contact: str | None = Field(default=None, max_length=256)
    detail: str | None = Field(default=None, max_length=2000)


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    meme_id: uuid.UUID
    reason_cd: str
    status_cd: str
    created_ts: dt.datetime | None = None


class ReportListResponse(BaseModel):
    """운영용 신고 목록 {items, total, page, page_size}."""

    items: list[ReportResponse]
    total: int
    page: int
    page_size: int
