"""임베딩 서비스 — TRANSCODED → EMBEDDED (embedder 스텁).

analysis 텍스트(caption/usage_context 등)를 bge-m3 로 임베딩(1024d)해
meme.embedding 에 적재할 예정. 스텁은 상태 전이만 수행한다.
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from src.features.ingest.domain.pipeline_states import PipelineState
from src.features.ingest.infrastructure.raw_item_repo import RawItemRepo
from src.infrastructure.embedding.embedder import embedder

logger = logging.getLogger("shotpocket.ingest.embed")


class EmbedService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = RawItemRepo(db)
        self.embedder = embedder

    def run(self, limit: int = 100) -> int:
        items = self.repo.list_by_status(PipelineState.TRANSCODED, limit)
        processed = 0
        for item in items:
            # vector = self.embedder.embed_text(<analysis text>) → meme.embedding upsert
            logger.debug("embed item=%s model=%s", item.id, self.embedder.model_cd)
            self.repo.set_status(item.id, PipelineState.EMBEDDED)
            processed += 1
        self.db.commit()
        logger.info("embed processed=%d", processed)
        return processed
