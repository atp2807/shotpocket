"""임베딩 스텁 — 인터페이스만.

EMBEDDING_MODEL=bge-m3, 차원 1024. 실제 모델 로딩/추론은 추후 연결.
검색·의미유사 파이프라인은 이 인터페이스에만 의존한다(교체 용이).
"""
from __future__ import annotations

from src.config.settings import settings

EMBEDDING_DIM = 1024


class Embedder:
    """텍스트 → 1024차원 벡터. (스텁: 0벡터 반환)"""

    def __init__(self) -> None:
        self.model_cd = settings.EMBEDDING_MODEL
        self.dim = EMBEDDING_DIM

    def embed_text(self, text: str) -> list[float]:
        """단일 텍스트 임베딩. 실제 구현 시 bge-m3 추론 결과를 반환."""
        # placeholder: 실제 벡터 대신 0벡터. 검색 서비스는 이 스텁일 때
        #             pgvector 유사도 대신 rank_score 폴백을 사용한다.
        return [0.0] * self.dim

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """배치 임베딩."""
        return [self.embed_text(t) for t in texts]


embedder = Embedder()
