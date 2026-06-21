# -*- coding: utf-8 -*-
"""interfaces/http — 모델 등록/조회/차트(19-4 §5·§8). 봉투 적용 + artifact-first 차트(kebab)."""
from fastapi import APIRouter, Depends
from app.interfaces.http.deps import require_api_key, unwrap
from app.interfaces.http.responses import ok
from app.schemas.model_submit_schema import ModelSubmitIn
from app.application import submit_model_usecase as uc
from app.application import charts_usecase as cu

router = APIRouter(tags=["models"], dependencies=[Depends(require_api_key)])


@router.post("/models/submit")
async def submit(body: ModelSubmitIn):
    return ok(unwrap(uc.submit_model(body.model_dump())))


@router.get("/models")
async def list_models():
    return ok(unwrap(uc.list_models()))


@router.get("/models/active")
async def list_active():
    return ok(unwrap(uc.list_active()))


@router.get("/models/{model_id}/evaluation")
async def model_evaluation(model_id: str):
    return ok(unwrap(uc.get_model_evaluation(model_id)))


@router.get("/models/{model}/charts/{chart_name}")
async def model_charts(model: str, chart_name: str):
    """chart_name: pr-auc·roc-auc·threshold·calibration·confusion-matrix·lift·
    score-distribution·shap-summary·value-at-risk·revenue-recovery·train-val-loss."""
    return ok(unwrap(cu.get_model_chart(model, chart_name)))
