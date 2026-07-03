"""에러코드 레지스트리 — frozen dataclass 패턴.

각 에러코드는 code(DOMAIN_NNN) / status(HTTP) / message(사용자 노출 문구)를 갖는다.
error_handler 가 BusinessError 를 받아 {error_code, message} 응답으로 변환한다.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class _ErrorCode:
    code: str
    status: int
    message: str


class ErrorCode:
    # 공통
    COMMON_001 = _ErrorCode("COMMON_001", 400, "잘못된 요청입니다.")
    COMMON_002 = _ErrorCode("COMMON_002", 500, "서버 오류가 발생했습니다.")
    COMMON_003 = _ErrorCode("COMMON_003", 429, "요청 한도를 초과했습니다.")

    # 짤(meme)
    MEME_NOT_FOUND = _ErrorCode("MEME_001", 404, "짤을 찾을 수 없습니다.")

    # 검색(search)
    SEARCH_EMPTY_QUERY = _ErrorCode("SEARCH_001", 400, "검색어가 비어있습니다.")
    SEARCH_FAILED = _ErrorCode("SEARCH_002", 500, "검색에 실패했습니다.")

    # 피드(feed)
    FEED_INVALID_CURSOR = _ErrorCode("FEED_001", 400, "잘못된 커서입니다.")

    # 인게이지(engage)
    ENGAGE_DUPLICATE = _ErrorCode("ENGAGE_001", 409, "중복 요청입니다.")

    # 신고(report)
    REPORT_INVALID_REASON = _ErrorCode("REPORT_001", 400, "잘못된 신고 사유입니다.")

    # 운영(ops)
    OPS_FORBIDDEN = _ErrorCode("OPS_001", 403, "권한이 없습니다.")
