"""meme 요청/응답 스키마 — pydantic v2."""
from __future__ import annotations

import datetime as dt
import uuid

from pydantic import BaseModel, ConfigDict


class MemeResponse(BaseModel):
    """단건 짤 응답(엔티티 직접 반환, data 래퍼 없음)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    media_type_cd: str
    status_cd: str
    origin_url: str | None = None
    source_cd: str | None = None
    r2_mp4_key: str | None = None
    r2_thumb_key: str | None = None
    width: int | None = None
    height: int | None = None
    duration_ms: int | None = None
    created_ts: dt.datetime | None = None


class MemeSummary(BaseModel):
    """목록/피드용 축약 짤."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    media_type_cd: str
    r2_mp4_key: str | None = None
    r2_thumb_key: str | None = None
    width: int | None = None
    height: int | None = None


class SimilarResponse(BaseModel):
    """유사 짤 목록 응답."""

    items: list[MemeSummary]
    total: int


class EngageResponse(BaseModel):
    """좋아요/다운로드 집계 응답."""

    meme_id: uuid.UUID
    like_cnt: int | None = None
    download_cnt: int | None = None
