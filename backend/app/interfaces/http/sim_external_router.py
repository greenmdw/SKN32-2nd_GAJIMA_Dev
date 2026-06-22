# -*- coding: utf-8 -*-
"""interfaces/http — 시뮬 사이트(ecom-churn-simulation) 외부 계약 어댑터.
앱의 fastApiClient.ts가 기대하는 raw JSON(봉투 X, api-key X)으로 응답.
실추론은 sim_usecase(prep 번들)·추천은 catalog_store 재사용. CORS는 main에서 허용."""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter
from app.schemas.sim_external_schema import ChurnPredictIn, RecommendationIn, EventIn
from app.application import sim_usecase as sim
from app.infrastructure.files import catalog_store as cat
from app.infrastructure.mysql.session import sim_event_repository

router = APIRouter(tags=["sim-external"])
KST = timezone(timedelta(hours=9))


def _now():
    return datetime.now(KST).isoformat()


@router.post("/api/churn/predict")
async def churn_predict(body: ChurnPredictIn):
    # 실시간 세션 이탈값 = 3단 폴백(B-모델 models/ → B-데이터 data/ → A-하자드).
    # 모델팀 세션모델 배포 전엔 A(하자드, 학습 0·설명가능)가 동작.
    scored = sim.realtime_session_score(body.session_id, body.user_id,
                                        [e.model_dump() for e in body.events])
    p = scored.get("churn_probability")
    prob_pct = round(float(p) * 100, 1) if isinstance(p, (int, float)) else 0.0
    return {"session_id": body.session_id, "churn_probability": prob_pct,
            "risk_level": scored.get("risk_level", "low"),
            "source": scored.get("source"), "timestamp": _now()}


@router.post("/api/recommendations")
async def recommendations(body: RecommendationIn):
    recs = []
    sims = cat.similar_categories(body.category_id, k=3) if body.category_id else []
    for s in sims:
        for pr in cat.products(limit=1, category_id=s["category_id"]):
            recs.append({
                "product_id": str(pr.get("product_id")),
                "name": pr.get("category_name") or str(pr.get("product_id")),
                "category_id": str(pr.get("category_id")),
                "brand": pr.get("brand"),
                "price": pr.get("price"),
                "score": s.get("cosine"),
                "reason": f"유사 카테고리(코사인 {s.get('cosine')})",
            })
    return {"session_id": body.session_id, "user_id": body.user_id,
            "current_product_id": body.current_product_id,
            "recommendations": recs, "timestamp": _now()}


@router.post("/api/events")
async def ingest_event(body: EventIn):
    sim_event_repository.log({
        "user_id": str(body.user_id), "session_id": body.session_id,
        "event_type": body.event_type, "product_id": body.product_id,
        "category_id": body.category_id, "brand": body.brand, "price": body.price,
        "churn_prob": None, "risk_level": None})
    return {"status": "ok", "event_id": body.event_id, "timestamp": _now()}


@router.get("/api/analytics/session/{session_id}")
async def analytics(session_id: str):
    a = sim.session_analytics(session_id)
    return {"session_id": session_id, "average_session_duration": 0, **a}
