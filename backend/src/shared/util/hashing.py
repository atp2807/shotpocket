"""해시 유틸.

PII 비저장 원칙: 클라이언트 IP 는 절대 원문 저장하지 않고 sha256 해시로만 저장한다.
동일 IP 판별(중복/레이트리밋 로깅)에는 해시만으로 충분하다.
"""
from __future__ import annotations

import hashlib


def hash_ip(ip: str | None) -> str:
    """IP 문자열을 sha256 hex 로 변환. None/빈값은 'unknown' 처리."""
    raw = (ip or "unknown").strip()
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def hash_text(text: str) -> str:
    """임의 텍스트의 sha256 hex."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
