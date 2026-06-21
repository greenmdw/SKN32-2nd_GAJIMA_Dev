# -*- coding: utf-8 -*-
"""main — FastAPI 부트스트랩(19-2). 운영 백엔드: 레지스트리·평가 ingest·차트 API·예측 로그.
모든 응답은 {ok,data,meta,error} 봉투(19-4 §6). 추론(학습) 코드 없음.
실행: uvicorn app.main:app --port 8090."""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.responses import JSONResponse
from app.config import PORT
from app.infrastructure.mysql.session import mode
from app.interfaces.http.responses import err
from app.interfaces.http import (health_router, auth_router, models_router,
                                 predictions_router, dashboard_router)

app = FastAPI(title="가지마 운영 백엔드 (FastAPI)", version="19-2",
              description="모델 레지스트리·평가 ingest·대시보드 차트 API·예측 로그. 학습 없음.")

app.include_router(health_router.router)
app.include_router(auth_router.router)
app.include_router(models_router.router)
app.include_router(predictions_router.router)
app.include_router(dashboard_router.router)


# --- 에러도 봉투로 통일(19-4 §6) ---
@app.exception_handler(StarletteHTTPException)
async def http_exc(_: Request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code,
                        content=err(f"HTTP_{exc.status_code}", str(exc.detail)))


@app.exception_handler(RequestValidationError)
async def validation_exc(_: Request, exc: RequestValidationError):
    msg = "; ".join(f"{'.'.join(str(x) for x in e.get('loc', []))}: {e.get('msg')}" for e in exc.errors())
    return JSONResponse(status_code=422, content=err("VALIDATION", msg or "검증 실패"))


@app.exception_handler(Exception)
async def unhandled_exc(_: Request, exc: Exception):
    return JSONResponse(status_code=500, content=err("INTERNAL", str(exc)))


@app.get("/")
async def root():
    return {"service": "gajima-backend", "framework": "fastapi", "db_mode": mode(),
            "docs": "/docs", "spec": "19-2/19-4"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=PORT, reload=False)
