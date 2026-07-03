"""코드값 상수 (파이썬 미러) — 정본: packages/shared/categories.js.

프론트/백 공용 정본은 JS 파일이며, 백엔드 파이프라인(시드/비전 mock)이 참조하기
위한 파이썬 미러. 값이 어긋나지 않도록 JS 와 동일 문자열을 유지한다.
"""
from __future__ import annotations

EMOTION = {
    "JOY": "기쁨",
    "SADNESS": "슬픔",
    "ANGER": "분노",
    "TIRED": "피곤",
    "AWKWARD": "어색",
    "PANIC": "당황",
    "PROUD": "뿌듯",
    "LOVE": "애정",
    "DISGUST": "현타",
    "SURPRISE": "놀람",
}

SITUATION = {
    "WORK": "회사",
    "SCHOOL": "학교",
    "FRIEND": "친구",
    "LOVE": "연애",
    "GAME": "게임",
    "FOOD": "음식",
    "MONEY": "돈",
    "EXERCISE": "운동",
    "WEATHER": "날씨",
    "ETC": "기타",
}

EMOTION_CODES = tuple(EMOTION.keys())
SITUATION_CODES = tuple(SITUATION.keys())
