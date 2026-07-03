"""소스 어댑터 레지스트리 — 크롤 대상별 fetch 인터페이스.

각 어댑터는 fetch() -> list[dict] (origin_url/phash/payload 후보) 를 반환한다.
source.source_type_cd 로 어댑터를 선택한다.

- LocalFolderAdapter(LOCAL): 무인 로컬 인박스 수집. INBOX_DIR 스캔 → 파일을
  WORK_DIR 로 이동하고 후보를 반환(재스캔 시 중복 픽업 방지).
- DcinsideAdapter(DCINSIDE): 디시인사이드 힛갤 실크롤(dcinside.py).
- RuliwebAdapter(RULIWEB): 루리웹 유머 베스트 실크롤(ruliweb.py).
- WebSourceAdapter(WEB): 일반 웹 페이지 크롤 어댑터 자리(TODO).

fetch(base_url, *, limit, is_seen) — limit=회당 글 상한, is_seen(origin_url)->bool 은
글 단위 중복 스킵(DB 조회) 콜백. 실크롤 어댑터가 사용하며, 로컬/스텁 어댑터는 무시한다.
"""
from __future__ import annotations

import logging
import os
import shutil
import uuid
from typing import Callable, Protocol

from src.config.settings import settings
from src.features.ingest.infrastructure.source_adapters.dcinside import DcinsideAdapter
from src.features.ingest.infrastructure.source_adapters.ruliweb import RuliwebAdapter

logger = logging.getLogger("shotpocket.ingest.adapter")

_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


class SourceAdapter(Protocol):
    source_type_cd: str

    def fetch(
        self,
        base_url: str,
        *,
        limit: int = 30,
        is_seen: Callable[[str], bool] | None = None,
    ) -> list[dict]:
        """소스에서 후보 아이템 목록을 수집.

        limit: 회당 글 수집 상한. is_seen: origin_url 기존 존재 여부 콜백(중복 스킵).
        로컬/스텁 어댑터는 두 인자를 무시한다.
        """
        ...


class LocalFolderAdapter:
    """로컬 인박스 폴더 수집 어댑터.

    base_url 이 폴더 경로면 그 경로를, 비어있으면 settings.INBOX_DIR 를 스캔한다.
    수집한 파일은 WORK_DIR 로 이동해 payload 에 작업경로/원본파일명을 남긴다.
    """

    source_type_cd = "LOCAL"

    def fetch(
        self,
        base_url: str,
        *,
        limit: int = 30,
        is_seen: Callable[[str], bool] | None = None,
    ) -> list[dict]:
        inbox = base_url or settings.INBOX_DIR
        work_dir = settings.WORK_DIR
        if not os.path.isdir(inbox):
            logger.info("local inbox 없음: %s", inbox)
            return []
        os.makedirs(work_dir, exist_ok=True)

        candidates: list[dict] = []
        for name in sorted(os.listdir(inbox)):
            src_path = os.path.join(inbox, name)
            if not os.path.isfile(src_path):
                continue
            ext = os.path.splitext(name)[1].lower()
            if ext not in _IMAGE_EXTS:
                continue
            work_path = os.path.join(work_dir, f"{uuid.uuid4().hex}{ext}")
            shutil.move(src_path, work_path)
            candidates.append(
                {
                    "origin_url": None,
                    "phash": None,  # phash 는 dedup 단계에서 계산
                    "payload": {
                        "file_path": work_path,
                        "orig_filename": name,
                        "ext": ext.lstrip("."),
                        "src_cd": self.source_type_cd,
                    },
                }
            )
        logger.info("local inbox 수집 %d건 (%s)", len(candidates), inbox)
        return candidates


class WebSourceAdapter:
    """일반 웹 페이지 크롤 어댑터(미구현 스텁 — TODO: httpx 크롤)."""

    source_type_cd = "WEB"

    def fetch(
        self,
        base_url: str,
        *,
        limit: int = 30,
        is_seen: Callable[[str], bool] | None = None,
    ) -> list[dict]:
        return []


# source_type_cd → 어댑터 인스턴스
ADAPTER_REGISTRY: dict[str, SourceAdapter] = {
    LocalFolderAdapter.source_type_cd: LocalFolderAdapter(),
    DcinsideAdapter.source_type_cd: DcinsideAdapter(),
    RuliwebAdapter.source_type_cd: RuliwebAdapter(),
    WebSourceAdapter.source_type_cd: WebSourceAdapter(),
}


def get_adapter(source_type_cd: str) -> SourceAdapter | None:
    return ADAPTER_REGISTRY.get(source_type_cd)
