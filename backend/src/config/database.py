"""데이터베이스 엔진/세션 — SQLAlchemy 2.0 sync (psycopg2).

get_db 는 FastAPI 의존성. 요청당 세션을 열고 종료 시 닫는다.
스키마는 4개(meme/ingest/stat/ops) — public 사용 금지, 모델 __table_args__ 에서 지정.
"""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from src.config.settings import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    future=True,
    echo=settings.DEBUG,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    future=True,
)


class Base(DeclarativeBase):
    """전 ORM 모델의 declarative base."""


def get_db() -> Iterator[Session]:
    """요청 스코프 DB 세션 의존성."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
