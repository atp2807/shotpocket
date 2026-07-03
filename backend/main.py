"""FastAPI 앱 팩토리 — ShotPocket API.

계정/로그인 없는 공개 짤 서비스. 운영 엔드포인트만 X-Ops-Key 로 보호.

미들웨어 등록 순서 규약:
  Starlette 는 '나중에 add 된 미들웨어가 바깥(=요청을 먼저 처리)'이다.
  즉 실행 순서는 등록의 '역순'. 아래는 지정된 add 순서이며, 그 결과
  요청 처리(바깥→안쪽) 실행 순서는 다음과 같다:

    [요청]  CORS → RequestID → SecurityHeaders → (HSTS, prod만)
            → NoCache(/api/ops만) → RateLimit → AccessLog → [라우트]

  add 순서(이 파일 아래 코드 순): AccessLog → RateLimit → NoCache → HSTS
            → SecurityHeaders → RequestID → CORS(마지막 add = 최선 실행).
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config.settings import settings
from src.presentation.middleware.access_log import AccessLogMiddleware
from src.presentation.middleware.error_handler import register_error_handlers
from src.presentation.middleware.request_id import RequestIDMiddleware
from src.presentation.routers import feed, memes, ops, reports, search
from src.shared.security.middleware.rate_limit import RateLimitMiddleware
from src.shared.security.middleware.security_headers import (
    HSTSMiddleware,
    NoCacheMiddleware,
    SecurityHeadersMiddleware,
)


def create_app() -> FastAPI:
    app = FastAPI(
        title="ShotPocket API",
        version="0.1.0",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url=None,
    )

    # --- 미들웨어 등록 (아래로 갈수록 나중 add = 더 바깥/먼저 실행) ---
    # 1) AccessLog  : 가장 안쪽(라우트 직전). 최종 상태코드/지연 관측.
    app.add_middleware(AccessLogMiddleware)
    # 2) RateLimit  : Redis INCR+TTL, IP당 분당 제한. 초과 429 COMMON_003.
    app.add_middleware(RateLimitMiddleware)
    # 3) NoCache    : /api/ops 응답만 no-store.
    app.add_middleware(NoCacheMiddleware, prefix="/api/ops")
    # 4) HSTS       : prod(=not DEBUG)에서만 등록.
    if not settings.DEBUG:
        app.add_middleware(HSTSMiddleware)
    # 5) SecurityHeaders : 정적 보안 헤더 상시 부착.
    app.add_middleware(SecurityHeadersMiddleware)
    # 6) RequestID  : 요청 상관ID 발급/전파.
    app.add_middleware(RequestIDMiddleware)
    # 7) CORS       : 마지막 add = 최선(최외곽) 실행.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 공개 읽기 API. 운영에서 도메인 화이트리스트로 축소.
        allow_credentials=False,  # 쿠키/세션 없음(계정 없는 서비스)
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    # 예외 핸들러: BusinessError → {error_code, message}, 그 외 → 500 COMMON_002
    register_error_handlers(app)

    # 라우터
    app.include_router(memes.router)
    app.include_router(search.router)
    app.include_router(feed.router)
    app.include_router(reports.router)
    app.include_router(ops.router)

    @app.get("/health", tags=["ops"])
    def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
