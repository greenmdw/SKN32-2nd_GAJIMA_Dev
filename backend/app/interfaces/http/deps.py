# -*- coding: utf-8 -*-
"""interfaces/http — 공통 의존성(API 키 검증) + usecase 결과 언래핑."""
from fastapi import Header, HTTPException
from app.config import API_KEY


async def require_api_key(x_api_key: str = Header(default="")):
    """/health 외 모든 라우트에 적용(Node server.js 의 x-api-key 검사 포팅)."""
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="invalid api key")


def unwrap(result: dict):
    """usecase 가 {'_status': nnn, 'error': ...} 를 주면 HTTPException 으로 변환."""
    if isinstance(result, dict) and result.get("_status"):
        raise HTTPException(status_code=result["_status"], detail=result.get("error", "error"))
    return result
