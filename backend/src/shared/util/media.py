"""미디어 URL 빌더 — 저장키(key) → 공개 URL.

STORAGE_MODE:
  local : /media/{key}  (main.py StaticFiles 마운트가 MEDIA_ROOT 를 서빙)
  r2    : R2 public URL (R2_PUBLIC_BASE_URL 또는 r2_client.public_url)
r2_*_key 컬럼에는 항상 '{meme_id}/orig.png' 같은 상대 key 만 저장한다.
"""
from __future__ import annotations

from src.config.settings import settings


def media_url(key: str | None) -> str | None:
    """저장 key → 클라이언트가 접근 가능한 URL. key 없으면 None."""
    if not key:
        return None
    if settings.STORAGE_MODE == "r2":
        # 프리픽스(shotpocket/) 포함 공개 URL — r2_client 가 단일 소스
        from src.infrastructure.r2.r2_client import r2_client

        return r2_client.public_url(key)
    return f"/media/{key}"
