"""feed 리포지토리 — 커서(keyset) 페이지네이션 + 섹션별 정렬.

섹션(sort):
  - recommended: rank_score(신선도+인기 감쇠) 내림차순. 무한 스와이프 기본.
  - today      : 최근 24h engage_hourly 가중합(like×3+download×5+view) 내림차순.
  - rising     : 최근 2h 반응합 ÷ GREATEST(직전 24h 시간당 평균, 1) 가속도.
                 created_ts 24h 이내 신규는 ×1.5 부스트.
  - new        : created_ts 내림차순.

모든 섹션이 (score, id) keyset 로 통일된다(new 는 score=created_ts epoch).
OFFSET 대신 keyset 을 쓰는 이유: 무한 세로 스와이프에서 새 항목 유입에도
중복/누락 없이 다음 페이지를 안정적으로 얻기 위함. today/rising 은 상위
_SECTION_CAP(200)개까지만 페이지네이션한다(그 뒤 next_cursor=null).
"""
from __future__ import annotations

import datetime as dt
import uuid
from decimal import Decimal

from sqlalchemy import Numeric, and_, case, cast, func, select, tuple_
from sqlalchemy.orm import Session

from src.features.meme.domain.entities import MemeStatus
from src.infrastructure.db.models.meme import Meme
from src.infrastructure.db.models.stat import EngageHourly, MemeStat

# today/rising 은 상위 N개까지만 페이지네이션(그 뒤 next_cursor=null)
_SECTION_CAP = 200
# 반응 가중치: like×3 + download×5 + view
_W_LIKE, _W_DOWNLOAD, _W_VIEW = 3, 5, 1
# score 를 고정 정밀 numeric 으로 캐스팅 — 커서(Decimal) 왕복 시 부동소수 오차 방지
_SCORE_NUM = Numeric(20, 6)


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _weight_col():
    """engage_hourly row 단위 가중 반응값 표현식."""
    return (
        EngageHourly.like_cnt * _W_LIKE
        + EngageHourly.download_cnt * _W_DOWNLOAD
        + EngageHourly.view_cnt * _W_VIEW
    )


class FeedRepo:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ---- recommended: rank_score keyset (기존 동작 유지) ----
    def list_feed(
        self,
        after_rank: Decimal | None,
        after_id: uuid.UUID | None,
        limit: int,
    ) -> list[tuple[Meme, Decimal]]:
        rank = func.coalesce(MemeStat.rank_score, 0)
        stmt = (
            select(Meme, rank.label("score"))
            .join(MemeStat, MemeStat.meme_id == Meme.id, isouter=True)
            .where(Meme.status_cd == MemeStatus.ACTIVE)
        )
        if after_rank is not None and after_id is not None:
            stmt = stmt.where(tuple_(rank, Meme.id) < tuple_(after_rank, after_id))
        stmt = stmt.order_by(rank.desc(), Meme.id.desc()).limit(limit)
        rows = self.db.execute(stmt).all()
        return [(row[0], Decimal(str(row[1]))) for row in rows]

    # ---- today: 최근 24h 가중합 ----
    def list_today(self, after_score, after_id, limit):
        since = _utcnow() - dt.timedelta(hours=24)
        weighted = (
            func.sum(EngageHourly.like_cnt) * _W_LIKE
            + func.sum(EngageHourly.download_cnt) * _W_DOWNLOAD
            + func.sum(EngageHourly.view_cnt) * _W_VIEW
        )
        scored = (
            select(
                EngageHourly.meme_id.label("meme_id"),
                cast(weighted, _SCORE_NUM).label("score"),
            )
            .where(EngageHourly.hour_ts >= since)
            .group_by(EngageHourly.meme_id)
            .subquery()
        )
        return self._paginate(scored, after_score, after_id, limit, _SECTION_CAP)

    # ---- rising: 최근 2h 가속도 + 신규 부스트 ----
    def list_rising(self, after_score, after_id, limit):
        now = _utcnow()
        recent_since = now - dt.timedelta(hours=2)
        base_since = now - dt.timedelta(hours=26)  # 직전 24h(= now-26h ~ now-2h)
        fresh_since = now - dt.timedelta(hours=24)
        w = _weight_col()
        recent = func.coalesce(
            func.sum(w).filter(EngageHourly.hour_ts >= recent_since), 0
        )
        base = func.coalesce(
            func.sum(w).filter(
                and_(
                    EngageHourly.hour_ts >= base_since,
                    EngageHourly.hour_ts < recent_since,
                )
            ),
            0,
        )
        # 직전 24h 시간당 평균 = base/24, 최소 1 → 가속도 = recent / 평균
        avg_per_hour = func.greatest(cast(base, _SCORE_NUM) / 24.0, 1.0)
        accel = cast(recent, _SCORE_NUM) / avg_per_hour
        boost = case((Meme.created_ts >= fresh_since, 1.5), else_=1.0)
        scored = (
            select(
                Meme.id.label("meme_id"),
                cast(accel * boost, _SCORE_NUM).label("score"),
            )
            .join(EngageHourly, EngageHourly.meme_id == Meme.id)
            .where(
                Meme.status_cd == MemeStatus.ACTIVE,
                EngageHourly.hour_ts >= base_since,
            )
            .group_by(Meme.id, Meme.created_ts)
            # 최근 2h 반응이 있는 짤만 '지금 뜨는'
            .having(func.sum(w).filter(EngageHourly.hour_ts >= recent_since) > 0)
            .subquery()
        )
        return self._paginate(scored, after_score, after_id, limit, _SECTION_CAP)

    # ---- new: created_ts 내림차순 ----
    def list_new(self, after_score, after_id, limit):
        score = cast(func.extract("epoch", Meme.created_ts), _SCORE_NUM)
        scored = (
            select(Meme.id.label("meme_id"), score.label("score"))
            .where(Meme.status_cd == MemeStatus.ACTIVE)
            .subquery()
        )
        return self._paginate(scored, after_score, after_id, limit, cap=None)

    # ---- 공통 keyset 페이지네이터 ----
    def _paginate(
        self, scored, after_score, after_id, limit: int, cap: int | None
    ) -> list[tuple[Meme, Decimal]]:
        if cap is not None:
            scored = (
                select(scored.c.meme_id, scored.c.score)
                .order_by(scored.c.score.desc(), scored.c.meme_id.desc())
                .limit(cap)
                .subquery()
            )
        stmt = (
            select(Meme, scored.c.score)
            .join(scored, scored.c.meme_id == Meme.id)
            .where(Meme.status_cd == MemeStatus.ACTIVE)
        )
        if after_score is not None and after_id is not None:
            stmt = stmt.where(
                tuple_(scored.c.score, Meme.id) < tuple_(after_score, after_id)
            )
        stmt = stmt.order_by(scored.c.score.desc(), Meme.id.desc()).limit(limit)
        rows = self.db.execute(stmt).all()
        return [(row[0], Decimal(str(row[1]))) for row in rows]
