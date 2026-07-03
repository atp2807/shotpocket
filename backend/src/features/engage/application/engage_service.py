"""engage 애플리케이션 서비스 — 좋아요/다운로드 집계.

계정이 없으므로 사용자 단위 dedup 은 불가. 짧은 시간창 내 동일 IP 중복은
Redis SETNX 키(engage:{kind}:{meme}:{ip_hash}) TTL 로 흡수하는 스텁 훅을 둔다.
중복이면 ENGAGE_001(409). Redis 미연결 시 dedup 생략(가용성 우선).
"""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from src.features.engage.infrastructure.engage_repo import EngageRepo
from src.features.meme.infrastructure.meme_repo import MemeRepo
from src.shared.errors.error_codes import ErrorCode
from src.shared.errors.exceptions import BusinessError

_DEDUP_TTL_SEC = 5


class EngageService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = EngageRepo(db)
        self.meme_repo = MemeRepo(db)

    def _assert_meme(self, meme_id: uuid.UUID) -> None:
        if self.meme_repo.get_active_by_id(meme_id) is None:
            raise BusinessError(ErrorCode.MEME_NOT_FOUND)

    def _check_dup(self, kind: str, meme_id: uuid.UUID, ip_hash: str | None) -> None:
        """스텁: Redis SETNX 기반 단시간 중복 차단 훅. 미연결 시 pass."""
        if ip_hash is None:
            return
        # key = f"engage:{kind}:{meme_id}:{ip_hash}"
        # if redis and not redis.set(key, 1, nx=True, ex=_DEDUP_TTL_SEC):
        #     raise BusinessError(ErrorCode.ENGAGE_DUPLICATE)
        _ = _DEDUP_TTL_SEC

    def like(self, meme_id: uuid.UUID, ip_hash: str | None = None) -> int:
        """좋아요 +1 → 누적 like_cnt."""
        self._assert_meme(meme_id)
        self._check_dup("like", meme_id, ip_hash)
        like_cnt = self.repo.increment_like(meme_id)
        self.db.commit()
        return like_cnt

    def download(self, meme_id: uuid.UUID, ip_hash: str | None = None) -> int:
        """다운로드 +1 → 누적 download_cnt."""
        self._assert_meme(meme_id)
        self._check_dup("download", meme_id, ip_hash)
        download_cnt = self.repo.increment_download(meme_id)
        self.db.commit()
        return download_cnt
