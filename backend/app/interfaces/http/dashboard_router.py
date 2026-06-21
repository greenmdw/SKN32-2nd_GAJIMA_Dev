# -*- coding: utf-8 -*-
"""interfaces/http — 대시보드 요약/차트(모델 비종속)/유저/추천/리텐션/앙상블(19-4 §5). 봉투 적용."""
from fastapi import APIRouter, Depends
from app.interfaces.http.deps import require_api_key, unwrap
from app.interfaces.http.responses import ok
from app.schemas.model_submit_schema import EnsembleIn
from app.schemas.ops_schema import RetentionActionIn
from app.application.dashboard_usecase import get_dashboard_summary
from app.application import charts_usecase as cu
from app.application import predict_usecase as puc
from app.infrastructure.mysql import ops_repository as ops

router = APIRouter(tags=["dashboard"], dependencies=[Depends(require_api_key)])


@router.get("/dashboard/summary")
async def dashboard_summary():
    return ok(get_dashboard_summary())


@router.get("/dashboard/charts/{chart_name}")
async def dashboard_chart(chart_name: str):
    """모델 비종속: system-architecture·data-distribution·cohort-retention·baseline-comparison."""
    return ok(unwrap(cu.get_dashboard_chart(chart_name)))


@router.get("/dashboard/user/{user_id}")
async def dashboard_user(user_id: str):
    return ok(unwrap(cu.get_user_dashboard(user_id)))


@router.get("/recommendations/{user_id}")
async def recommendations(user_id: str):
    return ok(cu.get_recommendations(user_id))


@router.post("/retention-actions")
async def retention_action(body: RetentionActionIn):
    return ok(ops.add_retention_action(body.user_id, body.action_type, body.message, body.prediction_id))


@router.post("/ensemble/run")
async def ensemble_run(body: EnsembleIn):
    return ok(puc.run_ensemble([m.model_dump() for m in body.members]))
