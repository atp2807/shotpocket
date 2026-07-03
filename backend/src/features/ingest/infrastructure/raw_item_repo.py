"""raw_item 리포지토리 — 파이프라인 상태/페이로드 조회·전이."""
from __future__ import annotations

import uuid

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from src.features.meme.domain.entities import MemeStatus
from src.infrastructure.db.models.ingest import RawItem
from src.infrastructure.db.models.meme import Meme

# dedup 비교 대상: 이미 수용(=거부 아님)되어 파이프라인에 올라간 raw_item 상태들
_ACCEPTED_STATES = ("DEDUPED", "ANALYZED", "TRANSCODED", "EMBEDDED", "PUBLISHED")


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

    def accepted_phashes(self) -> list[str]:
        """수용된 raw_item 들의 phash (dedup 근접중복 비교용)."""
        stmt = select(RawItem.phash).where(
            RawItem.phash.is_not(None),
            RawItem.status_cd.in_(_ACCEPTED_STATES),
        )
        return [row[0] for row in self.db.execute(stmt).all()]

    def meme_phashes(self) -> list[str]:
        """게시된 meme 들의 phash (dedup 근접중복 비교용). REMOVED 제외."""
        stmt = select(Meme.phash).where(
            Meme.phash.is_not(None),
            Meme.status_cd != MemeStatus.REMOVED,
        )
        return [row[0] for row in self.db.execute(stmt).all()]

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

    def set_phash(self, item_id: uuid.UUID, phash: str) -> None:
        stmt = update(RawItem).where(RawItem.id == item_id).values(phash=phash)
        self.db.execute(stmt)
        self.db.flush()

    def update_payload(self, item_id: uuid.UUID, payload: dict) -> None:
        """JSONB payload 전체 교체 (mutation tracking 미사용 → 전체 재할당)."""
        stmt = update(RawItem).where(RawItem.id == item_id).values(payload=payload)
        self.db.execute(stmt)
        self.db.flush()
