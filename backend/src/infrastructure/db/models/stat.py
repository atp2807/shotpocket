"""stat 스키마 ORM 모델 — meme_stat / query_log."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.config.database import Base

SCHEMA = "stat"


class MemeStat(Base):
    __tablename__ = "meme_stat"
    __table_args__ = {"schema": SCHEMA}

    meme_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("meme.meme.id", ondelete="CASCADE"),
        primary_key=True,
    )
    view_cnt: Mapped[int] = mapped_column(Integer, default=0)
    like_cnt: Mapped[int] = mapped_column(Integer, default=0)
    download_cnt: Mapped[int] = mapped_column(Integer, default=0)
    rank_score: Mapped[float] = mapped_column(Numeric(12, 4), default=0, index=True)
    updated_ts: Mapped[dt.datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )


class QueryLog(Base):
    __tablename__ = "query_log"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    query_text: Mapped[str] = mapped_column(Text)
    result_cnt: Mapped[int] = mapped_column(Integer, default=0)
    failed_yn: Mapped[bool] = mapped_column(default=False)
    ip_hash: Mapped[str | None] = mapped_column(String(64))
    created_ts: Mapped[dt.datetime] = mapped_column(server_default=func.now())
