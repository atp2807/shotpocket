"""수동 파이프라인 실행 진입점 — `python -m scripts.run_pipeline`.

INBOX_DIR 를 크롤 → dedup → analyze → transcode → embed → publish → rank_recalc
순으로 한 번 완주한다. 무인 scheduler(pipeline_tick)와 동일 로직을 수동 구동한다.
"""
from __future__ import annotations

import logging

from src.config.database import SessionLocal
from src.features.engage.application.rank_service import RankService
from src.features.ingest.application.analyze_service import AnalyzeService
from src.features.ingest.application.crawl_service import CrawlService
from src.features.ingest.application.dedup_service import DedupService
from src.features.ingest.application.embed_service import EmbedService
from src.features.ingest.application.publish_service import PublishService
from src.features.ingest.application.transcode_service import TranscodeService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("shotpocket.pipeline")


def run_once() -> dict:
    db = SessionLocal()
    try:
        counts = {
            "crawl": CrawlService(db).crawl(),
            "dedup": DedupService(db).run(),
            "analyze": AnalyzeService(db).run(),
            "transcode": TranscodeService(db).run(),
            "embed": EmbedService(db).run(),
            "publish": PublishService(db).run(),
            "rank_recalc": RankService(db).recalc(),
        }
        logger.info("pipeline done: %s", counts)
        return counts
    finally:
        db.close()


if __name__ == "__main__":
    result = run_once()
    print("PIPELINE_RESULT", result)
