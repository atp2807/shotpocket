"""ingest 스키마 ORM 모델 — source / raw_item."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.config.database import Base

SCHEMA = "ingest"


class Source(Base):
    __tablename__ = "source"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    name: Mapped[str] = mapped_column(String(128))
    base_url: Mapped[str | None] = mapped_column(Text)
    source_type_cd: Mapped[str] = mapped_column(String(32), default="WEB")
    priority: Mapped[int] = mapped_column(Integer, default=100)
    enabled_yn: Mapped[bool] = mapped_column(default=True)
    created_ts: Mapped[dt.datetime] = mapped_column(server_default=func.now())


class RawItem(Base):
    __tablename__ = "raw_item"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.source.id", ondelete="CASCADE"), index=True
    )
    origin_url: Mapped[str | None] = mapped_column(Text)
    phash: Mapped[str | None] = mapped_column(String(64), index=True)
    status_cd: Mapped[str] = mapped_column(String(16), default="FETCHED", index=True)
    reject_reason_cd: Mapped[str | None] = mapped_column(String(32))
    payload: Mapped[dict | None] = mapped_column(JSONB)
    created_ts: Mapped[dt.datetime] = mapped_column(server_default=func.now())
    updated_ts: Mapped[dt.datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
