"""search 리포지토리 — 시맨틱(pgvector) + 키워드(ILIKE) 후보 조회 + query_log."""
from __future__ import annotations

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from src.features.meme.domain.entities import MemeStatus
from src.infrastructure.db.models.meme import Analysis, Embedding, Meme
from src.infrastructure.db.models.stat import MemeStat, QueryLog


class SearchRepo:
    def __init__(self, db: Session) -> None:
        self.db = db

    def semantic_ids(self, vec: list[float], limit: int) -> list[uuid.UUID]:
        """쿼리 임베딩 코사인 근접순 meme_id (ACTIVE + 임베딩 보유)."""
        distance = Embedding.embedding.cosine_distance(vec)
        stmt = (
            select(Meme.id)
            .join(Embedding, Embedding.meme_id == Meme.id)
            .where(Meme.status_cd == MemeStatus.ACTIVE)
            .order_by(distance.asc())
            .limit(limit)
        )
        return [row[0] for row in self.db.execute(stmt).all()]

    def keyword_ids(self, q: str, limit: int) -> list[uuid.UUID]:
        """caption/ocr_text/meme_name/tags ILIKE 매칭 meme_id (ACTIVE), rank_score 순.

        tags 는 태그 검색(F26 시리즈 모아보기 포함)의 핵심 신호라 배열 원소 부분
        일치(ANY)도 포함한다 — 정확일치보다 회복력 있는 매칭.
        """
        like = f"%{q}%"
        text_match = or_(
            Analysis.caption.ilike(like),
            Analysis.ocr_text.ilike(like),
            Analysis.meme_name.ilike(like),
            Analysis.tags.any(q),
            func.array_to_string(Analysis.tags, " ").ilike(like),
        )
        stmt = (
            select(Meme.id)
            .join(Analysis, Analysis.meme_id == Meme.id)
            .join(MemeStat, MemeStat.meme_id == Meme.id, isouter=True)
            .where(Meme.status_cd == MemeStatus.ACTIVE, text_match)
            .order_by(func.coalesce(MemeStat.rank_score, 0).desc())
            .limit(limit)
        )
        return [row[0] for row in self.db.execute(stmt).all()]

    def get_memes_by_ids(self, ids: list[uuid.UUID]) -> list[Meme]:
        """id 목록으로 Meme 조회 후 입력 순서(=랭킹 순서)로 정렬해 반환."""
        if not ids:
            return []
        stmt = select(Meme).where(Meme.id.in_(ids))
        by_id = {m.id: m for m in self.db.execute(stmt).scalars().all()}
        return [by_id[i] for i in ids if i in by_id]

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
