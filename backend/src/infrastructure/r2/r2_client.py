"""R2(Cloudflare) 클라이언트 — boto3 S3 호환.

공유 버킷(모하더스 계정)을 쓰므로 모든 객체는 R2_KEY_PREFIX(shotpocket/) 아래에만
생성한다. DB 의 r2_*_key 컬럼에는 프리픽스 없는 상대 key('{meme_id}/orig.png')만
저장하고, 업로드/삭제/URL 조합 시 이 클라이언트가 프리픽스를 붙인다 — 버킷/폴더
이전 시 DB 재작성이 필요 없도록.

orphan(고아 객체) 방지 순서 규약:
  1) DB 에 레코드를 status=PENDING 으로 먼저 생성(키 예약).
  2) R2 에 업로드.
  3) 성공 시 DB status=CONFIRMED(ACTIVE) 로 전이.
업로드 실패로 2)에서 끊겨도 DB 는 PENDING 으로 남아 orphan_cleanup 잡이
일정 시간 경과한 PENDING(+대응 객체 없음)을 회수한다. 역순(업로드 먼저)이면
DB 미기록 객체가 새어나가 회수 불가 → 반드시 이 순서를 지킬 것.
"""
from __future__ import annotations

import logging
import mimetypes

import boto3
from botocore.config import Config

from src.config.settings import settings

logger = logging.getLogger("shotpocket.r2")

_CONTENT_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".mp4": "video/mp4",
}


def guess_content_type(key: str) -> str:
    for ext, ct in _CONTENT_TYPES.items():
        if key.lower().endswith(ext):
            return ct
    return mimetypes.guess_type(key)[0] or "application/octet-stream"


class R2Client:
    """S3 호환 R2 래퍼. 프리픽스 스코핑 + lazy 클라이언트."""

    def __init__(self) -> None:
        self._client = None  # lazy — 자격증명 없는 개발환경에서 import 시 실패 방지

    @property
    def _bucket(self) -> str:
        return settings.R2_BUCKET

    @staticmethod
    def _full_key(key: str) -> str:
        prefix = settings.R2_KEY_PREFIX
        if prefix and not prefix.endswith("/"):
            prefix += "/"
        return f"{prefix}{key.lstrip('/')}"

    def _ensure_client(self):
        if self._client is None:
            endpoint = f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
            self._client = boto3.client(
                "s3",
                endpoint_url=endpoint,
                aws_access_key_id=settings.R2_ACCESS_KEY_ID,
                aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
                config=Config(signature_version="s3v4"),
                region_name="auto",
            )
        return self._client

    def upload_bytes(self, key: str, data: bytes, content_type: str | None = None) -> str:
        """바이트 업로드 → 상대 key 반환. DB PENDING 선생성 후 호출할 것(orphan 방지)."""
        full = self._full_key(key)
        self._ensure_client().put_object(
            Bucket=self._bucket,
            Key=full,
            Body=data,
            ContentType=content_type or guess_content_type(key),
        )
        logger.info("r2 upload key=%s bytes=%d", full, len(data))
        return key

    def upload_file(self, key: str, path: str, content_type: str | None = None) -> str:
        with open(path, "rb") as f:
            return self.upload_bytes(key, f.read(), content_type)

    def object_exists(self, key: str) -> bool:
        try:
            self._ensure_client().head_object(Bucket=self._bucket, Key=self._full_key(key))
            return True
        except Exception:  # noqa: BLE001 — 404 포함
            return False

    def delete_object(self, key: str) -> None:
        """객체 삭제(orphan_cleanup 회수/게시 실패 정리용)."""
        full = self._full_key(key)
        self._ensure_client().delete_object(Bucket=self._bucket, Key=full)
        logger.info("r2 delete key=%s", full)

    def public_url(self, key: str) -> str:
        """공개 URL 조합 (R2_PUBLIC_BASE_URL + 프리픽스 + 상대 key)."""
        base = (settings.R2_PUBLIC_BASE_URL or "").rstrip("/")
        if not base:
            base = f"https://{self._bucket}.r2.dev"
        return f"{base}/{self._full_key(key)}"


r2_client = R2Client()
