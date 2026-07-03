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
        base = (settings.R2_PUBLIC_BASE_URL or "").rstrip("/")
        if base:
            return f"{base}/{key}"
        # 폴백: 계정 기반 r2.dev 형태(운영에선 커스텀 도메인 권장)
        return f"https://{settings.R2_BUCKET}.r2.dev/{key}"
    return f"/media/{key}"
