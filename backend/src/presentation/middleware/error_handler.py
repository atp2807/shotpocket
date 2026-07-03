"""에러 핸들러 등록.

- BusinessError → 해당 status + {error_code, message}.
- 그 외 미처리 예외 → 500 COMMON_002 (내부 정보 노출 금지, 로그에만 상세 기록).
FastAPI exception_handler 로 등록한다(미들웨어 아님).
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.shared.errors.error_codes import ErrorCode
from src.shared.errors.exceptions import BusinessError

logger = logging.getLogger("shotpocket.error")


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(BusinessError)
    async def _business_error_handler(request: Request, exc: BusinessError) -> JSONResponse:
        ec = exc.error_code
        return JSONResponse(
            status_code=ec.status,
            content={"error_code": ec.code, "message": exc.message},
        )

    @app.exception_handler(Exception)
    async def _unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        # 내부 정보 노출 금지: 상세는 로그에만, 응답은 일반화된 COMMON_002
        rid = getattr(request.state, "request_id", None)
        logger.exception("unhandled error request_id=%s path=%s", rid, request.url.path)
        ec = ErrorCode.COMMON_002
        return JSONResponse(
            status_code=ec.status,
            content={"error_code": ec.code, "message": ec.message},
        )
