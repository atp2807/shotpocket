"""루리웹 유머 베스트 크롤 어댑터.

목록: 유머 베스트(https://bbs.ruliweb.com/best/humor) 최근 1~2페이지.
글: 본문 컨테이너(.view_content)의 img 추출.
origin_url = 글 URL(정규화: PC판 /best/board/{id}/read/{no}).

셀렉터 근거(실측): 목록의 글 링크는 a[href*='/best/board/{id}/read/{no}'] (모바일
m.ruliweb.com 도메인으로 오는 경우가 있어 PC bbs.ruliweb.com 으로 정규화). 본문
이미지는 .view_content img 의 src=https://i*.ruliweb.com/img/... 형태.
"""
from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from src.features.ingest.infrastructure.source_adapters._web import BaseWebAdapter

# /best/board/300143/read/75806551 형태에서 board id 와 글번호 추출
_READ_RE = re.compile(r"/best/board/(\d+)/read/(\d+)")


class RuliwebAdapter(BaseWebAdapter):
    source_type_cd = "RULIWEB"

    def list_urls(self, base_url: str) -> list[str]:
        sep = "&" if "?" in base_url else "?"
        return [base_url, f"{base_url}{sep}page=2"]

    def parse_post_links(self, html: str, list_url: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        out: list[str] = []
        for a in soup.select("a[href*='/read/']"):
            m = _READ_RE.search(a["href"])
            if not m:
                continue
            board, no = m.group(1), m.group(2)
            out.append(f"https://bbs.ruliweb.com/best/board/{board}/read/{no}")
        return out

    def parse_image_urls(self, html: str, post_url: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        container = soup.select_one(".view_content")
        if container is None:
            return []
        out: list[str] = []
        seen: set[str] = set()
        for img in container.find_all("img"):
            url = img.get("src") or img.get("data-src")
            if not url:
                continue
            url = urljoin(post_url, url)
            if not url.startswith("http"):  # data: URI 등 제외
                continue
            if url in seen:
                continue
            seen.add(url)
            out.append(url)
        return out
