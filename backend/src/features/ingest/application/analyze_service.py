"""분석 서비스 — DEDUPED → ANALYZED.

VisionProvider(mock|anthropic)로 이미지를 분석해 결과를 raw_item.payload['analysis']
에 적재한다(게시 단계에서 meme.analysis 로 확정). NSFW 임계 초과면 REJECTED.
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from src.features.ingest.domain.pipeline_states import PipelineState, RejectReason
from src.features.ingest.infrastructure.raw_item_repo import RawItemRepo
from src.infrastructure.vision.vision_provider import get_vision_provider

logger = logging.getLogger("shotpocket.ingest.analyze")

_NSFW_THRESHOLD = 0.9


class AnalyzeService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = RawItemRepo(db)
        self.vision = get_vision_provider()

    def run(self, limit: int = 100) -> int:
        items = self.repo.list_by_status(PipelineState.DEDUPED, limit)
        processed = 0
        for item in items:
            payload = dict(item.payload or {})
            path = payload.get("file_path")
            if not path:
                self.repo.set_status(
                    item.id, PipelineState.REJECTED, RejectReason.FETCH_ERROR
                )
                processed += 1
                continue

            analysis = self.vision.analyze(path, payload.get("orig_filename", ""))
            if float(analysis.get("nsfw_score") or 0.0) >= _NSFW_THRESHOLD:
                self.repo.set_status(
                    item.id, PipelineState.REJECTED, RejectReason.NSFW
                )
                processed += 1
                continue

            payload["analysis"] = analysis
            self.repo.update_payload(item.id, payload)
            self.repo.set_status(item.id, PipelineState.ANALYZED)
            processed += 1
        self.db.commit()
        logger.info("analyze processed=%d", processed)
        return processed
