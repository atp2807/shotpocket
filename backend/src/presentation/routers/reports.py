"""reports 라우터 — 공개(인증 없음). 신고=자동 비공개."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.features.report.application.report_service import ReportService
from src.presentation.deps import get_ip_hash
from src.presentation.schemas.report.report_schema import (
    ReportCreateRequest,
    ReportResponse,
)

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
def create_report(
    body: ReportCreateRequest, request: Request, db: Session = Depends(get_db)
) -> ReportResponse:
    report = ReportService(db).create_report(
        meme_id=body.meme_id,
        reason_cd=body.reason_cd,
        contact=body.contact,
        detail=body.detail,
        ip_hash=get_ip_hash(request),
    )
    return ReportResponse.model_validate(report)
