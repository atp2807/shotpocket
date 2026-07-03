"""트랜스코드 서비스 — ANALYZED → TRANSCODED (ffmpeg 스텁).

LOOP(루프 움짤) 원본 → 웹 최적 mp4 + 썸네일 생성 후 R2 업로드 예정.
STILL(스틸컷)은 트랜스코드 없이 썸네일만 생성한다.
R2 업로드는 orphan 방지 규약(PENDING 선생성→업로드→CONFIRMED)을 따른다.
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from src.features.ingest.domain.pipeline_states import PipelineState
from src.features.ingest.infrastructure.raw_item_repo import RawItemRepo

logger = logging.getLogger("shotpocket.ingest.transcode")


class TranscodeService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = RawItemRepo(db)

    def run(self, limit: int = 100) -> int:
        items = self.repo.list_by_status(PipelineState.ANALYZED, limit)
        processed = 0
        for item in items:
            # ffmpeg 트랜스코드 + 썸네일 → R2 업로드(스텁)
            logger.debug("transcode item=%s", item.id)
            self.repo.set_status(item.id, PipelineState.TRANSCODED)
            processed += 1
        self.db.commit()
        logger.info("transcode processed=%d", processed)
        return processed
