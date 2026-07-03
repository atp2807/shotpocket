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
_MEME_SCORE_THRESHOLD = 0.4


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

            # 밈 판별: vision 이 밈 아님으로 판정하면 게시하지 않는다.
            # (파일럿 실측: 힛갤·유머베스트 크롤분의 ~절반이 여행·취미 등 일반 사진)
            if analysis.get("is_meme") is False or (
                analysis.get("meme_score") is not None
                and float(analysis["meme_score"]) < _MEME_SCORE_THRESHOLD
            ):
                self.repo.set_status(
                    item.id, PipelineState.REJECTED, RejectReason.NOT_MEME
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
