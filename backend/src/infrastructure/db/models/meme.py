"""meme 스키마 ORM 모델 — meme / analysis / embedding."""
from __future__ import annotations

import datetime as dt
import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.config.database import Base

SCHEMA = "meme"


class Meme(Base):
    __tablename__ = "meme"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    phash: Mapped[str | None] = mapped_column(String(64), index=True)
    # 정본 어휘: STILL(스틸컷) | LOOP(루프 움짤)
    media_type_cd: Mapped[str] = mapped_column(String(16), default="STILL")
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    r2_orig_key: Mapped[str | None] = mapped_column(String(512))
    r2_mp4_key: Mapped[str | None] = mapped_column(String(512))
    r2_thumb_key: Mapped[str | None] = mapped_column(String(512))
    origin_url: Mapped[str | None] = mapped_column(Text)
    source_cd: Mapped[str | None] = mapped_column(String(32))
    status_cd: Mapped[str] = mapped_column(String(16), default="ACTIVE", index=True)
    created_ts: Mapped[dt.datetime] = mapped_column(server_default=func.now())
    updated_ts: Mapped[dt.datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )


class Analysis(Base):
    __tablename__ = "analysis"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    meme_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.meme.id", ondelete="CASCADE"), index=True
    )
    caption: Mapped[str | None] = mapped_column(Text)
    situation: Mapped[str | None] = mapped_column(Text)
    emotion_cd: Mapped[str | None] = mapped_column(String(32))
    ocr_text: Mapped[str | None] = mapped_column(Text)
    usage_context: Mapped[str | None] = mapped_column(Text)
    character_name: Mapped[str | None] = mapped_column(String(128))
    meme_name: Mapped[str | None] = mapped_column(String(128))
    lang_cd: Mapped[str | None] = mapped_column(String(8))
    nsfw_score: Mapped[float | None] = mapped_column(Numeric(5, 4))
    confidence: Mapped[float | None] = mapped_column(Numeric(5, 4))
    model_cd: Mapped[str | None] = mapped_column(String(64))
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default="{}")
    created_ts: Mapped[dt.datetime] = mapped_column(server_default=func.now())


class Embedding(Base):
    __tablename__ = "embedding"
    __table_args__ = {"schema": SCHEMA}

    meme_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.meme.id", ondelete="CASCADE"),
        primary_key=True,
    )
    # 차원 384 (intfloat/multilingual-e5-small). HNSW cosine 인덱스는 마이그레이션에서 생성.
    embedding: Mapped[list[float]] = mapped_column(Vector(384))
