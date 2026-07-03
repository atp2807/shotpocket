"""meme 애플리케이션 서비스."""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from src.features.meme.infrastructure.meme_repo import MemeRepo
from src.infrastructure.db.models.meme import Meme
from src.shared.errors.error_codes import ErrorCode
from src.shared.errors.exceptions import BusinessError


class MemeService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = MemeRepo(db)

    def get_meme(self, meme_id: uuid.UUID) -> Meme:
        """단건 조회. 없거나 비공개면 MEME_NOT_FOUND."""
        meme = self.repo.get_active_by_id(meme_id)
        if meme is None:
            raise BusinessError(ErrorCode.MEME_NOT_FOUND)
        return meme

    def list_similar(self, meme_id: uuid.UUID, limit: int = 20) -> list[Meme]:
        """유사 짤 목록. 기준 짤 존재 검증 후 반환."""
        if self.repo.get_active_by_id(meme_id) is None:
            raise BusinessError(ErrorCode.MEME_NOT_FOUND)
        return self.repo.list_similar(meme_id, limit)
