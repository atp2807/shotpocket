"""크롤 서비스 — enabled 소스 순회 → raw_item(FETCHED) 적재 (스텁)."""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.features.ingest.infrastructure.raw_item_repo import RawItemRepo
from src.features.ingest.infrastructure.source_adapters import get_adapter
from src.infrastructure.db.models.ingest import Source

logger = logging.getLogger("shotpocket.ingest.crawl")


class CrawlService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = RawItemRepo(db)

    def crawl(self) -> int:
        """활성 소스 크롤 → 신규 raw_item 수. (스텁: 어댑터가 빈 목록 반환)"""
        stmt = (
            select(Source)
            .where(Source.enabled_yn.is_(True))
            .order_by(Source.priority.asc())
        )
        sources = list(self.db.execute(stmt).scalars().all())
        created = 0
        for source in sources:
            adapter = get_adapter(source.source_type_cd)
            if adapter is None:
                logger.warning("no adapter for source_type=%s", source.source_type_cd)
                continue
            for cand in adapter.fetch(source.base_url or ""):
                phash = cand.get("phash")
                if phash and self.repo.exists_phash(phash):
                    continue
                self.repo.create(
                    source_id=source.id,
                    origin_url=cand.get("origin_url", ""),
                    phash=phash,
                    payload=cand.get("payload"),
                )
                created += 1
        self.db.commit()
        logger.info("crawl done sources=%d created=%d", len(sources), created)
        return created
