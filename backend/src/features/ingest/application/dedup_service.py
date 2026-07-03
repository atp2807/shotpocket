"""중복제거 서비스 — FETCHED → DEDUPED / REJECTED(DUPLICATE) (스텁).

phash 해밍거리 기반 근접중복 판정. 스텁에서는 완전일치만 검사한다.
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from src.features.ingest.domain.pipeline_states import PipelineState, RejectReason
from src.features.ingest.infrastructure.raw_item_repo import RawItemRepo

logger = logging.getLogger("shotpocket.ingest.dedup")


class DedupService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = RawItemRepo(db)

    def run(self, limit: int = 100) -> int:
        items = self.repo.list_by_status(PipelineState.FETCHED, limit)
        seen: set[str] = set()
        processed = 0
        for item in items:
            if item.phash and item.phash in seen:
                # 근접중복 판정은 imagehash 해밍거리로 교체(스텁: 정확일치만)
                self.repo.set_status(
                    item.id, PipelineState.REJECTED, RejectReason.DUPLICATE
                )
            else:
                if item.phash:
                    seen.add(item.phash)
                self.repo.set_status(item.id, PipelineState.DEDUPED)
            processed += 1
        self.db.commit()
        logger.info("dedup processed=%d", processed)
        return processed
