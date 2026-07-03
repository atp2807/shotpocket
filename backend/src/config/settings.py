"""애플리케이션 설정 — pydantic-settings.

.env 파일 + 환경변수에서 로드. 인증/세션 없음(계정 없는 서비스).
운영 접근은 OPS_API_KEY(Cloudflare Access 뒤단) 만 존재한다.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # R2 (Cloudflare, S3 호환)
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET: str = "shotpocket"

    # 분석/임베딩
    EMBEDDING_MODEL: str = "bge-m3"
    EMBEDDING_DIM: int = 1024
    VISION_MODE: str = "local"

    # 운영 API (X-Ops-Key 헤더로 검증. Cloudflare Access 뒤 배치 전제)
    OPS_API_KEY: str = "change-me-ops-key"

    # 레이트리밋
    RATE_LIMIT_PER_MIN: int = 120


@lru_cache
def get_settings() -> Settings:
    """설정 싱글턴. 프로세스 내 1회 로드."""
    return Settings()


settings = get_settings()
