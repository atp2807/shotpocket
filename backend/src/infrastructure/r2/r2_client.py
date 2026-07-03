"""R2(Cloudflare) 클라이언트 — boto3 S3 호환 스텁.

orphan(고아 객체) 방지 순서 규약:
  1) DB 에 레코드를 status=PENDING 으로 먼저 생성(키 예약).
  2) R2 에 업로드.
  3) 성공 시 DB status=CONFIRMED 로 전이.
업로드 실패로 2)에서 끊겨도 DB 는 PENDING 으로 남아 orphan_cleanup 잡이
일정 시간 경과한 PENDING(+대응 객체 없음)을 회수한다. 역순(업로드 먼저)이면
DB 미기록 객체가 새어나가 회수 불가 → 반드시 이 순서를 지킬 것.
"""
from __future__ import annotations

import logging

import boto3
from botocore.config import Config

from src.config.settings import settings

logger = logging.getLogger("shotpocket.r2")


class R2Client:
    """S3 호환 R2 래퍼(스텁). 실제 전송 로직은 파이프라인 연동 시 구현."""

    def __init__(self) -> None:
        self._bucket = settings.R2_BUCKET
        self._client = None  # lazy — 자격증명 없는 개발환경에서 import 시 실패 방지

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

    def upload_bytes(self, key: str, data: bytes, content_type: str) -> str:
        """바이트 업로드 → object key 반환. (스텁: 로그만)"""
        # 호출 전제: DB 레코드가 PENDING 으로 선생성되어 있어야 한다(orphan 방지).
        logger.info("r2 upload key=%s bytes=%d type=%s", key, len(data), content_type)
        # self._ensure_client().put_object(Bucket=self._bucket, Key=key, Body=data,
        #                                  ContentType=content_type)
        return key

    def delete_object(self, key: str) -> None:
        """객체 삭제(orphan_cleanup 회수용). (스텁: 로그만)"""
        logger.info("r2 delete key=%s", key)
        # self._ensure_client().delete_object(Bucket=self._bucket, Key=key)

    def public_url(self, key: str) -> str:
        """공개 CDN URL 조합(스텁)."""
        return f"https://cdn.shotpocket.example/{key}"


r2_client = R2Client()
