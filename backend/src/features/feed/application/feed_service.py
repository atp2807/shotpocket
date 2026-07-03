"""feed 애플리케이션 서비스 — 커서 인코딩/디코딩."""
from __future__ import annotations

import base64
import binascii
import uuid
from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from src.features.feed.infrastructure.feed_repo import FeedRepo
from src.infrastructure.db.models.meme import Meme
from src.shared.errors.error_codes import ErrorCode
from src.shared.errors.exceptions import BusinessError

DEFAULT_LIMIT = 10


class FeedService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = FeedRepo(db)

    @staticmethod
    def _encode_cursor(rank: Decimal, meme_id: uuid.UUID) -> str:
        raw = f"{rank}|{meme_id}".encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("ascii")

    @staticmethod
    def _decode_cursor(cursor: str) -> tuple[Decimal, uuid.UUID]:
        try:
            raw = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
            rank_str, id_str = raw.split("|", 1)
            return Decimal(rank_str), uuid.UUID(id_str)
        except (binascii.Error, ValueError, InvalidOperation, UnicodeDecodeError) as exc:
            raise BusinessError(ErrorCode.FEED_INVALID_CURSOR) from exc

    def list_feed(
        self, cursor: str | None = None, limit: int = DEFAULT_LIMIT
    ) -> tuple[list[Meme], str | None]:
        """피드 페이지 → (items, next_cursor). 커서 파싱 실패 시 FEED_001."""
        limit = max(min(limit, 50), 1)
        after_rank: Decimal | None = None
        after_id: uuid.UUID | None = None
        if cursor:
            after_rank, after_id = self._decode_cursor(cursor)

        rows = self.repo.list_feed(after_rank, after_id, limit)
        items = [meme for meme, _ in rows]

        next_cursor: str | None = None
        if len(rows) == limit:
            last_meme, last_rank = rows[-1]
            next_cursor = self._encode_cursor(last_rank, last_meme.id)
        return items, next_cursor
