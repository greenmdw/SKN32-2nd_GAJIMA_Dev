# -*- coding: utf-8 -*-
"""interfaces/http — health(인증 불필요). 봉투 적용(19-4 §6)."""
from fastapi import APIRouter
from app.interfaces.http.responses import ok
from app.infrastructure.files import artifact_store as art
from app.infrastructure.mysql.session import mode

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    return ok({"eval": art.eval_exists(), "db_mode": mode(), "server": "fastapi"})
