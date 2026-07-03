"""소스 어댑터 레지스트리 — 크롤 대상별 fetch 인터페이스(스텁).

각 어댑터는 fetch() -> list[dict] (origin_url/phash/payload 후보) 를 반환한다.
source.source_type_cd 로 어댑터를 선택한다. 실제 구현(httpx 크롤링)은 추후.
"""
from __future__ import annotations

from typing import Protocol


class SourceAdapter(Protocol):
    source_type_cd: str

    def fetch(self, base_url: str) -> list[dict]:
        """소스에서 후보 아이템 목록을 수집."""
        ...


class WebSourceAdapter:
    """일반 웹 페이지 크롤 어댑터(스텁)."""

    source_type_cd = "WEB"

    def fetch(self, base_url: str) -> list[dict]:
        # httpx 로 목록 페이지 요청 → 이미지/영상 후보 파싱 (미구현 스텁)
        return []


# source_type_cd → 어댑터 인스턴스
ADAPTER_REGISTRY: dict[str, SourceAdapter] = {
    WebSourceAdapter.source_type_cd: WebSourceAdapter(),
}


def get_adapter(source_type_cd: str) -> SourceAdapter | None:
    return ADAPTER_REGISTRY.get(source_type_cd)
