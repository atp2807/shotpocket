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
DEFAULT_SORT = "recommended"
# 지원 섹션. 미지원 값은 기본(recommended)으로 폴백한다.
SORTS = ("recommended", "today", "rising", "new")


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
        self,
        cursor: str | None = None,
        limit: int = DEFAULT_LIMIT,
        sort: str = DEFAULT_SORT,
    ) -> tuple[list[Meme], str | None]:
        """피드 페이지 → (items, next_cursor). 커서 파싱 실패 시 FEED_001.

        sort 로 섹션을 선택한다(미지원 값은 recommended 로 폴백). 전 섹션 ACTIVE만,
        (score, id) keyset 커서를 공유한다(new 는 score=created_ts epoch).
        """
        if sort not in SORTS:
            sort = DEFAULT_SORT
        limit = max(min(limit, 50), 1)
        after_score: Decimal | None = None
        after_id: uuid.UUID | None = None
        if cursor:
            after_score, after_id = self._decode_cursor(cursor)

        section = {
            "recommended": self.repo.list_feed,
            "today": self.repo.list_today,
            "rising": self.repo.list_rising,
            "new": self.repo.list_new,
        }[sort]
        rows = section(after_score, after_id, limit)
        items = [meme for meme, _ in rows]

        next_cursor: str | None = None
        if len(rows) == limit:
            last_meme, last_score = rows[-1]
            next_cursor = self._encode_cursor(last_score, last_meme.id)
        return items, next_cursor
