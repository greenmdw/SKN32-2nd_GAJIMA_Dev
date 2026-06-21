# -*- coding: utf-8 -*-
"""interfaces/http — 예측 기록/조회(19-4 §5). 봉투 적용."""
from fastapi import APIRouter, Depends, Query
from app.interfaces.http.deps import require_api_key, unwrap
from app.interfaces.http.responses import ok
from app.schemas.model_submit_schema import PredictIn
from app.application import predict_usecase as uc

router = APIRouter(tags=["predictions"], dependencies=[Depends(require_api_key)])


@router.post("/predict")
async def predict(body: PredictIn):
    return ok(uc.predict_from_score(body.user_id, body.churn_probability, body.model_id))


@router.get("/predictions/latest")
async def latest(user_id: str = Query(...)):
    return ok(unwrap(uc.get_latest(user_id)))


@router.get("/predictions/top-risk")
async def top_risk(limit: int = Query(20, ge=1, le=500), min_prob: float = Query(0.0, ge=0.0, le=1.0)):
    return ok(uc.get_top_risk(limit=limit, min_prob=min_prob))
