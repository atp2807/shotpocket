"""요청 ID 미들웨어.

요청마다 UUID 를 발급(또는 인바운드 X-Request-ID 승계)하여
request.state.request_id 로 노출하고 응답 헤더 X-Request-ID 에 실어준다.
access_log / error_handler 가 이 값을 참조해 상관관계를 남긴다.
"""
from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

REQUEST_ID_HEADER = "X-Request-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
