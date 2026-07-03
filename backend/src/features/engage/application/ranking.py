"""랭크 스코어 계산 — (인기 가중합 + 신선도 기저) × 지수감쇠.

score = (ln(1 + like*3 + download*5 + view) + FRESH_BOOST) * exp(-경과일 / 14)
- 다운로드 가중 5, 좋아요 3, 조회 1. 14일 스케일 지수감쇠.
- FRESH_BOOST 를 감쇠 안쪽 기저항으로 두어 통계 0인 신규 짤도 0이 아닌
  스코어로 노출되고, rank_recalc 재계산에도 기저가 지워지지 않는다
  (기저를 publish 시 1회성 초기값으로만 주면 recalc 가 popularity=0 → 0
  으로 덮어써 초기 노출 보정이 소실된다 — 실측으로 확인된 회귀).
publish 시 초기값도 동일 식(age=0)으로 계산해 일관성을 유지한다.
"""
from __future__ import annotations

import math

DECAY_DAYS = 14.0
# 신규 게시물 신선도 기저(통계 0 이어도 노출 기회). 좋아요 수 개 수준.
FRESH_BOOST = 1.2


def rank_score(
    like_cnt: int, download_cnt: int, view_cnt: int, age_days: float
) -> float:
    popularity = math.log1p(
        max(like_cnt, 0) * 3 + max(download_cnt, 0) * 5 + max(view_cnt, 0)
    )
    freshness = math.exp(-max(age_days, 0.0) / DECAY_DAYS)
    return (popularity + FRESH_BOOST) * freshness


def initial_rank_score() -> float:
    """게시 직후 초기 rank_score — rank_score(0,0,0, age=0) = FRESH_BOOST."""
    return rank_score(0, 0, 0, 0.0)
