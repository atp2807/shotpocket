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

    def _publish_one(self, item) -> tuple[str, str | None]:
        """게시 1건. (meme_id, 생성한 미디어 디렉토리 경로) 반환(활성화·실패정리용)."""
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

        # 2) 미디어 저장 — meme PENDING 선생성 뒤에만 실행(orphan 방지 규약)
        pairs: list[tuple[str, str]] = [(f"{meme_id}/orig.{ext}", media["orig_path"])]
        if media.get("thumb_path"):
            pairs.append((f"{meme_id}/thumb.webp", media["thumb_path"]))
        if media.get("mp4_path"):
            pairs.append((f"{meme_id}/video.mp4", media["mp4_path"]))

        dest_dir: str | None = None
        if settings.STORAGE_MODE == "r2":
            # r2: 업로드 후 로컬 임시파일 제거. 실패 시 업로드분은 롤백 핸들러가 회수
            from src.infrastructure.r2.r2_client import r2_client

            self._uploaded_keys = []
            for key, path in pairs:
                r2_client.upload_file(key, path)
                self._uploaded_keys.append(key)
                os.remove(path)
        else:
            # local: MEDIA_ROOT/{meme_id}/ 로 이동
            dest_dir = os.path.join(settings.MEDIA_ROOT, str(meme_id))
            os.makedirs(dest_dir, exist_ok=True)
            self._current_dir = dest_dir  # 부분 이동 실패 시 정리 대상
            for key, path in pairs:
                shutil.move(path, os.path.join(settings.MEDIA_ROOT, key))

        meme.r2_orig_key = pairs[0][0]
        for key, _ in pairs[1:]:
            if key.endswith("thumb.webp"):
                meme.r2_thumb_key = key
            elif key.endswith("video.mp4"):
                meme.r2_mp4_key = key

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
                tags=analysis.get("tags") or [],
            )
        )
        if embedding:
            self.db.add(Embedding(meme_id=meme_id, embedding=embedding))

        # 4) 활성화 + meme_stat 초기 row
        # DEFER 모드(맥 야간 배치): 미디어가 서버로 rsync 되기 전 ACTIVE 되면
        # 피드에 깨진 이미지가 뜬다 → PENDING 유지, stat row 는 그대로 생성.
        # 오케스트레이터가 rsync 성공 후 이번 run 의 meme 만 일괄 ACTIVE 전이한다.
        if not settings.PUBLISH_DEFER_ACTIVATE:
            meme.status_cd = MemeStatus.ACTIVE
        self.db.add(MemeStat(meme_id=meme_id, rank_score=initial_rank_score()))

        # 5) raw_item PUBLISHED
        self.repo.set_status(item.id, PipelineState.PUBLISHED)
        return str(meme_id), dest_dir

    def run(self, limit: int = 100) -> list[str]:
        """게시 실행. 이번 run 에서 생성된 meme_id 문자열 목록을 반환한다.

        DEFER 모드에서 오케스트레이터가 이 목록으로 (rsync 후) 활성화 대상을
        특정한다. 반환 목록 길이가 곧 게시 건수다(len()).
        """
        items = self.repo.list_by_status(PipelineState.EMBEDDED, limit)
        meme_ids: list[str] = []
        for item in items:
            self._current_dir: str | None = None
            self._uploaded_keys: list[str] = []
            try:
                meme_id, self._current_dir = self._publish_one(item)
                self.db.commit()
                meme_ids.append(meme_id)
            except Exception:  # noqa: BLE001
                self.db.rollback()
                logger.warning("publish 실패 item=%s", item.id, exc_info=True)
                # 롤백으로 meme row 는 미확정. 이동·업로드된 미디어만 정리(고아 파일 방지)
                if self._current_dir and os.path.isdir(self._current_dir):
                    shutil.rmtree(self._current_dir, ignore_errors=True)
                if self._uploaded_keys:
                    from src.infrastructure.r2.r2_client import r2_client

                    for key in self._uploaded_keys:
                        try:
                            r2_client.delete_object(key)
                        except Exception:  # noqa: BLE001
                            logger.warning("r2 orphan 회수 실패 key=%s", key)
                # raw_item REJECTED (새 트랜잭션)
                self.repo.set_status(
                    item.id, PipelineState.REJECTED, RejectReason.FETCH_ERROR
                )
                self.db.commit()
        logger.info("publish published=%d", len(meme_ids))
        return meme_ids
