"""분석 서비스 — DEDUPED → ANALYZED (비전/캡션 스텁).

VISION_MODE(local/remote)에 따라 캡션·감정·OCR·NSFW 를 산출해 meme.analysis 에
적재할 예정. 스텁은 상태 전이만 수행한다.
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from src.config.settings import settings
from src.features.ingest.domain.pipeline_states import PipelineState, RejectReason
from src.features.ingest.infrastructure.raw_item_repo import RawItemRepo

logger = logging.getLogger("shotpocket.ingest.analyze")

_NSFW_THRESHOLD = 0.9


class AnalyzeService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = RawItemRepo(db)

    def run(self, limit: int = 100) -> int:
        items = self.repo.list_by_status(PipelineState.DEDUPED, limit)
        processed = 0
        for item in items:
            # vision 분석(VISION_MODE=%s) → caption/emotion/ocr/nsfw 산출 예정
            logger.debug("analyze item=%s mode=%s", item.id, settings.VISION_MODE)
            nsfw_score = 0.0  # 스텁
            if nsfw_score >= _NSFW_THRESHOLD:
                self.repo.set_status(item.id, PipelineState.REJECTED, RejectReason.NSFW)
            else:
                self.repo.set_status(item.id, PipelineState.ANALYZED)
            processed += 1
        self.db.commit()
        logger.info("analyze processed=%d", processed)
        return processed
