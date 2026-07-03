"""도메인 예외 — BusinessError.

서비스 계층은 ErrorCode 상수를 담아 BusinessError 를 raise 하고,
presentation.middleware.error_handler 가 이를 잡아 {error_code, message} 응답으로 변환한다.
"""
from __future__ import annotations

from src.shared.errors.error_codes import _ErrorCode


class BusinessError(Exception):
    """비즈니스 규칙 위반. error_code(_ErrorCode)를 그대로 전달한다."""

    def __init__(self, error_code: _ErrorCode, message: str | None = None) -> None:
        self.error_code = error_code
        # message 인자로 문맥별 상세 메시지 override 가능(기본은 레지스트리 메시지)
        self.message = message or error_code.message
        super().__init__(self.message)
