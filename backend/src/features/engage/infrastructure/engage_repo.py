"""engage 리포지토리 — meme_stat 카운터 upsert."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.infrastructure.db.models.stat import MemeStat


class EngageRepo:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _get_or_create_stat(self, meme_id: uuid.UUID) -> MemeStat:
        stmt = select(MemeStat).where(MemeStat.meme_id == meme_id)
        stat = self.db.execute(stmt).scalar_one_or_none()
        if stat is None:
            stat = MemeStat(meme_id=meme_id, view_cnt=0, like_cnt=0, download_cnt=0)
            self.db.add(stat)
            self.db.flush()
        return stat

    def increment_like(self, meme_id: uuid.UUID) -> int:
        stat = self._get_or_create_stat(meme_id)
        stat.like_cnt = (stat.like_cnt or 0) + 1
        self.db.flush()
        return stat.like_cnt

    def increment_download(self, meme_id: uuid.UUID) -> int:
        stat = self._get_or_create_stat(meme_id)
        stat.download_cnt = (stat.download_cnt or 0) + 1
        self.db.flush()
        return stat.download_cnt
