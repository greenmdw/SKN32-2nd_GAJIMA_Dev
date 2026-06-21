# -*- coding: utf-8 -*-
"""application — 예측 기록/조회/앙상블 usecase(19-2 §9.2).
점수(churn_probability)는 모델파트/사이드카가 제공. 백엔드는 위험등급·리텐션·로그를 담당(학습 금지)."""
from app.domain.risk_level import risk_level, retention_action, ensemble
from app.infrastructure.mysql.session import prediction_repository


def predict_from_score(user_id: str, churn_probability: float, model_id=None) -> dict:
    r = risk_level(churn_probability)
    act = retention_action(churn_probability)
    prediction_repository.log({
        "model_id": model_id, "user_id": user_id,
        "churn_probability": churn_probability, "risk_level": r,
        "recommended_action": act["action_message"],
    })
    return {"user_id": user_id, "churn_probability": churn_probability,
            "risk_level": r, "recommended_action": act["action_message"], "horizon_days": 7}


def get_latest(user_id: str) -> dict:
    row = prediction_repository.latest(user_id)
    if not row:
        return {"_status": 404, "error": f"예측 없음: {user_id}"}
    return {"user_id": user_id, "prediction": row}


def get_top_risk(limit: int = 20, min_prob: float = 0.0) -> dict:
    rows = prediction_repository.top_risk(limit=limit, min_prob=min_prob)
    return {"count": len(rows), "horizon_days": 7,
            "title": "향후 7일 이탈 확률 고위험 유저", "users": rows}


def run_ensemble(members: list) -> dict:
    return ensemble(members or [])
