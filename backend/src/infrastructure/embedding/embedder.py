"""임베딩 공급자 — 텍스트 → 384차원 dense 벡터.

- EmbeddingProvider: 인터페이스 (embed_query / embed_passage / embed_text / embed_texts)
- MockEmbeddingProvider: sha256 시드 기반 결정적 단위벡터 (모델/네트워크 불필요)
- FastembedProvider: fastembed 'intfloat/multilingual-e5-small' (384d), lazy 싱글톤

프로덕션 RAM 1.8GB 제약으로 경량 e5-small(≈200MB) 채택. e5 계열은 관례상
쿼리에 'query: ', 문서에 'passage: ' 프리픽스를 붙여야 검색 성능이 나온다 —
embed_query/embed_passage 로 구분 처리한다. 검색은 embed_query, 수집 임베딩은
embed_passage 를 사용한다. embed_text 는 embed_passage 별칭(하위호환).
공급자 선택은 settings.EMBEDDING_PROVIDER (fastembed|mock, 기본 mock).
"""
from __future__ import annotations

import hashlib
import logging
import math
import random
from typing import Protocol

from src.config.settings import settings

logger = logging.getLogger("shotpocket.embedding")

EMBEDDING_DIM = 384
_QUERY_PREFIX = "query: "
_PASSAGE_PREFIX = "passage: "


class EmbeddingProvider(Protocol):
    model_cd: str
    dim: int

    def embed_query(self, text: str) -> list[float]: ...

    def embed_passage(self, text: str) -> list[float]: ...

    def embed_text(self, text: str) -> list[float]: ...

    def embed_texts(self, texts: list[str]) -> list[list[float]]: ...


def _unit_normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0.0:
        return vec
    return [v / norm for v in vec]


class MockEmbeddingProvider:
    """결정적 mock 임베딩(384d).

    같은 입력 → 같은 벡터. sha256(text) 를 시드로 rng 를 초기화해 성분을 뽑고 단위
    정규화한다. e5 프리픽스도 그대로 반영(query/passage 는 다른 벡터가 된다).
    의미 유사도는 없지만 벡터 파이프라인(pgvector 저장/코사인/차원 검증)을 실제로
    구동·검증할 수 있다.
    """

    model_cd = "mock-e5-384"
    dim = EMBEDDING_DIM

    def _embed(self, text: str) -> list[float]:
        seed = int.from_bytes(
            hashlib.sha256((text or "").encode("utf-8")).digest()[:8], "big"
        )
        rng = random.Random(seed)
        vec = [rng.gauss(0.0, 1.0) for _ in range(self.dim)]
        return _unit_normalize(vec)

    def embed_query(self, text: str) -> list[float]:
        return self._embed(_QUERY_PREFIX + (text or ""))

    def embed_passage(self, text: str) -> list[float]:
        return self._embed(_PASSAGE_PREFIX + (text or ""))

    def embed_text(self, text: str) -> list[float]:
        return self.embed_passage(text)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_passage(t) for t in texts]


class FastembedProvider:
    """fastembed ONNX 임베딩 (settings.EMBEDDING_MODEL, 384d). lazy 싱글톤 로딩.

    기본 모델: paraphrase-multilingual-MiniLM-L12-v2 (e5-small은 fastembed
    registry 미지원). query:/passage: 프리픽스는 e5 계열 모델일 때만 적용.
    """

    dim = EMBEDDING_DIM

    def __init__(self) -> None:
        self._model = None
        self.model_cd = settings.EMBEDDING_MODEL
        self._use_e5_prefix = "e5" in self.model_cd.lower()

    def _ensure_model(self):
        if self._model is None:
            from fastembed import TextEmbedding  # 지연 import (미설치 환경 보호)

            logger.info("loading fastembed model=%s", self.model_cd)
            self._model = TextEmbedding(model_name=self.model_cd)
        return self._model

    def _embed_prefixed(self, texts: list[str]) -> list[list[float]]:
        model = self._ensure_model()
        return [list(map(float, v)) for v in model.embed(list(texts))]

    def _prefix(self, text: str, prefix: str) -> str:
        return (prefix + (text or "")) if self._use_e5_prefix else (text or "")

    def embed_query(self, text: str) -> list[float]:
        return self._embed_prefixed([self._prefix(text, _QUERY_PREFIX)])[0]

    def embed_passage(self, text: str) -> list[float]:
        return self._embed_prefixed([self._prefix(text, _PASSAGE_PREFIX)])[0]

    def embed_text(self, text: str) -> list[float]:
        return self.embed_passage(text)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return self._embed_prefixed([self._prefix(t, _PASSAGE_PREFIX) for t in texts])


_PROVIDERS: dict[str, EmbeddingProvider] = {}


def get_embedder() -> EmbeddingProvider:
    """settings.EMBEDDING_PROVIDER 에 따른 공급자 싱글톤."""
    name = (settings.EMBEDDING_PROVIDER or "mock").lower()
    if name not in _PROVIDERS:
        if name == "fastembed":
            try:
                _PROVIDERS[name] = FastembedProvider()
            except Exception:  # noqa: BLE001 — 미설치 시 mock 폴백
                logger.warning("fastembed 초기화 실패 → mock 폴백")
                _PROVIDERS[name] = MockEmbeddingProvider()
        else:
            _PROVIDERS[name] = MockEmbeddingProvider()
    return _PROVIDERS[name]


# 하위호환 별칭 (기존 참조). model_cd/embed_text/embed_texts 제공.
embedder = get_embedder()
