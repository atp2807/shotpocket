"""APScheduler 진입점 — 무인 운영 파이프라인 잡 스텁.

잡:
  - crawl              : 1시간마다 소스 크롤 → raw_item(FETCHED)
  - pipeline_tick      : 10분마다 dedup→analyze→transcode→embed→publish 순차 처리
  - rank_recalc        : 1시간마다 인기/신선도 기반 rank_score 재계산
  - seo_build          : 매일 04:00 사이트맵/정적 SEO 빌드
  - orphan_cleanup     : 매일 05:00 R2 고아 객체 + PENDING 잔여 회수

각 잡은 DB 세션을 열어 해당 서비스를 호출하고 로그만 남기는 스텁이다.
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from src.config.database import SessionLocal
from src.features.ingest.application.analyze_service import AnalyzeService
from src.features.ingest.application.crawl_service import CrawlService
from src.features.ingest.application.dedup_service import DedupService
from src.features.ingest.application.embed_service import EmbedService
from src.features.ingest.application.publish_service import PublishService
from src.features.ingest.application.transcode_service import TranscodeService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("shotpocket.scheduler")


def job_crawl() -> None:
    db = SessionLocal()
    try:
        n = CrawlService(db).crawl()
        logger.info("[crawl] created=%d", n)
    finally:
        db.close()


def job_pipeline_tick() -> None:
    """dedup → analyze → transcode → embed → publish 를 순차로 한 틱 진행."""
    db = SessionLocal()
    try:
        DedupService(db).run()
        AnalyzeService(db).run()
        TranscodeService(db).run()
        EmbedService(db).run()
        PublishService(db).run()
        logger.info("[pipeline_tick] done")
    finally:
        db.close()


def job_rank_recalc() -> None:
    db = SessionLocal()
    try:
        # 스텁: rank_score = f(like, download, view, 신선도) 재계산 예정
        logger.info("[rank_recalc] stub")
    finally:
        db.close()


def job_seo_build() -> None:
    # 스텁: 사이트맵/OG/정적 SEO 산출물 빌드 예정
    logger.info("[seo_build] stub")


def job_orphan_cleanup() -> None:
    db = SessionLocal()
    try:
        # 스텁: 일정시간 경과한 PENDING 레코드 + 대응 없는 R2 객체 회수 예정
        logger.info("[orphan_cleanup] stub")
    finally:
        db.close()


def build_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="Asia/Seoul")
    scheduler.add_job(job_crawl, "interval", hours=1, id="crawl")
    scheduler.add_job(job_pipeline_tick, "interval", minutes=10, id="pipeline_tick")
    scheduler.add_job(job_rank_recalc, "interval", hours=1, id="rank_recalc")
    scheduler.add_job(job_seo_build, "cron", hour=4, minute=0, id="seo_build")
    scheduler.add_job(job_orphan_cleanup, "cron", hour=5, minute=0, id="orphan_cleanup")
    return scheduler


def main() -> None:
    scheduler = build_scheduler()
    scheduler.start()
    logger.info("scheduler started: %s", [j.id for j in scheduler.get_jobs()])
    try:
        import time

        while True:
            time.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("scheduler stopped")


if __name__ == "__main__":
    main()
