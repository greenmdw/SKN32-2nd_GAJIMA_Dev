# -*- coding: utf-8 -*-
"""schemas — 얼굴 인증 요청 모델(19-4)."""
from typing import Optional, List
from pydantic import BaseModel


class FaceRegisterIn(BaseModel):
    user_id: str
    display_name: Optional[str] = None
    role: str = "customer"
    embedding: Optional[List[float]] = None     # insightface 512d normed (클라이언트 추출)


class FaceLoginIn(BaseModel):
    embedding: Optional[List[float]] = None
    user_id: Optional[str] = None               # 얼굴 없을 때 아이디 폴백
