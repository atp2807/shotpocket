"""meme 리포지토리 — SQLAlchemy 쿼리."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.features.meme.domain.entities import MemeStatus
from src.infrastructure.db.models.meme import Embedding, Meme
from src.infrastructure.db.models.stat import MemeStat


class MemeRepo:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, meme_id: uuid.UUID) -> Meme | None:
        return self.db.get(Meme, meme_id)

    def get_active_by_id(self, meme_id: uuid.UUID) -> Meme | None:
        stmt = select(Meme).where(
            Meme.id == meme_id, Meme.status_cd == MemeStatus.ACTIVE
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_similar(self, meme_id: uuid.UUID, limit: int = 20) -> list[Meme]:
        """유사 짤 목록.

        placeholder: 임베딩 스텁(0벡터)이라 pgvector cosine 검색이 무의미하므로
        현재는 rank_score DESC 폴백으로 인기순을 반환한다. 실제 임베딩 연결 후
        아래 pgvector 절로 교체:
            base = select(Embedding.embedding).where(Embedding.meme_id == meme_id)
            stmt = (select(Meme).join(Embedding, ...)
                    .order_by(Embedding.embedding.cosine_distance(base)))
        """
        _ = Embedding  # 실제 유사도 구현 시 사용
        stmt = (
            select(Meme)
            .join(MemeStat, MemeStat.meme_id == Meme.id, isouter=True)
            .where(Meme.status_cd == MemeStatus.ACTIVE, Meme.id != meme_id)
            .order_by(MemeStat.rank_score.desc().nullslast())
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def set_status(self, meme_id: uuid.UUID, status_cd: str) -> None:
        meme = self.db.get(Meme, meme_id)
        if meme is not None:
            meme.status_cd = status_cd
            self.db.flush()
