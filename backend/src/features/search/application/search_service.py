"""search 애플리케이션 서비스 — 시맨틱+키워드 RRF 융합."""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from src.features.search.infrastructure.search_repo import SearchRepo
from src.infrastructure.db.models.meme import Meme
from src.infrastructure.embedding.embedder import get_embedder
from src.shared.errors.error_codes import ErrorCode
from src.shared.errors.exceptions import BusinessError

DEFAULT_PAGE_SIZE = 20
# 각 후보 리스트에서 가져올 상한(RRF 융합 풀)
CANDIDATE_LIMIT = 200
# RRF 상수 (표준값 60): 상위 랭크 가중을 완만하게.
RRF_K = 60


def _rrf_fuse(*ranked_lists: list[uuid.UUID]) -> list[uuid.UUID]:
    """Reciprocal Rank Fusion. score(id) = Σ 1/(k + rank).

    rank 는 각 리스트에서 1-based 순위. 여러 리스트에 등장할수록 상단.
    동점은 최초 등장(먼저 삽입) 순서로 안정 정렬.
    """
    scores: dict[uuid.UUID, float] = {}
    order: dict[uuid.UUID, int] = {}
    seq = 0
    for ranked in ranked_lists:
        for rank, mid in enumerate(ranked, start=1):
            scores[mid] = scores.get(mid, 0.0) + 1.0 / (RRF_K + rank)
            if mid not in order:
                order[mid] = seq
                seq += 1
    return sorted(scores, key=lambda m: (-scores[m], order[m]))


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
            vec = get_embedder().embed_query(query_text)
            semantic = self.repo.semantic_ids(vec, CANDIDATE_LIMIT)
            keyword = self.repo.keyword_ids(query_text, CANDIDATE_LIMIT)
            fused = _rrf_fuse(semantic, keyword)

            total = len(fused)
            start = (page - 1) * page_size
            page_ids = fused[start : start + page_size]
            items = self.repo.get_memes_by_ids(page_ids)
        except Exception as exc:  # noqa: BLE001 — 검색 실패는 도메인 에러로 승격
            self.repo.save_query_log(query_text, 0, failed_yn=True, ip_hash=ip_hash)
            self.db.commit()
            raise BusinessError(ErrorCode.SEARCH_FAILED) from exc

        self.repo.save_query_log(
            query_text, total, failed_yn=(total == 0), ip_hash=ip_hash
        )
        self.db.commit()
        return items, total, page, page_size
