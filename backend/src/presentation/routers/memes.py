"""memes 라우터 — 공개(인증 없음)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.features.engage.application.engage_service import EngageService
from src.features.meme.application.meme_service import MemeService
from src.features.meme.infrastructure.meme_repo import load_meme_extras
from src.presentation.deps import get_ip_hash
from src.presentation.schemas.meme.meme_schema import (
    EngageResponse,
    MemeResponse,
    MemeSummary,
    SimilarResponse,
)

router = APIRouter(prefix="/api/memes", tags=["memes"])


@router.get("/{meme_id}", response_model=MemeResponse)
def get_meme(meme_id: uuid.UUID, db: Session = Depends(get_db)) -> MemeResponse:
    meme = MemeService(db).get_meme(meme_id)
    extras = load_meme_extras(db, [meme.id])
    return MemeResponse.from_meme(meme, extras.get(meme.id))


@router.get("/{meme_id}/similar", response_model=SimilarResponse)
def get_similar(meme_id: uuid.UUID, db: Session = Depends(get_db)) -> SimilarResponse:
    memes = MemeService(db).list_similar(meme_id)
    extras = load_meme_extras(db, [m.id for m in memes])  # 1회 일괄 로드 (N+1 금지)
    items = [MemeSummary.from_meme(m, extras.get(m.id)) for m in memes]
    return SimilarResponse(items=items, total=len(items))


@router.post("/{meme_id}/likes", response_model=EngageResponse)
def create_like(
    meme_id: uuid.UUID, request: Request, db: Session = Depends(get_db)
) -> EngageResponse:
    like_cnt = EngageService(db).like(meme_id, ip_hash=get_ip_hash(request))
    return EngageResponse(meme_id=meme_id, like_cnt=like_cnt)


@router.post("/{meme_id}/downloads", response_model=EngageResponse)
def create_download(
    meme_id: uuid.UUID, request: Request, db: Session = Depends(get_db)
) -> EngageResponse:
    download_cnt, download_url = EngageService(db).download(
        meme_id, ip_hash=get_ip_hash(request)
    )
    return EngageResponse(
        meme_id=meme_id, download_cnt=download_cnt, download_url=download_url
    )
