"""ops 스키마 ORM 모델 — report."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.config.database import Base

SCHEMA = "ops"


class Report(Base):
    __tablename__ = "report"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    meme_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("meme.meme.id", ondelete="CASCADE"), index=True
    )
    # 정본 6값: COPYRIGHT | PORTRAIT_RIGHT | NSFW | HATE | SPAM | ETC
    reason_cd: Mapped[str] = mapped_column(String(32))
    # 신고=자동 비공개 원칙(무인): 접수 즉시 AUTO_HIDDEN.
    # 상태 전이: AUTO_HIDDEN(기본) → RESTORED(운영 복구) | REMOVED(삭제 확정). PENDING 없음.
    status_cd: Mapped[str] = mapped_column(String(16), default="AUTO_HIDDEN")
    contact: Mapped[str | None] = mapped_column(String(256))
    detail: Mapped[str | None] = mapped_column(Text)
    ip_hash: Mapped[str | None] = mapped_column(String(64))
    created_ts: Mapped[dt.datetime] = mapped_column(server_default=func.now())
