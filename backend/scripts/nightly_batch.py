#!/usr/bin/env python3
"""맥 야간 무인 인덱싱 배치 오케스트레이터 — 사람 개입 0.

매일 밤 맥에서 한 번 완주한다:
  크롤(디시·루리웹) → pHash 중복제거 → claude_cli vision 분석(NOT_MEME 필터)
  → 변환 → 임베딩(fastembed) → 서버(프로덕션) DB 로 게시(PENDING) → 미디어 rsync
  → 일괄 활성화(PENDING→ACTIVE).

핵심 안전장치
  - 락파일(var/nightly.lock): 동시 실행 방지. stale 6h 초과면 무시하고 진행.
  - SSH 터널: 서버 DB(127.0.0.1:5432, 외부 미노출)로 로컬 임의 포트를 포워딩.
    서버 .env 의 DATABASE_URL 을 ssh 로 읽어 host/port 만 터널로 치환해 사용
    (비밀번호는 프로세스 메모리에만, 맥 디스크에 저장하지 않음).
  - PUBLISH_DEFER_ACTIVATE: 게시는 PENDING 으로만 만든다. 미디어가 서버로 rsync
    된 뒤에야 활성화 → 피드에 깨진 이미지가 뜨지 않는다.
  - rsync 는 -az (never --delete). rsync 실패 시 활성화 스킵 → 다음 run 이
    PENDING 을 재시도(활성화는 "이번 run + 서버에 파일 존재 확인"된 것만).
  - 어느 단계가 죽어도 finally 에서 터널·락을 반드시 정리한다.

실행:  .venv/bin/python -m scripts.nightly_batch
검증:  POSTS_PER_SOURCE=3 ANALYZE_LIMIT=5 .venv/bin/python -m scripts.nightly_batch
"""
from __future__ import annotations

import logging
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

BACKEND_DIR = Path(__file__).resolve().parents[1]  # backend/
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

VAR_DIR = BACKEND_DIR / "var"
LOCK_FILE = VAR_DIR / "nightly.lock"
STAGING_DIR = VAR_DIR / "staging_media"
LOCK_STALE_SECONDS = 6 * 3600

# 인프라 사실 (코디네이터 제공)
SSH_KEY = "/Users/daviy/Developer/key_pair/hadream/ops_aws_server/haedream-key.pem"
SERVER_USER = "ubuntu"
SERVER_HOST = "3.34.226.185"
SERVER_PORT = "23023"
SERVER_ENV_PATH = "/home/ubuntu/shotpocket/backend/.env"
SERVER_MEDIA_ROOT = "/home/ubuntu/shotpocket/media"
SERVER_DB_HOST = "127.0.0.1"
SERVER_DB_PORT = 5432

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("shotpocket.nightly")


# ---------------------------------------------------------------------------
# SSH helpers
# ---------------------------------------------------------------------------
def _ssh_base() -> list[str]:
    return [
        "ssh", "-i", SSH_KEY, "-p", SERVER_PORT,
        "-o", "ConnectTimeout=15",
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", "BatchMode=yes",
    ]


def _ssh(cmd: str, timeout: int = 60) -> str:
    """서버에서 명령 실행 → stdout(문자열). 실패 시 예외."""
    completed = subprocess.run(
        [*_ssh_base(), f"{SERVER_USER}@{SERVER_HOST}", cmd],
        capture_output=True, text=True, timeout=timeout, check=True,
    )
    return completed.stdout


def read_server_db_url() -> str:
    """서버 .env 의 DATABASE_URL 을 메모리로 읽어온다(디스크 저장 금지)."""
    out = _ssh(f"grep -m1 '^DATABASE_URL=' {SERVER_ENV_PATH}").strip()
    if not out.startswith("DATABASE_URL="):
        raise RuntimeError("서버 .env 에서 DATABASE_URL 을 찾지 못함")
    return out.split("=", 1)[1].strip().strip('"').strip("'")


def rewrite_db_url_for_tunnel(url: str, local_port: int) -> str:
    """DATABASE_URL 의 host/port 만 로컬 터널 엔드포인트로 치환(자격증명 보존)."""
    parts = urlsplit(url)
    userinfo = ""
    if parts.username:
        userinfo = parts.username
        if parts.password:
            userinfo += f":{parts.password}"
        userinfo += "@"
    netloc = f"{userinfo}127.0.0.1:{local_port}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def open_tunnel(local_port: int) -> subprocess.Popen:
    """서버 DB(127.0.0.1:5432)로 로컬 포트를 포워딩하는 ssh -N -L 프로세스."""
    proc = subprocess.Popen(
        [
            *_ssh_base(),
            "-N",
            "-o", "ExitOnForwardFailure=yes",
            "-o", "ServerAliveInterval=30",
            "-L", f"{local_port}:{SERVER_DB_HOST}:{SERVER_DB_PORT}",
            f"{SERVER_USER}@{SERVER_HOST}",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    # 포워딩 준비 대기 — 로컬 포트에 접속될 때까지 최대 20초 폴링
    deadline = time.time() + 20
    while time.time() < deadline:
        if proc.poll() is not None:
            err = (proc.stderr.read() if proc.stderr else "") or ""
            raise RuntimeError(f"SSH 터널 조기 종료: {err.strip()[:200]}")
        try:
            with socket.create_connection(("127.0.0.1", local_port), timeout=1):
                logger.info("SSH 터널 준비 완료 — 127.0.0.1:%d → 서버 DB", local_port)
                return proc
        except OSError:
            time.sleep(0.5)
    proc.terminate()
    raise RuntimeError("SSH 터널 준비 시간 초과")


def close_tunnel(proc: subprocess.Popen | None) -> None:
    if proc is None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
    logger.info("SSH 터널 종료")


# ---------------------------------------------------------------------------
# Lock
# ---------------------------------------------------------------------------
def acquire_lock() -> bool:
    """락 획득 성공 여부. 이미 유효한 락이 있으면 False(즉시 종료용)."""
    VAR_DIR.mkdir(parents=True, exist_ok=True)
    if LOCK_FILE.exists():
        age = time.time() - LOCK_FILE.stat().st_mtime
        if age < LOCK_STALE_SECONDS:
            other = LOCK_FILE.read_text().strip()
            logger.warning(
                "이미 실행 중(lock pid=%s, %.0f분 전) — 즉시 종료", other, age / 60
            )
            return False
        logger.warning("stale lock(%.1f시간) 무시하고 진행", age / 3600)
    LOCK_FILE.write_text(str(os.getpid()))
    return True


def release_lock() -> None:
    LOCK_FILE.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# rsync + 활성화
# ---------------------------------------------------------------------------
def rsync_media() -> int:
    """스테이징 미디어를 서버 미디어 루트로 rsync. 전송된 파일 수를 반환.

    -az, --itemize-changes. --delete 는 절대 사용하지 않는다(서버 기존 미디어 보호).
    """
    if not STAGING_DIR.exists() or not any(STAGING_DIR.iterdir()):
        logger.info("rsync: 스테이징 비어 있음 — 전송 없음")
        return 0
    rsh = f"ssh -i {SSH_KEY} -p {SERVER_PORT} -o ConnectTimeout=15 -o StrictHostKeyChecking=accept-new -o BatchMode=yes"
    completed = subprocess.run(
        [
            "rsync", "-az", "--itemize-changes",
            "-e", rsh,
            f"{STAGING_DIR}/",
            f"{SERVER_USER}@{SERVER_HOST}:{SERVER_MEDIA_ROOT}/",
        ],
        capture_output=True, text=True, timeout=600, check=True,
    )
    # 실제 전송된 정규 파일 = itemize 출력에서 '>f...' 로 시작하는 라인
    transferred = sum(
        1 for ln in completed.stdout.splitlines() if ln.startswith(">f")
    )
    logger.info("rsync 완료 — 전송 파일 %d개", transferred)
    return transferred


def server_media_dirs() -> set[str]:
    """서버 미디어 루트에 존재하는 meme_id 디렉토리 집합(활성화 존재확인용)."""
    out = _ssh(f"ls -1 {SERVER_MEDIA_ROOT} 2>/dev/null")
    return {ln.strip() for ln in out.splitlines() if ln.strip()}


def clear_staging() -> None:
    if STAGING_DIR.exists():
        shutil.rmtree(STAGING_DIR, ignore_errors=True)
    STAGING_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# 파이프라인
# ---------------------------------------------------------------------------
def _inject_env(tunnel_url: str) -> None:
    """서비스 임포트 전에 환경변수를 주입 — settings 싱글턴이 터널 DB·맥 설정을 본다."""
    os.environ["DATABASE_URL"] = tunnel_url
    os.environ["VISION_PROVIDER"] = "claude_cli"      # 구독 OAuth vision 강제
    os.environ["EMBEDDING_PROVIDER"] = "fastembed"    # 서버와 벡터 호환(384d)
    os.environ["STORAGE_MODE"] = "local"
    os.environ["MEDIA_ROOT"] = str(STAGING_DIR)        # 로컬 스테이징으로 게시
    os.environ["PUBLISH_DEFER_ACTIVATE"] = "true"      # PENDING 유지(rsync 후 활성화)
    os.environ["DEBUG"] = "false"                      # 서버 DB SQL echo 억제


def run() -> int:
    """전체 배치 1회 완주. 종료코드(0=성공, 1=실패)를 반환."""
    posts_per_source = int(os.environ.get("POSTS_PER_SOURCE", "30"))
    analyze_limit = int(os.environ.get("ANALYZE_LIMIT", "150"))
    stage_limit = int(os.environ.get("STAGE_LIMIT", "500"))

    t_start = time.monotonic()
    summary: dict[str, object] = {}
    timings: dict[str, float] = {}
    failed_stage: str | None = None
    meme_ids: list[str] = []
    transferred = 0
    activated = 0

    STAGING_DIR.mkdir(parents=True, exist_ok=True)

    # 환경 주입 후에 임포트해야 settings 가 터널 DB/맥 설정을 반영한다.
    from sqlalchemy import func, select
    from sqlalchemy import text as sa_text

    from src.config.database import SessionLocal
    from src.features.ingest.application.analyze_service import AnalyzeService
    from src.features.ingest.application.crawl_service import CrawlService
    from src.features.ingest.application.dedup_service import DedupService
    from src.features.ingest.application.embed_service import EmbedService
    from src.features.ingest.application.publish_service import PublishService
    from src.features.ingest.application.transcode_service import TranscodeService
    from src.features.ingest.domain.pipeline_states import (
        MAC_ONLY_SOURCE_TYPES,
        PipelineState,
        RejectReason,
    )
    from src.infrastructure.db.models.ingest import RawItem

    def _not_meme_total(db) -> int:
        return db.execute(
            select(func.count()).select_from(RawItem).where(
                RawItem.status_cd == PipelineState.REJECTED,
                RawItem.reject_reason_cd == RejectReason.NOT_MEME,
            )
        ).scalar_one()

    def stage(name: str, fn):
        nonlocal failed_stage
        failed_stage = name
        t0 = time.monotonic()
        result = fn()
        timings[name] = time.monotonic() - t0
        return result

    db = SessionLocal()
    try:
        # 1) 서버 DB 접속 확인 (기존 meme count 인용)
        server_meme_count = db.execute(
            sa_text("SELECT count(*) FROM meme.meme")
        ).scalar_one()
        summary["server_meme_before"] = server_meme_count
        logger.info("서버 DB 접속 성공 — 기존 meme 총 %d건", server_meme_count)

        # 2) 크롤 → dedup → analyze(claude_cli) → transcode → embed → publish
        not_meme_before = _not_meme_total(db)

        # 맥 전용 소스(MAC_ONLY_SOURCE_TYPES)로 전 단계를 스코핑한다 — 서버가 크롤한
        # 항목(파일이 서버 로컬 디스크에만 있음)을 맥이 잘못 집어가는 레이스를 방지
        # (실측으로 발견된 문제, lr-d0c4207f). crawl 도 같은 이유로 이 소스만 시도한다.
        summary["crawl"] = stage(
            "crawl",
            lambda: CrawlService(db).crawl(
                post_limit=posts_per_source, include_source_types=MAC_ONLY_SOURCE_TYPES
            ),
        )
        summary["dedup"] = stage(
            "dedup",
            lambda: DedupService(db).run(
                stage_limit, include_source_types=MAC_ONLY_SOURCE_TYPES
            ),
        )
        summary["analyze"] = stage(
            "analyze",
            lambda: AnalyzeService(db).run(
                analyze_limit, include_source_types=MAC_ONLY_SOURCE_TYPES
            ),
        )
        summary["not_meme_rejected"] = _not_meme_total(db) - not_meme_before
        summary["transcode"] = stage(
            "transcode",
            lambda: TranscodeService(db).run(
                stage_limit, include_source_types=MAC_ONLY_SOURCE_TYPES
            ),
        )
        summary["embed"] = stage(
            "embed",
            lambda: EmbedService(db).run(
                stage_limit, include_source_types=MAC_ONLY_SOURCE_TYPES
            ),
        )

        meme_ids = stage(
            "publish",
            lambda: PublishService(db).run(
                stage_limit, include_source_types=MAC_ONLY_SOURCE_TYPES
            ),
        )
        summary["publish_pending"] = len(meme_ids)

        # 3) 미디어 rsync (실패 시 활성화 스킵)
        transferred = stage("rsync", rsync_media)
        summary["rsync_files"] = transferred

        # 4) 활성화 — 이번 run 중 서버에 파일이 실제 존재하는 meme 만 PENDING→ACTIVE
        if meme_ids:
            present = server_media_dirs()
            to_activate = [m for m in meme_ids if m in present]
            if to_activate:
                res = stage(
                    "activate",
                    lambda: db.execute(
                        sa_text(
                            "UPDATE meme.meme SET status_cd='ACTIVE', updated_ts=now() "
                            "WHERE id = ANY(CAST(:ids AS uuid[])) AND status_cd='PENDING'"
                        ),
                        {"ids": to_activate},
                    ),
                )
                db.commit()
                activated = res.rowcount
            summary["activated"] = activated
            if len(to_activate) < len(meme_ids):
                logger.warning(
                    "서버에 파일 미확인 %d건 — 활성화 보류(다음 run 재시도)",
                    len(meme_ids) - len(to_activate),
                )

        # 5) rsync 성공 + 활성화까지 끝났으면 스테이징 정리
        clear_staging()
        failed_stage = None
    except Exception:
        logger.exception("배치 실패 — 단계=%s", failed_stage)
    finally:
        db.close()

    elapsed = time.monotonic() - t_start
    _log_summary(summary, timings, failed_stage, elapsed)
    return 1 if failed_stage else 0


def _log_summary(summary, timings, failed_stage, elapsed) -> None:
    logger.info("=" * 60)
    logger.info("야간 배치 요약 (총 %.1fs)", elapsed)
    logger.info(
        "  서버 meme(전) %s → 게시(PENDING) %s → rsync %s파일 → 활성화 %s",
        summary.get("server_meme_before", "?"),
        summary.get("publish_pending", 0),
        summary.get("rsync_files", 0),
        summary.get("activated", 0),
    )
    logger.info(
        "  단계건수: crawl=%s dedup=%s analyze=%s (NOT_MEME reject=%s) "
        "transcode=%s embed=%s",
        summary.get("crawl", 0),
        summary.get("dedup", 0),
        summary.get("analyze", 0),
        summary.get("not_meme_rejected", 0),
        summary.get("transcode", 0),
        summary.get("embed", 0),
    )
    if timings:
        logger.info(
            "  소요(초): %s",
            " ".join(f"{k}={v:.1f}" for k, v in timings.items()),
        )
    if failed_stage:
        logger.error("  결과: 실패 — 단계=%s", failed_stage)
    else:
        logger.info("  결과: 성공")
    logger.info("=" * 60)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main() -> int:
    if not acquire_lock():
        return 0  # 다른 run 이 진행 중 — 즉시 정상 종료

    tunnel: subprocess.Popen | None = None
    try:
        db_url = read_server_db_url()
        local_port = _pick_free_port()
        tunnel = open_tunnel(local_port)
        tunnel_url = rewrite_db_url_for_tunnel(db_url, local_port)
        _inject_env(tunnel_url)
        return run()
    except Exception:
        logger.exception("배치 부트스트랩 실패")
        return 1
    finally:
        close_tunnel(tunnel)
        release_lock()


if __name__ == "__main__":
    raise SystemExit(main())
