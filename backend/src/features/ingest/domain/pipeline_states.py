"""수집 파이프라인 상태 정의.

raw_item.status_cd 전이:
  FETCHED → DEDUPED → ANALYZED → TRANSCODED → EMBEDDED → PUBLISHED
  (임의 단계에서 REJECTED 로 이탈 가능; reject_reason_cd 기록)
각 파이프라인 잡은 '입력 상태' 항목을 집어 '출력 상태'로 전이시킨다.
"""
from __future__ import annotations


class PipelineState:
    FETCHED = "FETCHED"
    DEDUPED = "DEDUPED"
    ANALYZED = "ANALYZED"
    TRANSCODED = "TRANSCODED"
    EMBEDDED = "EMBEDDED"
    PUBLISHED = "PUBLISHED"
    REJECTED = "REJECTED"


class RejectReason:
    DUPLICATE = "DUPLICATE"
    NSFW = "NSFW"
    LOW_QUALITY = "LOW_QUALITY"
    FETCH_ERROR = "FETCH_ERROR"
    UNSUPPORTED = "UNSUPPORTED"
    # 루프(움짤) 재생시간이 정책 상한(3초)을 초과
    TOO_LONG = "TOO_LONG"


# 파이프라인 틱에서 순차 처리할 (입력→출력) 전이 순서
PIPELINE_ORDER: list[tuple[str, str]] = [
    (PipelineState.FETCHED, PipelineState.DEDUPED),
    (PipelineState.DEDUPED, PipelineState.ANALYZED),
    (PipelineState.ANALYZED, PipelineState.TRANSCODED),
    (PipelineState.TRANSCODED, PipelineState.EMBEDDED),
    (PipelineState.EMBEDDED, PipelineState.PUBLISHED),
]
