"""개발용 시드 — Pillow 로 데모 짤 40장 생성 → INBOX_DIR → 파이프라인 완주.

- 단색/그라데이션 배경 + 한글 문구 렌더. 파일명에 EMOTION/SITUATION 코드 인코딩
  (mock 비전이 파일명에서 감정/상황/캡션을 추출한다).
- 40장 중 앞 5장은 3프레임 애니 GIF(1초 루프) → 파이프라인에서 LOOP 로 처리.
- INBOX_DIR 에 배치한 뒤 crawl→...→publish 파이프라인을 실행한다.

실행: `python -m scripts.seed_dev`
"""
from __future__ import annotations

import logging
import os

from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import select

from src.config.database import SessionLocal
from src.config.settings import settings
from src.infrastructure.db.models.ingest import Source

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("shotpocket.seed")

# (문구, EMOTION_CD, SITUATION_CD). 앞 5개는 애니 GIF.
PHRASES: list[tuple[str, str, str]] = [
    ("퇴근하고싶다", "TIRED", "WORK"),
    ("월요일실화냐", "PANIC", "WORK"),
    ("현타온다", "DISGUST", "ETC"),
    ("배고파", "SADNESS", "FOOD"),
    ("주말어디갔어", "SADNESS", "ETC"),
    ("칼퇴각", "JOY", "WORK"),
    ("카페인수혈", "TIRED", "FOOD"),
    ("통장은텅장", "SADNESS", "MONEY"),
    ("로또돼라", "PROUD", "MONEY"),
    ("시험망함", "PANIC", "SCHOOL"),
    ("벼락치기", "PANIC", "SCHOOL"),
    ("게임한판더", "JOY", "GAME"),
    ("렉걸렸다", "ANGER", "GAME"),
    ("다이어트내일부터", "AWKWARD", "EXERCISE"),
    ("헬스등록만함", "AWKWARD", "EXERCISE"),
    ("비온다우산없다", "SADNESS", "WEATHER"),
    ("폭염주의", "TIRED", "WEATHER"),
    ("첫눈온다", "LOVE", "WEATHER"),
    ("썸타는중", "LOVE", "LOVE"),
    ("고백실패", "SADNESS", "LOVE"),
    ("친구가밥산대", "JOY", "FRIEND"),
    ("손절각", "ANGER", "FRIEND"),
    ("상사가불렀다", "PANIC", "WORK"),
    ("야근확정", "TIRED", "WORK"),
    ("월급날", "JOY", "MONEY"),
    ("카드값폭탄", "PANIC", "MONEY"),
    ("치킨시켰다", "JOY", "FOOD"),
    ("다이어트실패", "DISGUST", "FOOD"),
    ("알람못들음", "PANIC", "ETC"),
    ("지각각", "PANIC", "SCHOOL"),
    ("과제폭탄", "TIRED", "SCHOOL"),
    ("방학끝나감", "SADNESS", "SCHOOL"),
    ("운동가기싫다", "TIRED", "EXERCISE"),
    ("근육통", "TIRED", "EXERCISE"),
    ("소개팅망함", "AWKWARD", "LOVE"),
    ("심쿵주의", "LOVE", "LOVE"),
    ("친구결혼소식", "SURPRISE", "FRIEND"),
    ("회식싫다", "DISGUST", "WORK"),
    ("보너스나옴", "PROUD", "MONEY"),
    ("날씨좋다", "JOY", "WEATHER"),
]

_ANIMATED_COUNT = 5
_SIZE = 800

_FONT_CANDIDATES = [
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
    "/Library/Fonts/AppleGothic.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
]


def _find_font(size: int) -> ImageFont.FreeTypeFont:
    for path in _FONT_CANDIDATES:
        if os.path.isfile(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:  # noqa: BLE001
                continue
    logger.warning("한글 폰트 미발견 — 기본 폰트 사용(문구 렌더 품질 저하)")
    return ImageFont.load_default()


def _bg_color(idx: int) -> tuple[int, int, int]:
    r = (idx * 53 + 40) % 200 + 30
    g = (idx * 97 + 80) % 200 + 30
    b = (idx * 131 + 20) % 200 + 30
    return (r, g, b)


def _text_color(bg: tuple[int, int, int]) -> tuple[int, int, int]:
    lum = 0.299 * bg[0] + 0.587 * bg[1] + 0.114 * bg[2]
    return (30, 30, 30) if lum > 140 else (250, 250, 250)


def _gradient(idx: int) -> Image.Image:
    top = _bg_color(idx)
    bottom = _bg_color(idx + 7)
    img = Image.new("RGB", (_SIZE, _SIZE), top)
    draw = ImageDraw.Draw(img)
    for y in range(_SIZE):
        t = y / _SIZE
        col = tuple(int(top[c] * (1 - t) + bottom[c] * t) for c in range(3))
        draw.line([(0, y), (_SIZE, y)], fill=col)
    return img


def _draw_text(img: Image.Image, text: str, font: ImageFont.FreeTypeFont) -> None:
    draw = ImageDraw.Draw(img)
    bbox = draw.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (_SIZE - w) / 2 - bbox[0]
    y = (_SIZE - h) / 2 - bbox[1]
    # 배경 평균으로 대비색 결정
    color = _text_color(img.getpixel((_SIZE // 2, _SIZE // 2)))
    draw.text((x, y), text, font=font, fill=color)


def _render_still(idx: int, text: str, font, path: str) -> None:
    img = _gradient(idx) if idx % 2 == 0 else Image.new("RGB", (_SIZE, _SIZE), _bg_color(idx))
    _draw_text(img, text, font)
    img.save(path, format="PNG")


def _render_gif(idx: int, text: str, font, path: str) -> None:
    frames = []
    for f in range(3):
        img = Image.new("RGB", (_SIZE, _SIZE), _bg_color(idx + f * 3))
        _draw_text(img, text, font)
        frames.append(img)
    frames[0].save(
        path,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=333,  # 3프레임 * 333ms ≈ 1초 루프
        loop=0,
    )


def generate_images() -> int:
    inbox = settings.INBOX_DIR
    os.makedirs(inbox, exist_ok=True)
    font = _find_font(96)
    for i, (phrase, emotion, situation) in enumerate(PHRASES):
        animated = i < _ANIMATED_COUNT
        ext = "gif" if animated else "png"
        fname = f"{i:03d}_{phrase}_{emotion}_{situation}.{ext}"
        path = os.path.join(inbox, fname)
        if animated:
            _render_gif(i, phrase, font, path)
        else:
            _render_still(i, phrase, font, path)
    logger.info("생성 %d장 → %s (애니 %d장)", len(PHRASES), inbox, _ANIMATED_COUNT)
    return len(PHRASES)


def ensure_local_source() -> None:
    db = SessionLocal()
    try:
        exists = db.execute(
            select(Source).where(Source.source_type_cd == "LOCAL")
        ).scalar_one_or_none()
        if exists is None:
            db.add(
                Source(
                    name="local-inbox",
                    base_url=settings.INBOX_DIR,
                    source_type_cd="LOCAL",
                    priority=10,
                    enabled_yn=True,
                )
            )
            db.commit()
            logger.info("LOCAL 소스 생성 (base_url=%s)", settings.INBOX_DIR)
        else:
            logger.info("LOCAL 소스 이미 존재")
    finally:
        db.close()


def main() -> None:
    generate_images()
    ensure_local_source()
    # 파이프라인 완주
    from scripts.run_pipeline import run_once

    counts = run_once()
    print("SEED_PIPELINE_RESULT", counts)


if __name__ == "__main__":
    main()
