# -*- coding: utf-8 -*-
"""interfaces/http — health(인증 불필요). 봉투 적용(19-4 §6)."""
from fastapi import APIRouter
from app.interfaces.http.responses import ok
from app.infrastructure.files import artifact_store as art
from app.infrastructure.mysql.session import mode
from app.config import NEON_URL

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    # neon: 시뮬 이벤트 영속(B 모드) 가능 여부. 시뮬 사이트가 이벤트 흐름 모드(B/A)를 자동 선택하는 데 사용.
    return ok({"eval": art.eval_exists(), "db_mode": mode(),
               "neon": bool(NEON_URL), "server": "fastapi"})
