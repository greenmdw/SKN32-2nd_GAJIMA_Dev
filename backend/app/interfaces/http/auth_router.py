# -*- coding: utf-8 -*-
"""interfaces/http — 얼굴 인증(19-4 §5·§7.1). 봉투 적용. 대시보드는 /auth/* 만 호출."""
from fastapi import APIRouter, Depends, Query
from app.interfaces.http.deps import require_api_key, unwrap
from app.interfaces.http.responses import ok
from app.schemas.auth_schema import FaceRegisterIn, FaceLoginIn
from app.application import auth_usecase as uc

router = APIRouter(tags=["auth"], dependencies=[Depends(require_api_key)])


@router.post("/auth/face/register")
async def face_register(body: FaceRegisterIn):
    return ok(unwrap(uc.register_face(body.user_id, body.display_name, body.role, body.embedding)))


@router.post("/auth/face/login")
async def face_login(body: FaceLoginIn):
    return ok(unwrap(uc.login_face(body.embedding, body.user_id)))


@router.get("/auth/me")
async def auth_me(user_id: str = Query(...)):
    return ok(unwrap(uc.get_me(user_id)))


@router.get("/auth/logins")
async def auth_logins(limit: int = Query(20, ge=1, le=200)):
    return ok(uc.recent_logins(limit))
