"""raw_item 리포지토리 — 파이프라인 상태 조회/전이."""
from __future__ import annotations

import uuid

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from src.infrastructure.db.models.ingest import RawItem


class RawItemRepo:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_by_status(self, status_cd: str, limit: int = 100) -> list[RawItem]:
        stmt = (
            select(RawItem)
            .where(RawItem.status_cd == status_cd)
            .order_by(RawItem.created_ts.asc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def exists_phash(self, phash: str) -> bool:
        stmt = select(RawItem.id).where(RawItem.phash == phash).limit(1)
        return self.db.execute(stmt).first() is not None

    def create(
        self, source_id: uuid.UUID, origin_url: str, phash: str | None, payload: dict | None
    ) -> RawItem:
        item = RawItem(
            source_id=source_id, origin_url=origin_url, phash=phash, payload=payload
        )
        self.db.add(item)
        self.db.flush()
        return item

    def set_status(
        self, item_id: uuid.UUID, status_cd: str, reject_reason_cd: str | None = None
    ) -> None:
        stmt = (
            update(RawItem)
            .where(RawItem.id == item_id)
            .values(status_cd=status_cd, reject_reason_cd=reject_reason_cd)
        )
        self.db.execute(stmt)
        self.db.flush()
