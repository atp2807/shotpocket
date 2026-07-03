"""Redis 클라이언트 싱글톤 — 인게이지 중복차단(SETNX) 등에 사용.

미연결/오류 시 None 을 반환하여 호출부가 '가용성 우선'으로 우회할 수 있게 한다.
"""
from __future__ import annotations

import logging

import redis

from src.config.settings import settings

logger = logging.getLogger("shotpocket.redis")

_client: redis.Redis | None = None
_initialized = False


def get_redis() -> redis.Redis | None:
    """공유 Redis 클라이언트. 초기화 실패 시 None."""
    global _client, _initialized
    if not _initialized:
        _initialized = True
        try:
            _client = redis.Redis.from_url(
                settings.REDIS_URL, socket_timeout=0.3, socket_connect_timeout=0.3
            )
        except Exception:  # noqa: BLE001
            logger.warning("redis 초기화 실패 — 중복차단 우회")
            _client = None
    return _client
