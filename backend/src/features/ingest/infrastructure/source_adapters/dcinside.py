"""디시인사이드 힛갤 크롤 어댑터.

목록: 힛갤(https://gall.dcinside.com/board/lists/?id=hit) 최근 1~2페이지.
글: 본문 컨테이너(.write_div)의 img 중 viewimage.php 원본만 추출.
     lazy-load 이미지는 실제 원본이 data-original 에 있고 src 는 로딩 gif 이므로
     data-original 우선. 이미지 다운로드 시 Referer=글 URL 필수(없으면 차단 위험).
origin_url = 글 URL(정규화: id=hit&no=... 만 유지).

셀렉터 근거(실측): 목록은 td.gall_tit a[href*='/board/view/'], 본문 이미지는
.write_div img 의 src=https://dcimg*.dcinside.com/viewimage.php?... (또는 data-original).
"""
from __future__ import annotations

from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup

from src.features.ingest.infrastructure.source_adapters._web import BaseWebAdapter

_VIEW_BASE = "https://gall.dcinside.com/board/view/"


class DcinsideAdapter(BaseWebAdapter):
    source_type_cd = "DCINSIDE"

    def list_urls(self, base_url: str) -> list[str]:
        sep = "&" if "?" in base_url else "?"
        # 1페이지(base 그대로) + 2페이지
        return [base_url, f"{base_url}{sep}page=2"]

    def parse_post_links(self, html: str, list_url: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        out: list[str] = []
        for a in soup.select("td.gall_tit a[href]"):
            href = a["href"]
            if "/board/view/" not in href or "no=" not in href:
                continue
            if "t=cv" in href:  # 댓글보기 링크(reply_numbox) 제외
                continue
            abs_url = urljoin(list_url, href)
            q = parse_qs(urlparse(abs_url).query)
            gid = (q.get("id") or [None])[0]
            no = (q.get("no") or [None])[0]
            if not gid or not no:
                continue
            out.append(f"{_VIEW_BASE}?id={gid}&no={no}")
        return out

    def parse_image_urls(self, html: str, post_url: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        container = soup.select_one(".write_div") or soup.select_one(".writing_view_box")
        if container is None:
            return []
        out: list[str] = []
        seen: set[str] = set()
        for img in container.find_all("img"):
            # lazy-load: 원본은 data-original, src 는 로딩 gif 인 경우가 있음
            url = img.get("data-original") or img.get("src")
            if not url:
                continue
            url = urljoin(post_url, url)
            if "viewimage.php" not in url:  # 본문 원본 이미지만
                continue
            if url in seen:
                continue
            seen.add(url)
            out.append(url)
        return out
