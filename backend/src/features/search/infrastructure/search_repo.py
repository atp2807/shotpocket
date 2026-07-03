"""search 리포지토리 — SQLAlchemy 쿼리 + query_log 적재."""
from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from src.features.meme.domain.entities import MemeStatus
from src.infrastructure.db.models.meme import Analysis, Meme
from src.infrastructure.db.models.stat import MemeStat, QueryLog


class SearchRepo:
    def __init__(self, db: Session) -> None:
        self.db = db

    def search(self, q: str, page: int, page_size: int) -> tuple[list[Meme], int]:
        """의미 검색.

        placeholder: 임베딩 스텁이라 벡터 검색 대신 analysis 텍스트 ILIKE +
        rank_score 정렬 폴백. 실제 임베딩 연결 후엔 query 임베딩과
        embedding.cosine_distance 정렬로 교체한다.
        """
        like = f"%{q}%"
        text_match = or_(
            Analysis.caption.ilike(like),
            Analysis.ocr_text.ilike(like),
            Analysis.meme_name.ilike(like),
            Analysis.character_name.ilike(like),
            Analysis.usage_context.ilike(like),
        )
        base = (
            select(Meme)
            .join(Analysis, Analysis.meme_id == Meme.id)
            .join(MemeStat, MemeStat.meme_id == Meme.id, isouter=True)
            .where(Meme.status_cd == MemeStatus.ACTIVE, text_match)
        )

        count_stmt = select(func.count()).select_from(base.subquery())
        total = int(self.db.execute(count_stmt).scalar_one())

        stmt = (
            base.order_by(MemeStat.rank_score.desc().nullslast())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = list(self.db.execute(stmt).scalars().all())
        return items, total

    def save_query_log(
        self, query_text: str, result_cnt: int, failed_yn: bool, ip_hash: str | None
    ) -> None:
        self.db.add(
            QueryLog(
                query_text=query_text,
                result_cnt=result_cnt,
                failed_yn=failed_yn,
                ip_hash=ip_hash,
            )
        )
        self.db.flush()
