"""트랜스코드 서비스 — ANALYZED → TRANSCODED.

- 애니메이션(프레임>1): media_type=LOOP. imageio-ffmpeg 정적 바이너리로 MP4 변환
  + 첫 프레임 WebP 썸네일(최대 480px).
- 스틸: media_type=STILL. WebP 썸네일만.

수집 허용 검사(초과 시 REJECTED, reject_reason_cd 기록 — 설계 dc-28f124be v1.3):
  - 스틸: 파일 ≤20MB · 장변 ≤4096px  (초과 TOO_LARGE)
  - GIF : 파일 ≤15MB (초과 TOO_LARGE) · 재생 ≤3초 (초과 TOO_LONG)
  - 공통: 장변/단변 비율 ≤3.0 (초과 WRONG_ASPECT) — "짤"은 화면 한 장 기준,
    웹툰 컷처럼 세로(또는 가로)로 여러 화면 이어진 이미지 배제. 참고: 틱톡 표준
    9:16≈1.78:1, 갤럭시폴드 커버화면 22:9≈2.44:1 — 둘 다 3:1 안쪽.
정규화(허용된 미디어의 서빙 상한):
  - 스틸 장변 >2048px → 2048 다운스케일(포맷·EXIF 방향 유지, JPEG quality 90)
  - GIF  장변 >720px  → ffmpeg scale + palettegen/paletteuse 로 720px GIF 재생성
  - MP4 변환본도 장변 720px 상한

산출 미디어 메타/경로는 raw_item.payload['media'] 에 적재(게시 단계에서 이동·확정).
"""
from __future__ import annotations

import logging
import os
import subprocess

from PIL import Image, ImageOps, ImageSequence
from sqlalchemy.orm import Session

from src.config.settings import settings
from src.features.ingest.domain.pipeline_states import PipelineState, RejectReason
from src.features.ingest.infrastructure.raw_item_repo import RawItemRepo
from src.features.meme.domain.entities import MediaType

logger = logging.getLogger("shotpocket.ingest.transcode")

_MAX_DURATION_MS = 3000
_THUMB_MAX = 480

# 수집 허용 상한
_STILL_MAX_BYTES = 20 * 1024 * 1024
_STILL_MAX_EDGE = 4096
_GIF_MAX_BYTES = 15 * 1024 * 1024
_MAX_ASPECT_RATIO = 3.0

# 정규화(서빙) 상한
_STILL_NORMALIZE_EDGE = 2048
_LOOP_MAX_EDGE = 720
_JPEG_QUALITY = 90

# PIL 포맷 → 파일 확장자(정규화 임시파일용)
_FMT_EXT = {"JPEG": "jpg", "MPO": "jpg", "PNG": "png", "WEBP": "webp", "GIF": "gif"}


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
        # 장변 720 상한(≤720 이면 무변형) + 짝수 해상도 강제(yuv420p 요구),
        # faststart 로 웹 스트리밍 최적.
        vf = (
            "scale='min(720,iw)':'min(720,ih)':force_original_aspect_ratio=decrease,"
            "scale=trunc(iw/2)*2:trunc(ih/2)*2"
        )
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
            vf,
            "-an",
            out_path,
        ]
        subprocess.run(cmd, check=True, capture_output=True)

    def _gif_to_720(self, src: str, out_path: str) -> tuple[int, int]:
        """GIF 를 장변 720px 로 재생성(palettegen/paletteuse) → 새 (w, h)."""
        scale = "scale='if(gt(iw,ih),720,-1)':'if(gt(iw,ih),-1,720)':flags=lanczos"
        vf = f"[0:v] {scale},split [a][b];[a] palettegen [p];[b][p] paletteuse"
        cmd = [self._ffmpeg_exe(), "-y", "-i", src, "-filter_complex", vf, out_path]
        subprocess.run(cmd, check=True, capture_output=True)
        with Image.open(out_path) as g:
            return g.size

    def _normalize_still(
        self, src: str, work_dir: str, item_id, img_format: str | None
    ) -> tuple[str, int, int]:
        """스틸 장변 2048 다운스케일(EXIF 방향 반영, 포맷 유지, JPEG q90) → (경로,w,h)."""
        with Image.open(src) as opened:
            im = ImageOps.exif_transpose(opened)  # EXIF 방향을 픽셀에 반영
        im.thumbnail((_STILL_NORMALIZE_EDGE, _STILL_NORMALIZE_EDGE))
        fmt = (img_format or "PNG").upper()
        ext = _FMT_EXT.get(fmt, "png")
        out_path = os.path.join(work_dir, f"{item_id}_norm.{ext}")
        save_fmt = fmt
        save_kwargs: dict = {}
        if fmt in ("JPEG", "MPO"):
            save_fmt = "JPEG"
            save_kwargs["quality"] = _JPEG_QUALITY
            im = im.convert("RGB")
        im.save(out_path, format=save_fmt, **save_kwargs)
        return out_path, im.width, im.height

    def run(
        self,
        limit: int = 100,
        *,
        include_source_types: set[str] | None = None,
        exclude_source_types: set[str] | None = None,
    ) -> int:
        items = self.repo.list_by_status(
            PipelineState.ANALYZED,
            limit,
            include_source_types=include_source_types,
            exclude_source_types=exclude_source_types,
        )
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
                file_size = os.path.getsize(path)
                with Image.open(path) as im:
                    img_format = im.format
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
                long_edge = max(width, height)
                short_edge = max(min(width, height), 1)

                # ---- 수집 허용 검사 (초과 REJECT) ----
                if long_edge / short_edge > _MAX_ASPECT_RATIO:
                    self.repo.set_status(
                        item.id, PipelineState.REJECTED, RejectReason.WRONG_ASPECT
                    )
                    processed += 1
                    continue
                if is_loop:
                    if file_size > _GIF_MAX_BYTES:
                        self.repo.set_status(
                            item.id, PipelineState.REJECTED, RejectReason.TOO_LARGE
                        )
                        processed += 1
                        continue
                    if duration_ms and duration_ms > _MAX_DURATION_MS:
                        self.repo.set_status(
                            item.id, PipelineState.REJECTED, RejectReason.TOO_LONG
                        )
                        processed += 1
                        continue
                elif file_size > _STILL_MAX_BYTES or long_edge > _STILL_MAX_EDGE:
                    self.repo.set_status(
                        item.id, PipelineState.REJECTED, RejectReason.TOO_LARGE
                    )
                    processed += 1
                    continue

                # ---- 썸네일 ----
                thumb_path = os.path.join(work_dir, f"{item.id}.webp")
                self._make_thumb(first_frame, thumb_path)

                media = {
                    "width": width,
                    "height": height,
                    "orig_path": path,
                    "thumb_path": thumb_path,
                }

                if is_loop:
                    # 정규화: 장변 >720 이면 720 GIF 재생성 후 그 파일을 원본으로
                    orig_path = path
                    if long_edge > _LOOP_MAX_EDGE:
                        gif_path = os.path.join(work_dir, f"{item.id}_720.gif")
                        gw, gh = self._gif_to_720(path, gif_path)
                        orig_path = gif_path
                        media.update(width=gw, height=gh, orig_path=gif_path)
                    mp4_path = os.path.join(work_dir, f"{item.id}.mp4")
                    self._to_mp4(orig_path, mp4_path)  # 변환본 장변 720 상한
                    media.update(
                        media_type_cd=MediaType.LOOP,
                        duration_ms=int(duration_ms or 0),
                        mp4_path=mp4_path,
                    )
                else:
                    # 정규화: 장변 >2048 이면 2048 다운스케일
                    if long_edge > _STILL_NORMALIZE_EDGE:
                        norm_path, nw, nh = self._normalize_still(
                            path, work_dir, item.id, img_format
                        )
                        media.update(width=nw, height=nh, orig_path=norm_path)
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
