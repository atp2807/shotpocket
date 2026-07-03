"""게시 서비스 — EMBEDDED → PUBLISHED, meme 레코드 생성 (스텁).

파이프라인 최종 단계. raw_item 을 공개 meme(status=ACTIVE)으로 승격하고
meme_stat 초기 행을 만든다. 무인 자동 게시.
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from src.features.ingest.domain.pipeline_states import PipelineState
from src.features.ingest.infrastructure.raw_item_repo import RawItemRepo

logger = logging.getLogger("shotpocket.ingest.publish")


class PublishService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = RawItemRepo(db)

    def run(self, limit: int = 100) -> int:
        items = self.repo.list_by_status(PipelineState.EMBEDDED, limit)
        processed = 0
        for item in items:
            # meme(ACTIVE) + analysis + embedding + meme_stat 생성(스텁)
            logger.debug("publish item=%s", item.id)
            self.repo.set_status(item.id, PipelineState.PUBLISHED)
            processed += 1
        self.db.commit()
        logger.info("publish processed=%d", processed)
        return processed
