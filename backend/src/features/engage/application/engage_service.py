"""engage 애플리케이션 서비스 — 좋아요/다운로드/조회 집계.

계정이 없으므로 사용자 단위 dedup 은 불가. 동일 IP 의 시간창 내 중복은
Redis SETNX 키(engage:{action}:{meme_id}:{ip_hash}) 로 흡수한다.
- like/download: TTL 86400(1일). 중복이면 ENGAGE_001(409).
- view: TTL 3600(1시간). 뷰는 실패 개념이 없어 중복이어도 409 없이 200 으로
  현재 누적 view_cnt 를 그대로 반환한다(무증가).
Redis 미연결 시 dedup 생략(가용성 우선).

각 액션은 stat.meme_stat 누적 +1 과 stat.engage_hourly 시간버킷 +1 을 함께 반영한다.
"""
from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session

from src.features.engage.infrastructure.engage_repo import EngageRepo
from src.features.meme.infrastructure.meme_repo import MemeRepo
from src.infrastructure.redis.redis_client import get_redis
from src.shared.errors.error_codes import ErrorCode
from src.shared.errors.exceptions import BusinessError
from src.shared.util.media import media_url

logger = logging.getLogger("shotpocket.engage")

_DEDUP_TTL_SEC = 86400
_VIEW_TTL_SEC = 3600


class EngageService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = EngageRepo(db)
        self.meme_repo = MemeRepo(db)

    def _get_meme_or_404(self, meme_id: uuid.UUID):
        meme = self.meme_repo.get_active_by_id(meme_id)
        if meme is None:
            raise BusinessError(ErrorCode.MEME_NOT_FOUND)
        return meme

    def _claim(
        self, action: str, meme_id: uuid.UUID, ip_hash: str | None, ttl: int
    ) -> bool:
        """Redis SETNX 로 시간창 내 최초 액션인지 선점. 최초면 True, 중복이면 False.

        ip_hash 없음/Redis 미연결/오류 시엔 가용성 우선으로 True(집계)를 반환한다.
        """
        if ip_hash is None:
            return True
        client = get_redis()
        if client is None:
            return True
        key = f"engage:{action}:{meme_id}:{ip_hash}"
        try:
            ok = client.set(key, "1", nx=True, ex=ttl)
        except Exception:  # noqa: BLE001 — Redis 오류 시 가용성 우선(집계 진행)
            logger.warning("redis dedup 우회 action=%s meme=%s", action, meme_id)
            return True
        return bool(ok)

    def _guard_dup(self, action: str, meme_id: uuid.UUID, ip_hash: str | None) -> None:
        """like/download 중복 차단 — 중복이면 ENGAGE_001."""
        if not self._claim(action, meme_id, ip_hash, _DEDUP_TTL_SEC):
            raise BusinessError(ErrorCode.ENGAGE_DUPLICATE)

    def like(self, meme_id: uuid.UUID, ip_hash: str | None = None) -> int:
        """좋아요 +1 → 누적 like_cnt."""
        self._get_meme_or_404(meme_id)
        self._guard_dup("like", meme_id, ip_hash)
        like_cnt = self.repo.increment_like(meme_id)
        self.db.commit()
        return like_cnt

    def download(
        self, meme_id: uuid.UUID, ip_hash: str | None = None
    ) -> tuple[int, str | None]:
        """다운로드 +1 → (누적 download_cnt, 원본 다운로드 URL)."""
        meme = self._get_meme_or_404(meme_id)
        self._guard_dup("download", meme_id, ip_hash)
        download_cnt = self.repo.increment_download(meme_id)
        self.db.commit()
        return download_cnt, media_url(meme.r2_orig_key)

    def view(self, meme_id: uuid.UUID, ip_hash: str | None = None) -> int:
        """조회 +1 → 누적 view_cnt. 1시간 내 동일 IP 중복은 무증가(현재값 반환)."""
        self._get_meme_or_404(meme_id)
        if self._claim("view", meme_id, ip_hash, _VIEW_TTL_SEC):
            view_cnt = self.repo.increment_view(meme_id)
        else:
            view_cnt = self.repo.get_view_cnt(meme_id)
        self.db.commit()
        return view_cnt
