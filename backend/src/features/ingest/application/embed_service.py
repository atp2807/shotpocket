"""임베딩 서비스 — TRANSCODED → EMBEDDED.

analysis 텍스트(caption+situation+usage_context+ocr_text+tags)를 결합 임베딩해
raw_item.payload['embedding'] 에 적재(게시 단계에서 meme.embedding 로 확정).
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from src.features.ingest.domain.pipeline_states import PipelineState
from src.features.ingest.infrastructure.raw_item_repo import RawItemRepo
from src.infrastructure.embedding.embedder import get_embedder

logger = logging.getLogger("shotpocket.ingest.embed")


def build_embed_text(analysis: dict) -> str:
    parts = [
        analysis.get("caption"),
        analysis.get("situation"),
        analysis.get("usage_context"),
        analysis.get("ocr_text"),
        " ".join(analysis.get("tags") or []),
    ]
    return " ".join(p for p in parts if p).strip()


class EmbedService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = RawItemRepo(db)
        self.embedder = get_embedder()

    def run(
        self,
        limit: int = 100,
        *,
        include_source_types: set[str] | None = None,
        exclude_source_types: set[str] | None = None,
    ) -> int:
        items = self.repo.list_by_status(
            PipelineState.TRANSCODED,
            limit,
            include_source_types=include_source_types,
            exclude_source_types=exclude_source_types,
        )
        processed = 0
        for item in items:
            payload = dict(item.payload or {})
            analysis = payload.get("analysis") or {}
            text = build_embed_text(analysis) or (payload.get("orig_filename") or "")
            vector = self.embedder.embed_passage(text)
            payload["embedding"] = vector
            self.repo.update_payload(item.id, payload)
            self.repo.set_status(item.id, PipelineState.EMBEDDED)
            processed += 1
        self.db.commit()
        logger.info("embed processed=%d", processed)
        return processed
