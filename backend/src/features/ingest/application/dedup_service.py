"""중복제거 서비스 — FETCHED → DEDUPED / REJECTED(DUPLICATE).

imagehash pHash(64bit) 를 계산해 raw_item.phash 에 기록하고, 기존 게시 meme
및 선행 raw_item 들과 해밍거리 ≤ HAMMING_THRESHOLD 이면 근접중복으로 REJECTED.
"""
from __future__ import annotations

import logging

import imagehash
from PIL import Image
from sqlalchemy.orm import Session

from src.features.ingest.domain.pipeline_states import PipelineState, RejectReason
from src.features.ingest.infrastructure.raw_item_repo import RawItemRepo

logger = logging.getLogger("shotpocket.ingest.dedup")

HAMMING_THRESHOLD = 4


def _hamming(a: str, b: str) -> int:
    """두 64bit hex pHash 의 해밍거리."""
    try:
        return bin(int(a, 16) ^ int(b, 16)).count("1")
    except ValueError:
        return 64


class DedupService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = RawItemRepo(db)

    def _compute_phash(self, item) -> str | None:
        payload = item.payload or {}
        path = payload.get("file_path")
        if not path:
            return None
        try:
            with Image.open(path) as im:
                return str(imagehash.phash(im.convert("RGB")))
        except Exception:  # noqa: BLE001
            logger.warning("phash 계산 실패 item=%s path=%s", item.id, path)
            return None

    def run(
        self,
        limit: int = 100,
        *,
        include_source_types: set[str] | None = None,
        exclude_source_types: set[str] | None = None,
    ) -> int:
        items = self.repo.list_by_status(
            PipelineState.FETCHED,
            limit,
            include_source_types=include_source_types,
            exclude_source_types=exclude_source_types,
        )
        # 기존 게시 meme + 선행 수용 raw_item 의 phash 를 근접중복 기준으로 로드
        known: list[str] = [
            p for p in (self.repo.meme_phashes() + self.repo.accepted_phashes()) if p
        ]
        processed = 0
        for item in items:
            phash = self._compute_phash(item)
            if phash is None:
                self.repo.set_status(
                    item.id, PipelineState.REJECTED, RejectReason.FETCH_ERROR
                )
                processed += 1
                continue

            self.repo.set_phash(item.id, phash)
            dup = any(_hamming(phash, k) <= HAMMING_THRESHOLD for k in known)
            if dup:
                self.repo.set_status(
                    item.id, PipelineState.REJECTED, RejectReason.DUPLICATE
                )
            else:
                known.append(phash)  # 같은 배치 내 후속 중복도 차단
                self.repo.set_status(item.id, PipelineState.DEDUPED)
            processed += 1
        self.db.commit()
        logger.info("dedup processed=%d", processed)
        return processed
