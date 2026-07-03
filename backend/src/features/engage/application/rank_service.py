"""랭크 재계산 서비스 — 인기·신선도 기반 rank_score 갱신.

scheduler rank_recalc 잡 및 수동 파이프라인에서 호출. ACTIVE 짤의 통계·경과일로
rank_score 를 다시 계산해 stat.meme_stat 에 반영한다.
"""
from __future__ import annotations

import datetime as dt
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.features.engage.application.ranking import rank_score
from src.features.meme.domain.entities import MemeStatus
from src.infrastructure.db.models.meme import Meme
from src.infrastructure.db.models.stat import MemeStat

logger = logging.getLogger("shotpocket.rank")


class RankService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def recalc(self) -> int:
        now = dt.datetime.now(dt.timezone.utc)
        rows = self.db.execute(
            select(MemeStat, Meme.created_ts)
            .join(Meme, Meme.id == MemeStat.meme_id)
            .where(Meme.status_cd == MemeStatus.ACTIVE)
        ).all()
        updated = 0
        for stat, created_ts in rows:
            age_days = max((now - created_ts).total_seconds() / 86400.0, 0.0)
            stat.rank_score = rank_score(
                stat.like_cnt or 0, stat.download_cnt or 0, stat.view_cnt or 0, age_days
            )
            updated += 1
        self.db.commit()
        logger.info("rank_recalc updated=%d", updated)
        return updated
