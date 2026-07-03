"""애플리케이션 설정 — pydantic-settings.

.env 파일 + 환경변수에서 로드. 인증/세션 없음(계정 없는 서비스).
운영 접근은 OPS_API_KEY(Cloudflare Access 뒤단) 만 존재한다.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ 루트 (settings.py = backend/src/config/settings.py → parents[2])
BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 런타임
    DEBUG: bool = False
    PORT: int = 38090

    # 데이터스토어
    DATABASE_URL: str = "postgresql+psycopg2://shotpocket:shotpocket@db:5432/shotpocket"
    REDIS_URL: str = "redis://redis:6379/0"

    # 저장 방식: local(MEDIA_ROOT 파일) | r2(Cloudflare R2 public URL)
    STORAGE_MODE: str = "local"
    # 로컬 미디어 저장 루트 / 무인 수집 인박스 / 파이프라인 작업 디렉토리
    MEDIA_ROOT: str = str(BASE_DIR / "var" / "media")
    INBOX_DIR: str = str(BASE_DIR / "var" / "inbox")
    WORK_DIR: str = str(BASE_DIR / "var" / "work")

    # R2 (Cloudflare, S3 호환)
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET: str = "shotpocket"
    # r2 public 도메인 (STORAGE_MODE=r2 일 때 URL 빌더가 사용). 없으면 r2.dev 형태 폴백.
    R2_PUBLIC_BASE_URL: str = ""
    # 버킷 내 키 프리픽스(전용 버킷이면 빈 값). 쓰면 '/'로 끝나야 함
    R2_KEY_PREFIX: str = ""

    # 분석/임베딩 (프로덕션 RAM 1.8GB 제약 → 경량 ONNX 384차원)
    # e5-small은 fastembed registry 미지원 → MiniLM 다국어로 확정 (lr-333a4e1a)
    EMBEDDING_MODEL: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    EMBEDDING_DIM: int = 384
    # 임베딩 공급자: fastembed(EMBEDDING_MODEL, 384d) | mock(sha256 결정적)
    EMBEDDING_PROVIDER: str = "mock"
    # 비전 공급자: mock(Pillow 색상+파일명 규칙) | anthropic(API) | claude_cli(구독 OAuth, 맥 전용)
    VISION_PROVIDER: str = "mock"
    CLAUDE_CLI_MODEL: str = "sonnet"  # claude_cli 프로바이더용 (sonnet|haiku)
    VISION_MODE: str = "local"  # (구) 호환 필드 — 신규 코드는 VISION_PROVIDER 사용
    ANTHROPIC_API_KEY: str = ""

    # CORS 허용 오리진 (콤마 구분). 프로덕션: https://shotpocket.sitos.me
    ALLOWED_ORIGINS: str = "*"

    # 운영 API (X-Ops-Key 헤더로 검증. Cloudflare Access 뒤 배치 전제)
    OPS_API_KEY: str = "change-me-ops-key"

    # 레이트리밋
    RATE_LIMIT_PER_MIN: int = 120


@lru_cache
def get_settings() -> Settings:
    """설정 싱글턴. 프로세스 내 1회 로드."""
    return Settings()


settings = get_settings()
