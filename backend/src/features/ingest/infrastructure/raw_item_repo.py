"""raw_item 리포지토리 — 파이프라인 상태/페이로드 조회·전이."""
from __future__ import annotations

import uuid

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from src.features.meme.domain.entities import MemeStatus
from src.infrastructure.db.models.ingest import RawItem, Source
from src.infrastructure.db.models.meme import Meme

# dedup 비교 대상: 이미 수용(=거부 아님)되어 파이프라인에 올라간 raw_item 상태들
_ACCEPTED_STATES = ("DEDUPED", "ANALYZED", "TRANSCODED", "EMBEDDED", "PUBLISHED")


class RawItemRepo:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_by_status(
        self,
        status_cd: str,
        limit: int = 100,
        *,
        include_source_types: set[str] | None = None,
        exclude_source_types: set[str] | None = None,
    ) -> list[RawItem]:
        """대기열 조회. include/exclude_source_types 로 소스 유형 스코핑.

        크롤 환경(서버·맥)마다 이미지 파일이 로컬 디스크에만 있어, 서로 다른
        머신이 크롤한 raw_item 을 잘못 집어가면(파일 없음) 처리가 깨진다.
        환경별 진입점(scheduler_main.py=서버, nightly_batch.py=맥)이 이 스코핑으로
        서로의 대기열을 침범하지 않게 한다.
        """
        stmt = select(RawItem).where(RawItem.status_cd == status_cd)
        if include_source_types or exclude_source_types:
            stmt = stmt.join(Source, Source.id == RawItem.source_id)
            if include_source_types:
                stmt = stmt.where(Source.source_type_cd.in_(include_source_types))
            if exclude_source_types:
                stmt = stmt.where(Source.source_type_cd.notin_(exclude_source_types))
        stmt = stmt.order_by(RawItem.created_ts.asc()).limit(limit)
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
