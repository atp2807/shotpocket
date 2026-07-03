"""액세스 로그 미들웨어 — 버퍼 배치 스텁.

정책:
- GET 성공(2xx) 응답은 스킵(피드/조회 트래픽이 대부분이라 노이즈 제거).
- 그 외(쓰기·에러)는 버퍼에 적재 후 5초 또는 100건 단위로 flush.
스텁: flush 는 표준 로거로 배출. 운영에선 배치 인서트/외부 싱크로 교체.
"""
from __future__ import annotations

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("shotpocket.access")

_FLUSH_INTERVAL_SEC = 5.0
_FLUSH_MAX = 100


class AccessLogMiddleware(BaseHTTPMiddleware):
    def __init__(self, app) -> None:
        super().__init__(app)
        self._buffer: list[dict] = []
        self._last_flush = time.monotonic()

    def _maybe_flush(self, force: bool = False) -> None:
        now = time.monotonic()
        due = (now - self._last_flush) >= _FLUSH_INTERVAL_SEC
        if force or due or len(self._buffer) >= _FLUSH_MAX:
            for entry in self._buffer:
                logger.info("access %s", entry)
            self._buffer.clear()
            self._last_flush = now

    async def dispatch(self, request: Request, call_next):
        start = time.monotonic()
        response = await call_next(request)
        elapsed_ms = int((time.monotonic() - start) * 1000)

        # GET 성공은 스킵
        if request.method == "GET" and 200 <= response.status_code < 300:
            return response

        self._buffer.append(
            {
                "request_id": getattr(request.state, "request_id", None),
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "elapsed_ms": elapsed_ms,
            }
        )
        self._maybe_flush()
        return response
