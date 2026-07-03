"""report 도메인 코드값 (정본: packages/shared/categories.js + 네이밍사전)."""
from __future__ import annotations


class ReportReason:
    """신고 사유코드 — 6값."""

    COPYRIGHT = "COPYRIGHT"
    PORTRAIT_RIGHT = "PORTRAIT_RIGHT"
    NSFW = "NSFW"
    HATE = "HATE"
    SPAM = "SPAM"
    ETC = "ETC"


class ReportStatus:
    """신고 상태코드 — PENDING 없음(신고=접수 즉시 자동 비공개, 무인 원칙).

    AUTO_HIDDEN(기본, 접수 즉시 대상 짤 숨김) → RESTORED(운영 복구) | REMOVED(삭제 확정)
    """

    AUTO_HIDDEN = "AUTO_HIDDEN"
    RESTORED = "RESTORED"
    REMOVED = "REMOVED"
