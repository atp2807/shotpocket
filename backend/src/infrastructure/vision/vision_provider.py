"""비전 분석 공급자 — 이미지 → 캡션/감정/상황/OCR 등 분석 결과.

- VisionProvider: 인터페이스 (analyze(path, orig_filename) -> dict)
- MockVisionProvider: Pillow 주요색 추출 + 파일명 규칙 기반. 네트워크/키 불필요. confidence 0.2
- AnthropicVisionProvider: claude-haiku vision (httpx). ANTHROPIC_API_KEY 있을 때만. confidence 0.9

분석 결과 dict 키(정본 meme.analysis 규격):
  caption, situation, emotion_cd, ocr_text, usage_context,
  character_name, meme_name, lang_cd, nsfw_score, confidence, model_cd
공급자 선택은 settings.VISION_PROVIDER (mock|anthropic, 기본 mock).
키 없으면 anthropic → mock 자동 폴백.
"""
from __future__ import annotations

import base64
import json
import logging
import os
from typing import Protocol

from PIL import Image

from src.config.settings import settings
from src.shared.categories import (
    EMOTION,
    EMOTION_CODES,
    SITUATION,
    SITUATION_CODES,
)

logger = logging.getLogger("shotpocket.vision")

# 정본 analysis 스키마 키 (Anthropic JSON 강제용)
_SCHEMA_KEYS = (
    "caption",
    "situation",
    "emotion_cd",
    "ocr_text",
    "usage_context",
    "character_name",
    "meme_name",
    "lang_cd",
    "nsfw_score",
    "confidence",
    "tags",
)

_MAX_TAGS = 8


class VisionProvider(Protocol):
    def analyze(self, path: str, orig_filename: str) -> dict: ...


def _normalize_tags(raw: object) -> list[str]:
    """vision 응답의 tags 를 정본 형태로: list[str], 중복 제거, 공백 제거, 최대 개수 제한."""
    if not isinstance(raw, list):
        return []
    seen: dict[str, None] = {}
    for t in raw:
        tag = str(t).strip().lstrip("#")
        if tag and tag not in seen:
            seen[tag] = None
        if len(seen) >= _MAX_TAGS:
            break
    return list(seen)


def _dominant_colors(path: str, k: int = 3) -> list[str]:
    """Pillow 로 주요 색상 k개 추출 → #rrggbb 리스트."""
    try:
        with Image.open(path) as im:
            im = im.convert("RGB")
            im.thumbnail((64, 64))
            quant = im.quantize(colors=k)
            palette = quant.getpalette() or []
            counts = sorted(quant.getcolors() or [], reverse=True)
            colors: list[str] = []
            for _, idx in counts[:k]:
                r, g, b = palette[idx * 3 : idx * 3 + 3]
                colors.append(f"#{r:02x}{g:02x}{b:02x}")
            return colors
    except Exception:  # noqa: BLE001
        return []


class MockVisionProvider:
    """파일명 규칙 + 주요색 기반 결정적 분석(confidence 0.2)."""

    model_cd = "mock-vision"

    def analyze(self, path: str, orig_filename: str) -> dict:
        stem = os.path.splitext(orig_filename or "")[0]
        parts = [p for p in stem.replace("-", "_").split("_") if p]

        emotion_cd = next((p for p in parts if p in EMOTION_CODES), None)
        situation_cd = next((p for p in parts if p in SITUATION_CODES), None)

        # 캡션 = 코드/순번(숫자) 토큰을 제외한 나머지(한글 문구)
        caption_parts = [
            p
            for p in parts
            if p not in EMOTION_CODES and p not in SITUATION_CODES and not p.isdigit()
        ]
        caption = " ".join(caption_parts) or stem or "무제 짤"

        # 폴백: 코드가 파일명에 없으면 해시로 결정적 배정
        if emotion_cd is None:
            emotion_cd = EMOTION_CODES[hash(("e", stem)) % len(EMOTION_CODES)]
        if situation_cd is None:
            situation_cd = SITUATION_CODES[hash(("s", stem)) % len(SITUATION_CODES)]

        colors = _dominant_colors(path)
        situation_label = SITUATION.get(situation_cd, situation_cd)
        emotion_label = EMOTION.get(emotion_cd, emotion_cd)
        usage_context = (
            f"{situation_label} 상황에서 {emotion_label}할 때 쓰는 짤"
            + (f" · 주요색 {','.join(colors)}" if colors else "")
        )

        tags = _normalize_tags([situation_label, emotion_label, *caption_parts])

        return {
            "caption": caption,
            "situation": situation_label,
            "emotion_cd": emotion_cd,
            "ocr_text": caption,  # mock: 렌더된 문구를 OCR 결과로 사용
            "usage_context": usage_context,
            "character_name": None,
            "meme_name": caption,
            "lang_cd": "ko",
            "nsfw_score": 0.0,
            "confidence": 0.2,
            "model_cd": self.model_cd,
            "is_meme": True,  # mock 은 판별 능력 없음 — 통과시키고 게시 품질은 실 vision 에 위임
            "meme_score": 1.0,
            "tags": tags,
        }


class AnthropicVisionProvider:
    """claude-haiku vision 분석(confidence 0.9). 키 없으면 mock 폴백."""

    model_cd = "claude-haiku-4-5-20251001"
    _API_URL = "https://api.anthropic.com/v1/messages"

    def __init__(self) -> None:
        self._fallback = MockVisionProvider()

    def analyze(self, path: str, orig_filename: str) -> dict:
        api_key = settings.ANTHROPIC_API_KEY
        if not api_key:
            logger.info("ANTHROPIC_API_KEY 없음 → mock vision 폴백")
            return self._fallback.analyze(path, orig_filename)
        try:
            return self._analyze_remote(path, orig_filename, api_key)
        except Exception:  # noqa: BLE001
            logger.warning("anthropic vision 실패 → mock 폴백", exc_info=True)
            return self._fallback.analyze(path, orig_filename)

    def _media_type(self, path: str) -> str:
        ext = os.path.splitext(path)[1].lower()
        return {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
            ".gif": "image/gif",
        }.get(ext, "image/png")

    def _analyze_remote(self, path: str, orig_filename: str, api_key: str) -> dict:
        import httpx  # 지연 import

        with open(path, "rb") as fh:
            b64 = base64.standard_b64encode(fh.read()).decode("ascii")

        prompt = _analysis_prompt()
        payload = {
            "model": self.model_cd,
            "max_tokens": 1024,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": self._media_type(path),
                                "data": b64,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        }
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        resp = httpx.post(self._API_URL, json=payload, headers=headers, timeout=60.0)
        resp.raise_for_status()
        data = resp.json()
        text = "".join(
            b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"
        )
        parsed = json.loads(text[text.find("{") : text.rfind("}") + 1])

        result = {k: parsed.get(k) for k in _SCHEMA_KEYS}
        # 정본 강제: emotion_cd 검증, confidence 0.9 고정
        if result.get("emotion_cd") not in EMOTION_CODES:
            result["emotion_cd"] = EMOTION_CODES[0]
        result["lang_cd"] = "ko"
        result["confidence"] = 0.9
        result["nsfw_score"] = float(result.get("nsfw_score") or 0.0)
        result["model_cd"] = self.model_cd
        result["is_meme"] = bool(parsed.get("is_meme", True))
        result["meme_score"] = float(parsed.get("meme_score") or (1.0 if result["is_meme"] else 0.0))
        result["tags"] = _normalize_tags(parsed.get("tags"))
        return result


def _analysis_prompt() -> str:
    emotion_list = ", ".join(EMOTION_CODES)
    situation_list = ", ".join(SITUATION_CODES)
    return (
        "이 이미지는 한국어 밈(짤)이다. 아래 JSON 스키마로만 응답하라(설명 금지).\n"
        "{"
        '"caption": str, "situation": str, '
        f'"emotion_cd": one of [{emotion_list}], '
        '"ocr_text": str, "usage_context": str, '
        '"character_name": str|null, "meme_name": str, '
        '"lang_cd": "ko", "nsfw_score": 0~1 float, "confidence": 0~1 float, '
        '"is_meme": bool, "meme_score": 0~1 float, '
        f'"tags": string[] (최대 {_MAX_TAGS}개)'
        "}\n"
        f"situation 은 다음 코드 의미 중 하나로 서술: [{situation_list}]\n"
        "usage_context 는 '어떤 대화 상황에서 이 짤을 보내는가'를 구체적으로. "
        "ocr_text 는 이미지 안의 모든 한글/영문 텍스트.\n"
        "is_meme: **재사용 가능한 반응/감정 표현 템플릿**인지가 기준이다 — 다른 상황에서도 "
        "그대로 갖다 써도 어색하지 않은 표정·캐릭터·장면이면 true.\n"
        "false 로 판정할 것(둘 다 커뮤니티에 흔하지만 밈이 아니다):\n"
        "  1) 여행 인증샷·취미/제품 사진·풍경 등 일반 사진\n"
        "  2) **오늘/이번에 있었던 특정 일화·후기·목격담을 담은 스크린샷/사진** — "
        "본문이 '~했다', '~하길래', '~해서 놀랐다' 식 1회성 경험담이면, 표정이 재밌어도 false. "
        "예: '비행기 옆자리 사람이 침 흘리며 잠들었다', '편의점에서 물물교환 시도' 같은 "
        "그 사람 개인의 특정 사건 스토리는 다른 사람이 자기 상황에 재사용할 수 없다 → false.\n"
        "meme_score 는 '얼마나 재사용 가능한가'로 판단(일화성 스토리는 낮게, 유명 캐릭터/"
        "표정 템플릿은 높게).\n"
        "tags: 사람들이 이 짤을 찾을 때 검색할 법한 한국어 키워드(2~8개). "
        "상황·감정·등장인물·밈 유행어·행동을 짧은 명사/구로. 예: [\"퇴근\", \"월요일\", \"현타\", \"직장인\"]. "
        "situation·emotion_cd 와 겹쳐도 되고, 그보다 더 구체적인 검색어를 포함할 것."
    )


class ClaudeCliVisionProvider:
    """claude CLI headless(-p) + Read 도구 — 구독(OAuth) 기반, API 키/비용 없음.

    해드림 claude_cli.py 패턴의 vision 확장: Read 를 허용해 이미지를 시각적으로
    읽게 한다. 실패 시 mock 폴백. 맥 인덱싱 배치 전용(서버에서 쓰지 말 것 —
    서버엔 claude CLI/OAuth 없음).
    """

    _SCRUB_PREFIXES = ("ANTHROPIC_", "OPENAI_", "GOOGLE_")  # 구독(OAuth) 강제

    def __init__(self) -> None:
        self._fallback = MockVisionProvider()
        self.model_cd = f"claude-cli-{settings.CLAUDE_CLI_MODEL}"

    def analyze(self, path: str, orig_filename: str) -> dict:
        try:
            return self._analyze_cli(path)
        except Exception:  # noqa: BLE001
            logger.warning("claude_cli vision 실패 → mock 폴백", exc_info=True)
            return self._fallback.analyze(path, orig_filename)

    def _analyze_cli(self, path: str) -> dict:
        import subprocess  # 지연 import

        env = {
            k: v
            for k, v in os.environ.items()
            if not any(k.startswith(p) for p in self._SCRUB_PREFIXES)
        }
        completed = subprocess.run(
            [
                "claude", "-p",
                "--output-format", "json",
                "--allowedTools", "Read",
                "--model", settings.CLAUDE_CLI_MODEL,
                "--system-prompt",
                "밈 이미지 분석기. Read 도구로 지정된 이미지 파일을 읽고, "
                "요구된 JSON 하나만 출력한다. 다른 텍스트 금지.",
                f"이미지 파일을 Read 로 읽어라: {os.path.abspath(path)}\n\n" + _analysis_prompt(),
            ],
            capture_output=True,
            text=True,
            timeout=180,
            env=env,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(f"claude CLI 실패: {completed.stderr.strip()[:200]}")

        payload = json.loads(completed.stdout)
        text = payload.get("result") or ""
        parsed = json.loads(text[text.find("{") : text.rfind("}") + 1])

        result = {k: parsed.get(k) for k in _SCHEMA_KEYS}
        if result.get("emotion_cd") not in EMOTION_CODES:
            result["emotion_cd"] = EMOTION_CODES[0]
        result["lang_cd"] = "ko"
        result["confidence"] = 0.85
        result["nsfw_score"] = float(result.get("nsfw_score") or 0.0)
        result["model_cd"] = self.model_cd
        # 밈 판별 (analysis 테이블 저장 대상 아님 — analyze 단계 필터용)
        result["is_meme"] = bool(parsed.get("is_meme", True))
        result["meme_score"] = float(parsed.get("meme_score") or (1.0 if result["is_meme"] else 0.0))
        result["tags"] = _normalize_tags(parsed.get("tags"))
        return result


_PROVIDERS: dict[str, VisionProvider] = {}


def get_vision_provider() -> VisionProvider:
    name = (settings.VISION_PROVIDER or "mock").lower()
    if name not in _PROVIDERS:
        if name == "anthropic":
            _PROVIDERS[name] = AnthropicVisionProvider()
        elif name == "claude_cli":
            _PROVIDERS[name] = ClaudeCliVisionProvider()
        else:
            _PROVIDERS[name] = MockVisionProvider()
    return _PROVIDERS[name]
