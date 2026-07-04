"""웹 크롤 어댑터 공통 유틸 — 매너 준수(스로틀·robots·UA), 이미지 다운로드/필터.

크롤 매너(협상 불가):
- 요청 간격: 소스당 2~3초(jitter). 단일 스레드 순차 요청(동시 요청 금지).
- User-Agent 명시.
- robots.txt: 대상 경로가 Disallow면 스킵 + 경고 로그.
- 회당 수집 상한/글당 이미지 상한.
- 실패 격리: 글 1개 실패가 전체 크롤을 죽이지 않음(호출부 try/except).

수집은 '다운로드 + 후보 dict 생성'까지만 담당한다. dedup(pHash)/analyze/transcode
등 필터·변환은 후속 파이프라인 단계가 처리한다.
"""
from __future__ import annotations

import io
import logging
import os
import random
import time
import uuid
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
from PIL import Image

from src.config.settings import settings

logger = logging.getLogger("shotpocket.ingest.adapter")

USER_AGENT = "ShotPocketBot/0.1 (+https://shotpocket.sitos.me)"

# 수집 허용 이미지 포맷(영상 수집 금지 정책 → PIL 포맷 기준으로 필터).
_PIL_FMT_TO_EXT = {"PNG": "png", "JPEG": "jpg", "WEBP": "webp", "GIF": "gif"}

# 소형 이미지(프사/아이콘/광고) 제외 임계치.
_MIN_BYTES = 20 * 1024
_MIN_SIDE = 200

# 요청 간격(초) — 소스당 2~3초 jitter.
_DELAY_MIN = 2.0
_DELAY_MAX = 3.0


def _apply_longest_match(rp: RobotFileParser) -> None:
    """RobotFileParser 의 first-match 평가를 longest-match(RFC 9309/Google)로 보정.

    파이썬 표준 파서는 각 그룹의 룰을 '파일 순서 첫 매치'로 판정한다. 그래서
    `Disallow: /` 가 `Allow: /w/` 앞에 오면(namu.wiki 등) 더 구체적인 Allow 에 닿기 전에
    전 경로가 막힌다. 실제 크롤러는 '가장 긴(구체적인) 경로 우선, 동률이면 Allow 우선'을
    쓴다. 각 엔트리의 rulelines 를 그 순서로 재정렬하면 first-match=longest-match 가 된다.
    """
    entries = list(getattr(rp, "entries", []) or [])
    if getattr(rp, "default_entry", None) is not None:
        entries.append(rp.default_entry)
    for entry in entries:
        rulelines = getattr(entry, "rulelines", None)
        if not rulelines:
            continue
        # 긴 path 우선, 동률이면 Allow(allowance=True) 우선.
        rulelines.sort(key=lambda rl: (len(rl.path), rl.allowance), reverse=True)


class CrawlSession:
    """스로틀 httpx 클라이언트 + robots 판정. 소스 1개당 1인스턴스, 순차 사용."""

    def __init__(self) -> None:
        self._client = httpx.Client(
            headers={
                "User-Agent": USER_AGENT,
                "Accept-Language": "ko-KR,ko;q=0.9",
            },
            timeout=25.0,
            follow_redirects=True,
        )
        self._first = True
        self._robots: dict[str, RobotFileParser | None] = {}

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "CrawlSession":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _throttle(self) -> None:
        if self._first:
            self._first = False
            return
        time.sleep(random.uniform(_DELAY_MIN, _DELAY_MAX))

    def get(self, url: str, referer: str | None = None) -> httpx.Response:
        """스로틀 후 GET. 호출부가 상태코드/예외를 처리한다."""
        self._throttle()
        headers = {"Referer": referer} if referer else None
        return self._client.get(url, headers=headers)

    def _robots_for(self, url: str) -> RobotFileParser | None:
        parsed = urlparse(url)
        host = f"{parsed.scheme}://{parsed.netloc}"
        if host in self._robots:
            return self._robots[host]
        rp = RobotFileParser()
        rp.set_url(f"{host}/robots.txt")
        # RobotFileParser.read() 는 urllib 기본 UA 로 fetch 하는데, 일부 사이트(예: namu.wiki)는
        # 그 UA 에 403 을 주고 이때 disallow_all 이 켜져 전 경로가 차단된다. 우리 실제 UA(httpx
        # self._client)로 직접 받아 parse() 에 넘겨 이 오탐을 막는다(비200/실패는 허용 취급).
        try:
            resp = self._client.get(f"{host}/robots.txt")
            if resp.status_code != 200:
                logger.warning(
                    "robots.txt 응답 비정상(%s status=%s) — 허용으로 진행", host, resp.status_code
                )
                self._robots[host] = None
                return None
            rp.parse(resp.text.splitlines())
            _apply_longest_match(rp)
        except Exception as exc:  # noqa: BLE001 — robots 못 읽으면 보수적으로 허용 취급
            logger.warning("robots.txt 읽기 실패(%s): %s — 허용으로 진행", host, exc)
            self._robots[host] = None
            return None
        self._robots[host] = rp
        return rp

    def can_fetch(self, url: str) -> bool:
        rp = self._robots_for(url)
        if rp is None:
            return True
        return rp.can_fetch(USER_AGENT, url)


def download_image(
    session: CrawlSession,
    url: str,
    referer: str | None = None,
    *,
    min_bytes: int = _MIN_BYTES,
    min_side: int = _MIN_SIDE,
) -> dict | None:
    """이미지 1장 다운로드 + 필터 통과 시 WORK_DIR 저장 → 후보 payload 조각 반환.

    필터: 확장자 png/jpg/jpeg/webp/gif 외(PIL 포맷 기준) 제외, min_bytes 미만 제외,
    한 변 min_side px 미만 제외. 통과 실패/에러는 None(호출부에서 스킵).

    min_bytes/min_side 기본값은 포럼 원본(아이콘·광고 배제) 기준. 나무위키처럼 대표
    이미지가 CDN 리사이즈 썸네일(소용량 webp)인 소스는 이 임계를 낮춰 호출한다.
    """
    try:
        resp = session.get(url, referer=referer)
    except Exception as exc:  # noqa: BLE001
        logger.warning("이미지 다운로드 실패 %s: %s", url, exc)
        return None
    if resp.status_code != 200:
        logger.info("이미지 응답 비정상 %s status=%s", url, resp.status_code)
        return None

    data = resp.content
    if len(data) < min_bytes:
        logger.debug("소형 이미지 제외(<%dB, %dB) %s", min_bytes, len(data), url)
        return None

    try:
        with Image.open(io.BytesIO(data)) as im:
            fmt = im.format or ""
            width, height = im.size
    except Exception as exc:  # noqa: BLE001 — 이미지 아님/손상 → 제외
        logger.debug("이미지 파싱 실패(제외) %s: %s", url, exc)
        return None

    ext = _PIL_FMT_TO_EXT.get(fmt)
    if ext is None:
        logger.debug("미지원 포맷 제외 fmt=%s %s", fmt, url)
        return None
    if min(width, height) < min_side:
        logger.debug("소형 이미지 제외(<%dpx, %dx%d) %s", min_side, width, height, url)
        return None

    work_dir = settings.WORK_DIR
    os.makedirs(work_dir, exist_ok=True)
    work_path = os.path.join(work_dir, f"{uuid.uuid4().hex}.{ext}")
    with open(work_path, "wb") as f:
        f.write(data)

    orig_name = os.path.basename(urlparse(url).path) or f"image.{ext}"
    return {
        "file_path": work_path,
        "orig_filename": orig_name,
        "ext": ext,
        "source_url": url,
        "bytes": len(data),
        "width": width,
        "height": height,
    }


class BaseWebAdapter:
    """실크롤 어댑터 베이스.

    서브클래스가 구현:
      - source_type_cd: str
      - list_urls(base_url) -> list[str]     (최근 1~2페이지 목록 URL)
      - parse_post_links(html, list_url) -> list[str]   (글 URL, 순서 보존)
      - parse_image_urls(html, post_url) -> list[str]   (본문 이미지 URL 후보)
      - image_referer(post_url) -> str | None           (이미지 다운로드 Referer)
    """

    source_type_cd: str = ""
    max_images_per_post: int = 5

    def list_urls(self, base_url: str) -> list[str]:  # pragma: no cover - 추상
        raise NotImplementedError

    def parse_post_links(self, html: str, list_url: str) -> list[str]:  # pragma: no cover
        raise NotImplementedError

    def parse_image_urls(self, html: str, post_url: str) -> list[str]:  # pragma: no cover
        raise NotImplementedError

    def image_referer(self, post_url: str) -> str | None:
        return post_url

    def fetch(
        self,
        base_url: str,
        *,
        limit: int = 30,
        is_seen=None,
    ) -> list[dict]:
        """목록 → 글 → 본문 이미지 수집. limit=글 상한, is_seen(origin_url)->bool 중복 스킵."""
        if not base_url:
            logger.warning("%s: base_url 미설정 — 스킵", self.source_type_cd)
            return []

        session = CrawlSession()
        candidates: list[dict] = []
        try:
            if not session.can_fetch(base_url):
                logger.warning(
                    "robots.txt Disallow — 소스 스킵: %s (UA=%s)", base_url, USER_AGENT
                )
                return []

            # 1) 목록 페이지들에서 글 URL 수집(순서 보존 + 전역 dedup)
            post_urls: list[str] = []
            seen_urls: set[str] = set()
            for list_url in self.list_urls(base_url):
                if not session.can_fetch(list_url):
                    logger.warning("robots Disallow 목록 스킵: %s", list_url)
                    continue
                try:
                    resp = session.get(list_url)
                    if resp.status_code != 200:
                        logger.warning("목록 응답 비정상 %s status=%s", list_url, resp.status_code)
                        continue
                    for purl in self.parse_post_links(resp.text, list_url):
                        if purl not in seen_urls:
                            seen_urls.add(purl)
                            post_urls.append(purl)
                except Exception as exc:  # noqa: BLE001 — 목록 1개 실패 격리
                    logger.warning("목록 수집 실패 %s: %s", list_url, exc)

            logger.info("%s: 목록에서 글 %d개 수집(상한 %d)", self.source_type_cd, len(post_urls), limit)

            # 2) 글 단위 수집(상한/중복/robots/실패격리)
            # 상한(limit)은 '검토한 글' 기준 — 중복 스킵된 글도 상한에 포함한다.
            # (재실행 시 목록 상단이 전부 기존 글이면 신규 0건으로 끝나야 하고,
            #  목록을 더 깊이 파고들며 요청을 늘리지 않는다 — 야간 배치 매너)
            for post_url in post_urls[:limit]:
                if is_seen is not None and is_seen(post_url):
                    logger.info("중복 스킵(origin_url 기존): %s", post_url)
                    continue
                if not session.can_fetch(post_url):
                    logger.warning("robots Disallow 글 스킵: %s", post_url)
                    continue
                try:
                    got = self._fetch_post(session, post_url)
                except Exception as exc:  # noqa: BLE001 — 글 1개 실패가 전체를 죽이지 않음
                    logger.warning("글 수집 실패 %s: %s", post_url, exc)
                    continue
                if got:
                    candidates.extend(got)
        finally:
            session.close()

        logger.info(
            "%s: 수집 완료 — 글 %d, 이미지후보 %d",
            self.source_type_cd,
            len({c["origin_url"] for c in candidates}),
            len(candidates),
        )
        return candidates

    def _fetch_post(self, session: CrawlSession, post_url: str) -> list[dict]:
        resp = session.get(post_url)
        if resp.status_code != 200:
            logger.info("글 응답 비정상 %s status=%s", post_url, resp.status_code)
            return []
        img_urls = self.parse_image_urls(resp.text, post_url)
        referer = self.image_referer(post_url)
        out: list[dict] = []
        for img_url in img_urls:
            if len(out) >= self.max_images_per_post:
                break
            piece = download_image(session, img_url, referer=referer)
            if piece is None:
                continue
            piece["src_cd"] = self.source_type_cd
            out.append(
                {
                    "origin_url": post_url,
                    "phash": None,  # phash 는 dedup 단계에서 계산
                    "payload": piece,
                }
            )
        return out
