"""레이트리밋 미들웨어 — Redis INCR + TTL, IP 당 분당 N회.

키: rl:{ip_hash}:{epoch_minute} — INCR 후 첫 요청에 TTL 60s 설정.
Redis 미연결/오류 시 pass-through(서비스 가용성 우선).
초과 시 429 {error_code: COMMON_003}.
"""
from __future__ import annotations

import time

import redis
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.config.settings import settings
from src.shared.errors.error_codes import ErrorCode
from src.shared.util.hashing import hash_ip


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limit_per_min: int | None = None) -> None:
        super().__init__(app)
        self.limit = limit_per_min or settings.RATE_LIMIT_PER_MIN
        try:
            self._redis = redis.Redis.from_url(settings.REDIS_URL, socket_timeout=0.2)
        except Exception:
            self._redis = None

    def _client_ip(self, request: Request) -> str:
        # Cloudflare 뒤단: 원본 IP 는 CF-Connecting-IP → X-Forwarded-For 순으로 신뢰
        fwd = request.headers.get("cf-connecting-ip") or request.headers.get("x-forwarded-for")
        if fwd:
            return fwd.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next):
        if self._redis is None:
            return await call_next(request)

        ip_hash = hash_ip(self._client_ip(request))
        bucket = int(time.time() // 60)
        key = f"rl:{ip_hash}:{bucket}"
        try:
            count = self._redis.incr(key)
            if count == 1:
                self._redis.expire(key, 60)
        except Exception:
            # Redis 미연결/오류 → pass-through
            return await call_next(request)

        if count > self.limit:
            ec = ErrorCode.COMMON_003
            return JSONResponse(
                status_code=ec.status,
                content={"error_code": ec.code, "message": ec.message},
            )
        return await call_next(request)
