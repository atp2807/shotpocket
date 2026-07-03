"""게시 서비스 — EMBEDDED → PUBLISHED (orphan 방지 순서).

순서(반드시 준수):
  1) meme.meme 를 PENDING 으로 선생성(키/식별자 확보)
  2) 미디어 파일을 MEDIA_ROOT/{meme_id}/ 로 이동·저장하고 r2_*_key 기록
  3) meme.analysis / meme.embedding 확정 생성
  4) status ACTIVE 전이 + stat.meme_stat 초기 row(신선도 보정 rank_score)
  5) raw_item PUBLISHED
실패 시: 트랜잭션 롤백(→ meme row 미확정) + 이동된 미디어 디렉토리 정리 + raw_item REJECTED.
"""
from __future__ import annotations

import logging
import os
import shutil

from sqlalchemy.orm import Session

from src.features.engage.application.ranking import initial_rank_score
from src.features.ingest.domain.pipeline_states import PipelineState, RejectReason
from src.features.ingest.infrastructure.raw_item_repo import RawItemRepo
from src.features.meme.domain.entities import MediaType, MemeStatus
from src.infrastructure.db.models.meme import Analysis, Embedding, Meme
from src.infrastructure.db.models.stat import MemeStat
from src.config.settings import settings

logger = logging.getLogger("shotpocket.ingest.publish")


class PublishService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = RawItemRepo(db)

    def _publish_one(self, item) -> str:
        """게시 1건. 생성한 미디어 디렉토리 경로를 반환(실패 정리용)."""
        payload = dict(item.payload or {})
        media = payload.get("media") or {}
        analysis = payload.get("analysis") or {}
        embedding = payload.get("embedding")
        ext = payload.get("ext", "png")

        # 1) meme PENDING 선생성
        meme = Meme(
            phash=item.phash,
            media_type_cd=media.get("media_type_cd", MediaType.STILL),
            duration_ms=media.get("duration_ms"),
            width=media.get("width"),
            height=media.get("height"),
            origin_url=item.origin_url,
            source_cd=payload.get("src_cd"),
            status_cd=MemeStatus.PENDING,
        )
        self.db.add(meme)
        self.db.flush()  # meme.id 확보
        meme_id = meme.id

        # 2) 미디어 파일 이동 → MEDIA_ROOT/{meme_id}/
        dest_dir = os.path.join(settings.MEDIA_ROOT, str(meme_id))
        os.makedirs(dest_dir, exist_ok=True)
        self._current_dir = dest_dir  # 부분 이동 실패 시 정리 대상

        orig_key = f"{meme_id}/orig.{ext}"
        shutil.move(media["orig_path"], os.path.join(settings.MEDIA_ROOT, orig_key))
        meme.r2_orig_key = orig_key

        if media.get("thumb_path"):
            thumb_key = f"{meme_id}/thumb.webp"
            shutil.move(
                media["thumb_path"], os.path.join(settings.MEDIA_ROOT, thumb_key)
            )
            meme.r2_thumb_key = thumb_key

        if media.get("mp4_path"):
            mp4_key = f"{meme_id}/video.mp4"
            shutil.move(media["mp4_path"], os.path.join(settings.MEDIA_ROOT, mp4_key))
            meme.r2_mp4_key = mp4_key

        # 3) analysis / embedding 확정
        self.db.add(
            Analysis(
                meme_id=meme_id,
                caption=analysis.get("caption"),
                situation=analysis.get("situation"),
                emotion_cd=analysis.get("emotion_cd"),
                ocr_text=analysis.get("ocr_text"),
                usage_context=analysis.get("usage_context"),
                character_name=analysis.get("character_name"),
                meme_name=analysis.get("meme_name"),
                lang_cd=analysis.get("lang_cd"),
                nsfw_score=analysis.get("nsfw_score"),
                confidence=analysis.get("confidence"),
                model_cd=analysis.get("model_cd"),
            )
        )
        if embedding:
            self.db.add(Embedding(meme_id=meme_id, embedding=embedding))

        # 4) ACTIVE + meme_stat 초기 row
        meme.status_cd = MemeStatus.ACTIVE
        self.db.add(MemeStat(meme_id=meme_id, rank_score=initial_rank_score()))

        # 5) raw_item PUBLISHED
        self.repo.set_status(item.id, PipelineState.PUBLISHED)
        return dest_dir

    def run(self, limit: int = 100) -> int:
        items = self.repo.list_by_status(PipelineState.EMBEDDED, limit)
        published = 0
        for item in items:
            self._current_dir: str | None = None
            try:
                self._current_dir = self._publish_one(item)
                self.db.commit()
                published += 1
            except Exception:  # noqa: BLE001
                self.db.rollback()
                logger.warning("publish 실패 item=%s", item.id, exc_info=True)
                # 롤백으로 meme row 는 미확정. 이동된 미디어 디렉토리만 정리(고아 파일 방지)
                if self._current_dir and os.path.isdir(self._current_dir):
                    shutil.rmtree(self._current_dir, ignore_errors=True)
                # raw_item REJECTED (새 트랜잭션)
                self.repo.set_status(
                    item.id, PipelineState.REJECTED, RejectReason.FETCH_ERROR
                )
                self.db.commit()
        logger.info("publish published=%d", published)
        return published
