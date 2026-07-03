"""ops 라우터 — 운영 전용.

인증: 이 서비스에는 사용자 계정이 없다. 운영 엔드포인트는 Cloudflare Access
뒤에 배치하는 것을 전제로 하며, 추가로 X-Ops-Key 헤더 == settings.OPS_API_KEY
를 검증하는 Depends 를 둔다(이중 방어). 불일치 시 OPS_001(403).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.config.settings import settings
from src.features.meme.domain.entities import MemeStatus
from src.features.report.application.report_service import ReportService
from src.infrastructure.db.models.meme import Meme
from src.infrastructure.db.models.stat import MemeStat, QueryLog
from src.presentation.schemas.report.report_schema import (
    ReportListResponse,
    ReportResponse,
)
from src.shared.errors.error_codes import ErrorCode
from src.shared.errors.exceptions import BusinessError

router = APIRouter(prefix="/api/ops", tags=["ops"])


def require_ops_key(x_ops_key: str | None = Header(default=None)) -> None:
    """X-Ops-Key 검증. Cloudflare Access 뒤단 이중 방어."""
    if not x_ops_key or x_ops_key != settings.OPS_API_KEY:
        raise BusinessError(ErrorCode.OPS_FORBIDDEN)


@router.get("/reports", response_model=ReportListResponse, dependencies=[Depends(require_ops_key)])
def list_reports(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_cd: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> ReportListResponse:
    items, total, page_out, size_out = ReportService(db).list_reports(
        page=page, page_size=page_size, status_cd=status_cd
    )
    return ReportListResponse(
        items=[ReportResponse.model_validate(r) for r in items],
        total=total,
        page=page_out,
        page_size=size_out,
    )


@router.get("/stats", dependencies=[Depends(require_ops_key)])
def get_stats(db: Session = Depends(get_db)) -> dict:
    """운영 대시보드용 집계(단건 엔티티 아님 → dict 직접 반환)."""
    active_cnt = db.execute(
        select(func.count()).select_from(Meme).where(Meme.status_cd == MemeStatus.ACTIVE)
    ).scalar_one()
    hidden_cnt = db.execute(
        select(func.count()).select_from(Meme).where(Meme.status_cd == MemeStatus.HIDDEN)
    ).scalar_one()
    total_like = db.execute(select(func.coalesce(func.sum(MemeStat.like_cnt), 0))).scalar_one()
    total_download = db.execute(
        select(func.coalesce(func.sum(MemeStat.download_cnt), 0))
    ).scalar_one()
    query_cnt = db.execute(select(func.count()).select_from(QueryLog)).scalar_one()
    return {
        "active_meme_cnt": int(active_cnt),
        "hidden_meme_cnt": int(hidden_cnt),
        "total_like_cnt": int(total_like),
        "total_download_cnt": int(total_download),
        "query_cnt": int(query_cnt),
    }
