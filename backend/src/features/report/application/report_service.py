"""report 애플리케이션 서비스 — 신고 접수 = 자동 비공개(무인 원칙)."""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from src.features.meme.domain.entities import MemeStatus
from src.features.meme.infrastructure.meme_repo import MemeRepo
from src.features.report.domain.entities import ReportReason
from src.features.report.infrastructure.report_repo import ReportRepo
from src.infrastructure.db.models.ops import Report
from src.shared.errors.error_codes import ErrorCode
from src.shared.errors.exceptions import BusinessError

# 허용 신고 사유코드 (정본 6값: packages/shared/categories.js REPORT_REASON)
VALID_REASONS = frozenset(
    {
        ReportReason.COPYRIGHT,
        ReportReason.PORTRAIT_RIGHT,
        ReportReason.NSFW,
        ReportReason.HATE,
        ReportReason.SPAM,
        ReportReason.ETC,
    }
)


class ReportService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = ReportRepo(db)
        self.meme_repo = MemeRepo(db)

    def create_report(
        self,
        meme_id: uuid.UUID,
        reason_cd: str,
        contact: str | None = None,
        detail: str | None = None,
        ip_hash: str | None = None,
    ) -> Report:
        """신고 접수 → 대상 짤 즉시 HIDDEN 전이(무인 자동 비공개)."""
        if reason_cd not in VALID_REASONS:
            raise BusinessError(ErrorCode.REPORT_INVALID_REASON)
        if self.meme_repo.get_by_id(meme_id) is None:
            raise BusinessError(ErrorCode.MEME_NOT_FOUND)

        report = self.repo.create(meme_id, reason_cd, contact, detail, ip_hash)
        # 신고=자동 비공개: 검토 전 선제 숨김
        self.meme_repo.set_status(meme_id, MemeStatus.HIDDEN)
        self.db.commit()
        return report

    def list_reports(
        self, page: int = 1, page_size: int = 20, status_cd: str | None = None
    ) -> tuple[list[Report], int, int, int]:
        page = max(page, 1)
        page_size = max(min(page_size, 100), 1)
        items, total = self.repo.list_reports(page, page_size, status_cd)
        return items, total, page, page_size
