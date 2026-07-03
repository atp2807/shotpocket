"""feed 리포지토리 — 커서(keyset) 페이지네이션."""
from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select, tuple_
from sqlalchemy.orm import Session

from src.features.meme.domain.entities import MemeStatus
from src.infrastructure.db.models.meme import Meme
from src.infrastructure.db.models.stat import MemeStat


class FeedRepo:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_feed(
        self,
        after_rank: Decimal | None,
        after_id: uuid.UUID | None,
        limit: int,
    ) -> list[tuple[Meme, Decimal]]:
        """(rank_score DESC, id DESC) keyset 정렬. 커서 이후 limit건 반환.

        OFFSET 대신 keyset 을 쓰는 이유: 무한 세로 스와이프에서 새 항목 유입에도
        중복/누락 없이 안정적으로 다음 페이지를 얻기 위함.
        """
        rank = func_coalesce_rank()
        stmt = (
            select(Meme, rank.label("rank_score"))
            .join(MemeStat, MemeStat.meme_id == Meme.id, isouter=True)
            .where(Meme.status_cd == MemeStatus.ACTIVE)
        )
        if after_rank is not None and after_id is not None:
            # (rank, id) < (after_rank, after_id) — 내림차순 keyset
            stmt = stmt.where(
                tuple_(rank, Meme.id) < tuple_(after_rank, after_id)
            )
        stmt = stmt.order_by(rank.desc(), Meme.id.desc()).limit(limit)
        rows = self.db.execute(stmt).all()
        return [(row[0], row[1]) for row in rows]


def func_coalesce_rank():
    """rank_score NULL 을 0 으로 폴백(통계 미집계 신규 짤도 노출)."""
    from sqlalchemy import func

    return func.coalesce(MemeStat.rank_score, 0)
