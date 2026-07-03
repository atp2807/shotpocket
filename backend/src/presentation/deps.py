"""presentation 공용 의존성."""
from __future__ import annotations

from fastapi import Request

from src.shared.util.hashing import hash_ip


def get_ip_hash(request: Request) -> str:
    """요청 클라이언트 IP 의 sha256 해시(PII 비저장). Cloudflare 헤더 우선."""
    fwd = request.headers.get("cf-connecting-ip") or request.headers.get("x-forwarded-for")
    ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else None)
    return hash_ip(ip)
