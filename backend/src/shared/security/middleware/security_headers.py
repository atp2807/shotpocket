"""보안 헤더 미들웨어.

- SecurityHeadersMiddleware: 상시 보안 헤더(X-Content-Type-Options 등).
- HSTSMiddleware: prod 에서만 Strict-Transport-Security 부착.
- NoCacheMiddleware: /api/ops 경로에만 no-store 부착(운영 응답 캐시 방지).
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """정적 보안 헤더 부착."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("X-XSS-Protection", "0")
        return response


class HSTSMiddleware(BaseHTTPMiddleware):
    """prod 전용 HSTS. main.py 에서 prod 일 때만 등록한다."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault(
            "Strict-Transport-Security",
            "max-age=31536000; includeSubDomains",
        )
        return response


class NoCacheMiddleware(BaseHTTPMiddleware):
    """지정 prefix(기본 /api/ops) 응답에 캐시 금지 헤더 부착."""

    def __init__(self, app, prefix: str = "/api/ops") -> None:
        super().__init__(app)
        self.prefix = prefix

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith(self.prefix):
            response.headers["Cache-Control"] = "no-store, max-age=0"
            response.headers["Pragma"] = "no-cache"
        return response
