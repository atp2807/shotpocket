"""meme 도메인 엔티티 — 순수 파이썬(프레임워크/ORM 비의존)."""
from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass


class MemeStatus:
    """짤 상태코드 (정본: packages/shared/categories.js MEME_STATUS + PENDING)."""

    # R2 업로드 전 선생성 상태 — orphan 방지 규약(선생성→업로드→확정)용.
    # orphan_cleanup 잡이 일정 시간 경과한 PENDING 을 회수한다.
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    HIDDEN = "HIDDEN"
    # 신고 확정 삭제 (복구 불가 종결 상태)
    REMOVED = "REMOVED"


class MediaType:
    """미디어 유형코드 (정본: packages/shared/categories.js MEDIA_TYPE).

    STILL(스틸컷) / LOOP(루프 움짤) 둘뿐이다.
    - 원본 포맷이 무엇이든 서빙 유형이 루프 재생이면 LOOP.
    - 일반 동영상은 제품 정책상 수집 금지 — 별도 유형코드가 존재하지 않는다.
    """

    STILL = "STILL"
    LOOP = "LOOP"


@dataclass
class MemeEntity:
    """도메인 짤 엔티티. ORM 모델과 분리해 서비스 계층 계약을 안정화한다."""

    id: uuid.UUID
    media_type_cd: str
    status_cd: str
    origin_url: str | None = None
    source_cd: str | None = None
    r2_mp4_key: str | None = None
    r2_thumb_key: str | None = None
    width: int | None = None
    height: int | None = None
    duration_ms: int | None = None
    created_ts: dt.datetime | None = None

    @property
    def is_visible(self) -> bool:
        return self.status_cd == MemeStatus.ACTIVE
