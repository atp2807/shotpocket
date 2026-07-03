"""트랜스코드 서비스 — ANALYZED → TRANSCODED.

- 애니메이션(프레임>1): media_type=LOOP. duration>3000ms 면 REJECTED('TOO_LONG').
  imageio-ffmpeg 정적 바이너리로 MP4 변환 + 첫 프레임 WebP 썸네일(최대 480px).
- 스틸: media_type=STILL. WebP 썸네일만.
산출 미디어 메타/경로는 raw_item.payload['media'] 에 적재(게시 단계에서 이동·확정).
"""
from __future__ import annotations

import logging
import os
import subprocess

from PIL import Image, ImageSequence
from sqlalchemy.orm import Session

from src.config.settings import settings
from src.features.ingest.domain.pipeline_states import PipelineState, RejectReason
from src.features.ingest.infrastructure.raw_item_repo import RawItemRepo
from src.features.meme.domain.entities import MediaType

logger = logging.getLogger("shotpocket.ingest.transcode")

_MAX_DURATION_MS = 3000
_THUMB_MAX = 480


class TranscodeService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = RawItemRepo(db)

    def _ffmpeg_exe(self) -> str:
        import imageio_ffmpeg  # 지연 import

        return imageio_ffmpeg.get_ffmpeg_exe()

    def _make_thumb(self, im: Image.Image, out_path: str) -> None:
        thumb = im.convert("RGB")
        thumb.thumbnail((_THUMB_MAX, _THUMB_MAX))
        thumb.save(out_path, format="WEBP", quality=85)

    def _to_mp4(self, src: str, out_path: str) -> None:
        # 짝수 해상도 강제(yuv420p 요구), faststart 로 웹 스트리밍 최적
        cmd = [
            self._ffmpeg_exe(),
            "-y",
            "-i",
            src,
            "-movflags",
            "faststart",
            "-pix_fmt",
            "yuv420p",
            "-vf",
            "scale=trunc(iw/2)*2:trunc(ih/2)*2",
            "-an",
            out_path,
        ]
        subprocess.run(cmd, check=True, capture_output=True)

    def run(self, limit: int = 100) -> int:
        items = self.repo.list_by_status(PipelineState.ANALYZED, limit)
        work_dir = settings.WORK_DIR
        os.makedirs(work_dir, exist_ok=True)
        processed = 0
        for item in items:
            payload = dict(item.payload or {})
            path = payload.get("file_path")
            if not path or not os.path.isfile(path):
                self.repo.set_status(
                    item.id, PipelineState.REJECTED, RejectReason.FETCH_ERROR
                )
                processed += 1
                continue

            try:
                with Image.open(path) as im:
                    width, height = im.size
                    n_frames = getattr(im, "n_frames", 1)
                    is_loop = n_frames > 1

                    duration_ms = None
                    if is_loop:
                        duration_ms = sum(
                            frame.info.get("duration", 100)
                            for frame in ImageSequence.Iterator(im)
                        )
                    first_frame = im.convert("RGB")

                thumb_path = os.path.join(work_dir, f"{item.id}.webp")
                self._make_thumb(first_frame, thumb_path)

                media = {
                    "width": width,
                    "height": height,
                    "orig_path": path,
                    "thumb_path": thumb_path,
                }

                if is_loop:
                    if duration_ms and duration_ms > _MAX_DURATION_MS:
                        self.repo.set_status(
                            item.id, PipelineState.REJECTED, RejectReason.TOO_LONG
                        )
                        processed += 1
                        continue
                    mp4_path = os.path.join(work_dir, f"{item.id}.mp4")
                    self._to_mp4(path, mp4_path)
                    media.update(
                        media_type_cd=MediaType.LOOP,
                        duration_ms=int(duration_ms or 0),
                        mp4_path=mp4_path,
                    )
                else:
                    media.update(
                        media_type_cd=MediaType.STILL,
                        duration_ms=None,
                        mp4_path=None,
                    )
            except Exception:  # noqa: BLE001
                logger.warning("transcode 실패 item=%s", item.id, exc_info=True)
                self.repo.set_status(
                    item.id, PipelineState.REJECTED, RejectReason.LOW_QUALITY
                )
                processed += 1
                continue

            payload["media"] = media
            self.repo.update_payload(item.id, payload)
            self.repo.set_status(item.id, PipelineState.TRANSCODED)
            processed += 1
        self.db.commit()
        logger.info("transcode processed=%d", processed)
        return processed
