"""크롤 서비스 — enabled 소스 순회 → raw_item(FETCHED) 적재 (스텁)."""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.features.ingest.infrastructure.raw_item_repo import RawItemRepo
from src.features.ingest.infrastructure.source_adapters import get_adapter
from src.infrastructure.db.models.ingest import RawItem, Source

logger = logging.getLogger("shotpocket.ingest.crawl")

# 회당 소스별 글 수집 상한(설정 가능 — crawl(post_limit=...))
DEFAULT_POST_LIMIT = 30


class CrawlService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = RawItemRepo(db)

    def _origin_exists(self, origin_url: str | None) -> bool:
        """raw_item.origin_url 기존 존재 여부(글 단위 중복 스킵용). 빈 값은 미존재 취급."""
        if not origin_url:
            return False
        stmt = select(RawItem.id).where(RawItem.origin_url == origin_url).limit(1)
        return self.db.execute(stmt).first() is not None

    def crawl(self, post_limit: int = DEFAULT_POST_LIMIT) -> int:
        """활성 소스 크롤 → 신규 raw_item 수.

        각 어댑터에 글 상한(post_limit)과 origin_url 중복 스킵 콜백을 전달한다.
        어댑터 1개 실패가 전체 크롤을 죽이지 않도록 소스 단위로 격리한다.
        """
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
            try:
                cands = adapter.fetch(
                    source.base_url or "",
                    limit=post_limit,
                    is_seen=self._origin_exists,
                )
            except Exception as exc:  # noqa: BLE001 — 소스 1개 실패 격리
                logger.warning(
                    "source 크롤 실패 name=%s type=%s: %s",
                    source.name,
                    source.source_type_cd,
                    exc,
                )
                continue
            # 글 단위 중복(origin_url 기존)은 어댑터가 다운로드 전에 is_seen 으로 스킵한다.
            # 여기서 origin_url 재확인은 하지 않는다 — 한 글의 여러 이미지는 origin_url 이
            # 동일해, flush 후 재조회하면 2번째 이미지부터 오탈락하기 때문.
            for cand in cands:
                phash = cand.get("phash")
                if phash and self.repo.exists_phash(phash):
                    continue
                self.repo.create(
                    source_id=source.id,
                    origin_url=cand.get("origin_url") or "",
                    phash=phash,
                    payload=cand.get("payload"),
                )
                created += 1
            self.db.commit()
        logger.info("crawl done sources=%d created=%d", len(sources), created)
        return created
