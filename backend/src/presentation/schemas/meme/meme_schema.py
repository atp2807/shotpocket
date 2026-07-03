"""meme 요청/응답 스키마 — pydantic v2.

- 미디어 URL(thumb_url/mp4_url/orig_url)은 저장 key → media_url() 로 변환해 노출.
- 웹 계약 필드: caption/meme_name/emotion_cd/situation (meme.analysis, situation 은
  저장 텍스트 그대로), like_cnt/download_cnt (stat.meme_stat, 없으면 0).
  목록 경로는 meme_repo.load_meme_extras() 로 일괄 로드 후 from_meme(m, extra)
  로 채운다 (N+1 금지).
"""
from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict

from src.shared.util.media import media_url


class MemeSummary(BaseModel):
    """목록/피드용 축약 짤."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    media_type_cd: str
    width: int | None = None
    height: int | None = None
    thumb_url: str | None = None
    mp4_url: str | None = None
    orig_url: str | None = None
    # 분석 필드 (meme.analysis)
    caption: str | None = None
    meme_name: str | None = None
    emotion_cd: str | None = None
    situation: str | None = None
    # 집계 필드 (stat.meme_stat, 없으면 0)
    like_cnt: int = 0
    download_cnt: int = 0

    @classmethod
    def from_meme(cls, m: Any, extra: dict | None = None) -> "MemeSummary":
        extra = extra or {}
        return cls(
            id=m.id,
            media_type_cd=m.media_type_cd,
            width=m.width,
            height=m.height,
            thumb_url=media_url(m.r2_thumb_key),
            mp4_url=media_url(m.r2_mp4_key),
            orig_url=media_url(m.r2_orig_key),
            caption=extra.get("caption"),
            meme_name=extra.get("meme_name"),
            emotion_cd=extra.get("emotion_cd"),
            situation=extra.get("situation"),
            like_cnt=int(extra.get("like_cnt") or 0),
            download_cnt=int(extra.get("download_cnt") or 0),
        )


class MemeResponse(BaseModel):
    """단건 짤 응답(엔티티 직접 반환, data 래퍼 없음)."""

    id: uuid.UUID
    media_type_cd: str
    status_cd: str
    origin_url: str | None = None
    source_cd: str | None = None
    width: int | None = None
    height: int | None = None
    duration_ms: int | None = None
    created_ts: dt.datetime | None = None
    # 클라이언트 접근용 미디어 URL
    thumb_url: str | None = None
    mp4_url: str | None = None
    orig_url: str | None = None
    # 분석 필드 (meme.analysis)
    caption: str | None = None
    meme_name: str | None = None
    emotion_cd: str | None = None
    situation: str | None = None
    # 집계 필드 (stat.meme_stat, 없으면 0)
    like_cnt: int = 0
    download_cnt: int = 0

    @classmethod
    def from_meme(cls, m: Any, extra: dict | None = None) -> "MemeResponse":
        extra = extra or {}
        return cls(
            id=m.id,
            media_type_cd=m.media_type_cd,
            status_cd=m.status_cd,
            origin_url=m.origin_url,
            source_cd=m.source_cd,
            width=m.width,
            height=m.height,
            duration_ms=m.duration_ms,
            created_ts=m.created_ts,
            thumb_url=media_url(m.r2_thumb_key),
            mp4_url=media_url(m.r2_mp4_key),
            orig_url=media_url(m.r2_orig_key),
            caption=extra.get("caption"),
            meme_name=extra.get("meme_name"),
            emotion_cd=extra.get("emotion_cd"),
            situation=extra.get("situation"),
            like_cnt=int(extra.get("like_cnt") or 0),
            download_cnt=int(extra.get("download_cnt") or 0),
        )


class SimilarResponse(BaseModel):
    """유사 짤 목록 응답."""

    items: list[MemeSummary]
    total: int


class EngageResponse(BaseModel):
    """좋아요/다운로드/조회 집계 응답. download 시 download_url(orig) 포함."""

    meme_id: uuid.UUID
    like_cnt: int | None = None
    download_cnt: int | None = None
    view_cnt: int | None = None
    download_url: str | None = None
