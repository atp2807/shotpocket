"""ingest.source 시드 — 실크롤 소스 2건(디시 힛갤 / 루리웹 유머베스트) 등록.

멱등: 같은 source_type_cd 가 있으면 건너뛴다.
실행: `python -m scripts.seed_sources`
"""
from __future__ import annotations

import logging

from sqlalchemy import select

from src.config.database import SessionLocal
from src.infrastructure.db.models.ingest import Source

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("shotpocket.seed_sources")

# (name, base_url, source_type_cd, priority)
SEED_SOURCES: list[tuple[str, str, str, int]] = [
    (
        "dcinside-hit",
        "https://gall.dcinside.com/board/lists/?id=hit",
        "DCINSIDE",
        20,
    ),
    (
        "ruliweb-humor-best",
        "https://bbs.ruliweb.com/best/humor",
        "RULIWEB",
        20,
    ),
    (
        # 카테고리 페이지 URL(인코딩) — 분류:인터넷 밈
        "namuwiki-internet-meme",
        "https://namu.wiki/w/%EB%B6%84%EB%A5%98:%EC%9D%B8%ED%84%B0%EB%84%B7%20%EB%B0%88",
        "NAMUWIKI",
        20,
    ),
]


def seed() -> int:
    db = SessionLocal()
    added = 0
    try:
        for name, base_url, type_cd, priority in SEED_SOURCES:
            exists = db.execute(
                select(Source).where(Source.source_type_cd == type_cd)
            ).scalar_one_or_none()
            if exists is not None:
                logger.info("%s 소스 이미 존재 — 스킵", type_cd)
                continue
            db.add(
                Source(
                    name=name,
                    base_url=base_url,
                    source_type_cd=type_cd,
                    priority=priority,
                    enabled_yn=True,
                )
            )
            added += 1
            logger.info("%s 소스 생성 (%s)", type_cd, base_url)
        db.commit()
    finally:
        db.close()
    logger.info("seed_sources 완료 — 신규 %d건", added)
    return added


if __name__ == "__main__":
    n = seed()
    print("SEED_SOURCES_RESULT", {"added": n})
