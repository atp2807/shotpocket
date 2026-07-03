"""search 애플리케이션 서비스."""
from __future__ import annotations

from sqlalchemy.orm import Session

from src.features.search.infrastructure.search_repo import SearchRepo
from src.infrastructure.db.models.meme import Meme
from src.shared.errors.error_codes import ErrorCode
from src.shared.errors.exceptions import BusinessError

DEFAULT_PAGE_SIZE = 20


class SearchService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = SearchRepo(db)

    def search(
        self,
        q: str,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
        ip_hash: str | None = None,
    ) -> tuple[list[Meme], int, int, int]:
        """검색 실행 → (items, total, page, page_size). 검색어 비면 SEARCH_001."""
        query_text = (q or "").strip()
        if not query_text:
            raise BusinessError(ErrorCode.SEARCH_EMPTY_QUERY)

        page = max(page, 1)
        page_size = max(min(page_size, 100), 1)

        try:
            items, total = self.repo.search(query_text, page, page_size)
        except Exception as exc:  # noqa: BLE001 - 검색 실패는 도메인 에러로 승격
            self.repo.save_query_log(query_text, 0, failed_yn=True, ip_hash=ip_hash)
            self.db.commit()
            raise BusinessError(ErrorCode.SEARCH_FAILED) from exc

        self.repo.save_query_log(query_text, total, failed_yn=False, ip_hash=ip_hash)
        self.db.commit()
        return items, total, page, page_size
