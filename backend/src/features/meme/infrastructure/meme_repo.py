"""meme 리포지토리 — SQLAlchemy 쿼리."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.features.meme.domain.entities import MemeStatus
from src.infrastructure.db.models.meme import Analysis, Embedding, Meme
from src.infrastructure.db.models.stat import MemeStat


def load_meme_extras(db: Session, ids: list[uuid.UUID]) -> dict[uuid.UUID, dict]:
    """meme id 목록의 응답 보강 필드를 1회 쿼리로 일괄 로드 (N+1 금지).

    반환: {meme_id: {caption, meme_name, emotion_cd, situation,
                     like_cnt, download_cnt}}
    analysis 는 1:N 가능 — created_ts 오름차순으로 덮어써 최신 분석이 남는다.
    stat 없는 짤은 like/download 0.
    """
    if not ids:
        return {}
    rows = db.execute(
        select(
            Meme.id,
            Analysis.caption,
            Analysis.meme_name,
            Analysis.emotion_cd,
            Analysis.situation,
            Analysis.tags,
            MemeStat.like_cnt,
            MemeStat.download_cnt,
        )
        .join(Analysis, Analysis.meme_id == Meme.id, isouter=True)
        .join(MemeStat, MemeStat.meme_id == Meme.id, isouter=True)
        .where(Meme.id.in_(ids))
        .order_by(Analysis.created_ts.asc().nullsfirst())
    ).all()
    extras: dict[uuid.UUID, dict] = {}
    for mid, caption, meme_name, emotion_cd, situation, tags, like_cnt, download_cnt in rows:
        extras[mid] = {
            "caption": caption,
            "meme_name": meme_name,
            "emotion_cd": emotion_cd,
            "situation": situation,
            "tags": list(tags or []),
            "like_cnt": int(like_cnt or 0),
            "download_cnt": int(download_cnt or 0),
        }
    return extras


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
        """유사 짤 목록 — 기준 짤 임베딩 코사인 이웃(자기 제외, ACTIVE만).

        기준 짤에 임베딩이 없으면 rank_score 인기순으로 폴백한다.
        """
        base_vec = self.db.execute(
            select(Embedding.embedding).where(Embedding.meme_id == meme_id)
        ).scalar_one_or_none()

        if base_vec is not None:
            distance = Embedding.embedding.cosine_distance(base_vec)
            stmt = (
                select(Meme)
                .join(Embedding, Embedding.meme_id == Meme.id)
                .where(Meme.status_cd == MemeStatus.ACTIVE, Meme.id != meme_id)
                .order_by(distance.asc())
                .limit(limit)
            )
            return list(self.db.execute(stmt).scalars().all())

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
