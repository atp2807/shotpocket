"""나무위키(namu.wiki) 밈 문서 크롤 어댑터.

소스: `분류:인터넷 밈` 카테고리 페이지(base_url) → 소속 밈 문서들.
문서: 개별 문서(/w/<제목>) `<head>` 의 og 메타태그만 취한다.
  - og:title  → 정확한 밈 이름(meme_name). 게시 단계에서 vision 추측을 덮어쓴다.
  - og:image  → 대표 이미지(//i.namu.wiki/... → https: 붙여 다운로드).
  - og:description 은 절대 사용/저장하지 않는다(문서 텍스트 CC BY-NC-SA 비영리 라이선스).
origin_url = 문서 URL(https://namu.wiki/w/<인코딩된 제목>).

robots.txt 실측: `/w/`(개별 문서)·`/Search` 만 Allow, 그 외 Disallow. 카테고리 페이지와
개별 문서는 모두 /w/ 경로라 UA 무관 규칙상 허용된다(BaseWebAdapter 가 can_fetch 로 재확인).

구조 근거(실측):
- 카테고리 멤버 목록은 `ul > li > a[href^="/w/"]` 로 서버 렌더링된다(JS 불필요). 이 중
  디코딩한 제목이 "분류:" 로 시작하면 하위 카테고리, 아니면 실제 밈 문서다.
- 페이지네이션 없음: 현재 카테고리는 멤버 전체(≈90건)를 한 페이지에 렌더링하며
  `from=`/`until=`/커서/"다음 페이지" 앵커가 HTML 에 존재하지 않는다. 따라서 현재
  페이지 항목만 대상으로 한다(향후 커서가 생기면 list_urls 확장 지점).
- og:image 없는(이미지 없는 순수 텍스트) 문서는 스킵한다.
"""
from __future__ import annotations

import logging
from urllib.parse import unquote, urljoin

from bs4 import BeautifulSoup

from src.features.ingest.infrastructure.source_adapters._web import (
    BaseWebAdapter,
    CrawlSession,
    download_image,
)

logger = logging.getLogger("shotpocket.ingest.adapter")

_ORIGIN = "https://namu.wiki"
_DOC_PREFIX = "/w/"
_CATEGORY_PREFIX = "분류:"  # 디코딩된 제목 기준 하위 카테고리 표식
_CDN_PREFIX = "//i.namu.wiki/"  # 실제 대표 이미지 CDN(그 외 og:image 는 기본 아이콘 폴백)

# 나무위키 og:image 는 CDN 리사이즈 썸네일(대개 소용량 webp) — 포럼 원본용 임계(20KB/200px)
# 를 낮춰 받는다. svg/기본아이콘은 CDN 필터·PIL 포맷 필터로 자연 배제된다. 한 변 100px 미만
# (파비콘·소형 로고 티어)만 최소 방어로 제외.
_NAMU_MIN_BYTES = 0
_NAMU_MIN_SIDE = 100


class NamuwikiAdapter(BaseWebAdapter):
    """나무위키 밈 카테고리 크롤 어댑터.

    source_type_cd="NAMUWIKI" 는 레지스트리 키이자 payload.src_cd(→ meme.source_cd) 값이다.
    한 문서당 대표 이미지(og:image) 1장만 취한다.
    """

    source_type_cd = "NAMUWIKI"
    max_images_per_post = 1

    def list_urls(self, base_url: str) -> list[str]:
        # 페이지네이션 없음(실측) — 카테고리 페이지 1장만.
        return [base_url]

    def parse_post_links(self, html: str, list_url: str) -> list[str]:
        """카테고리 멤버 목록에서 실제 밈 문서 URL 만 추출(하위 카테고리 제외)."""
        soup = BeautifulSoup(html, "html.parser")
        out: list[str] = []
        seen: set[str] = set()
        for li in soup.select("ul > li"):
            a = li.find("a", href=True)
            if a is None:
                continue
            href = a["href"]
            if not href.startswith(_DOC_PREFIX):
                continue
            title = unquote(href[len(_DOC_PREFIX):])
            if title.startswith(_CATEGORY_PREFIX):  # 하위 카테고리 — 문서 아님
                continue
            abs_url = urljoin(_ORIGIN, href)
            if abs_url in seen:
                continue
            seen.add(abs_url)
            out.append(abs_url)
        return out

    def parse_image_urls(self, html: str, post_url: str) -> list[str]:
        """대표 이미지(og:image) 만 반환. 실제 수집은 _fetch_post 가 담당(og:title 병취)."""
        url = self._og(BeautifulSoup(html, "html.parser"), "og:image")
        if not url or not url.startswith(_CDN_PREFIX):
            return []
        return [self._abs_image(url)]

    def image_referer(self, post_url: str) -> str | None:
        # i.namu.wiki CDN 은 referer 불필요(실측: 200 OK).
        return None

    def _fetch_post(self, session: CrawlSession, post_url: str) -> list[dict]:
        """문서 fetch → og:title/og:image 파싱 → 이미지 다운로드 → 후보 1건.

        og:image 없으면 스킵. payload 에 namuwiki_meme_name(og:title) 을 실어
        게시 단계에서 analysis.meme_name 을 이 값으로 덮어쓰게 한다.
        og:description 은 파싱조차 하지 않는다(라이선스 규약).
        """
        resp = session.get(post_url)
        if resp.status_code != 200:
            logger.info("문서 응답 비정상 %s status=%s", post_url, resp.status_code)
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        og_title = self._og(soup, "og:title")
        og_image = self._og(soup, "og:image")
        # CDN(//i.namu.wiki/) 이미지가 아니면 대표 이미지 없음(기본 아이콘 폴백) → 스킵.
        if not og_image or not og_image.startswith(_CDN_PREFIX):
            logger.info("대표 이미지(og:image CDN) 없음 — 문서 스킵: %s", post_url)
            return []

        img_url = self._abs_image(og_image)
        piece = download_image(
            session,
            img_url,
            referer=self.image_referer(post_url),
            min_bytes=_NAMU_MIN_BYTES,
            min_side=_NAMU_MIN_SIDE,
        )
        if piece is None:
            return []
        piece["src_cd"] = self.source_type_cd
        if og_title:
            # 게시 단계에서 이 값이 있으면 meme_name 을 우선한다(vision 추측보다 신뢰).
            piece["namuwiki_meme_name"] = og_title
        return [{"origin_url": post_url, "phash": None, "payload": piece}]

    @staticmethod
    def _og(soup: BeautifulSoup, prop: str) -> str | None:
        tag = soup.find("meta", attrs={"property": prop})
        if tag is None:
            return None
        content = tag.get("content")
        return content.strip() if content else None

    @staticmethod
    def _abs_image(url: str) -> str:
        # og:image 는 프로토콜 없는 //i.namu.wiki/... 형태 → https: 부여.
        if url.startswith("//"):
            return "https:" + url
        return url
