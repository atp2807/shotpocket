"""engage 리포지토리 — meme_stat 누적 카운터 + stat.engage_hourly 시간버킷 집계."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from src.infrastructure.db.models.stat import EngageHourly, MemeStat

# action → (meme_stat 컬럼, engage_hourly 컬럼) 매핑
_ACTION_COL = {
    "view": "view_cnt",
    "like": "like_cnt",
    "download": "download_cnt",
}


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

    def _increment(self, meme_id: uuid.UUID, action: str) -> int:
        """meme_stat 해당 컬럼 +1 + engage_hourly UPSERT +1 → 누적값 반환."""
        col = _ACTION_COL[action]
        stat = self._get_or_create_stat(meme_id)
        new_val = (getattr(stat, col) or 0) + 1
        setattr(stat, col, new_val)
        self.db.flush()
        self.record_hourly(meme_id, action)
        return new_val

    def increment_like(self, meme_id: uuid.UUID) -> int:
        return self._increment(meme_id, "like")

    def increment_download(self, meme_id: uuid.UUID) -> int:
        return self._increment(meme_id, "download")

    def increment_view(self, meme_id: uuid.UUID) -> int:
        return self._increment(meme_id, "view")

    def get_view_cnt(self, meme_id: uuid.UUID) -> int:
        """현재 누적 view_cnt (stat 없으면 0). 뷰 중복(무증가) 응답용."""
        stmt = select(MemeStat.view_cnt).where(MemeStat.meme_id == meme_id)
        return int(self.db.execute(stmt).scalar_one_or_none() or 0)

    def record_hourly(self, meme_id: uuid.UUID, action: str) -> None:
        """stat.engage_hourly (meme_id, date_trunc('hour', now())) 버킷 +1 UPSERT."""
        col = _ACTION_COL[action]
        hour_ts = func.date_trunc("hour", func.now())
        values = {
            "meme_id": meme_id,
            "hour_ts": hour_ts,
            "view_cnt": 0,
            "like_cnt": 0,
            "download_cnt": 0,
            col: 1,
        }
        stmt = pg_insert(EngageHourly).values(**values)
        target = EngageHourly.__table__.c[col]
        stmt = stmt.on_conflict_do_update(
            index_elements=[EngageHourly.meme_id, EngageHourly.hour_ts],
            set_={col: target + 1},
        )
        self.db.execute(stmt)
        self.db.flush()

    def cleanup_hourly(self, older_than_days: int = 7) -> int:
        """hour_ts 가 지정 일수보다 오래된 engage_hourly row 삭제 → 삭제 건수."""
        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=older_than_days)
        result = self.db.execute(
            delete(EngageHourly).where(EngageHourly.hour_ts < cutoff)
        )
        self.db.commit()
        return int(result.rowcount or 0)
