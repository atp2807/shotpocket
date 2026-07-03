"""report 리포지토리 — SQLAlchemy 쿼리."""
from __future__ import annotations

import uuid

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from src.features.report.domain.entities import ReportStatus
from src.infrastructure.db.models.ops import Report


class ReportRepo:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        meme_id: uuid.UUID,
        reason_cd: str,
        contact: str | None,
        detail: str | None,
        ip_hash: str | None,
    ) -> Report:
        report = Report(
            meme_id=meme_id,
            reason_cd=reason_cd,
            status_cd=ReportStatus.AUTO_HIDDEN,
            contact=contact,
            detail=detail,
            ip_hash=ip_hash,
        )
        self.db.add(report)
        self.db.flush()
        return report

    def list_reports(
        self, page: int, page_size: int, status_cd: str | None = None
    ) -> tuple[list[Report], int]:
        base = select(Report)
        if status_cd:
            base = base.where(Report.status_cd == status_cd)

        total = int(
            self.db.execute(select(func.count()).select_from(base.subquery())).scalar_one()
        )
        stmt = (
            base.order_by(desc(Report.created_ts))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = list(self.db.execute(stmt).scalars().all())
        return items, total
