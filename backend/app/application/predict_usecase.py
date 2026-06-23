# -*- coding: utf-8 -*-
"""application — 예측 기록/조회/앙상블 usecase(19-2 §9.2).
점수(churn_probability)는 모델파트/사이드카가 제공. 백엔드는 위험등급·리텐션·로그를 담당(학습 금지)."""
from app.domain.risk_level import risk_level, retention_action, ensemble
from app.infrastructure.mysql.session import prediction_repository, model_repository


def predict_from_score(user_id: str, churn_probability: float, model_id=None) -> dict:
    r = risk_level(churn_probability)
    act = retention_action(churn_probability)
    if model_id is not None and not model_repository.exists(model_id):
        model_id = None        # FK 견고화: 미등록 model_id는 null로(prediction_log FK 위반 방지)
    prediction_repository.log({
        "model_id": model_id, "user_id": user_id,
        "churn_probability": churn_probability, "risk_level": r,
        "recommended_action": act["action_message"],
    })
    return {"user_id": user_id, "churn_probability": churn_probability,
            "risk_level": r, "recommended_action": act["action_message"], "horizon_days": 7}


def _active_model_name():
    try:
        rows = model_repository.active()
        if rows:
            return str(rows[0].get("model_name", "")).replace("_Churn_v2", "").replace("_v2", "") or None
    except Exception:
        pass
    return None


def get_latest(user_id: str) -> dict:
    """최신 예측(19-7-1 §5.3: 평탄한 prediction 객체). 없으면 200 빈 객체(프론트 render_empty)."""
    row = prediction_repository.latest(user_id)
    if not row:
        return {}        # _status 없음 → 404 아님. 프론트가 '예측 없음' 빈상태로 표시.
    out = dict(row)
    out.setdefault("user_id", user_id)
    if not out.get("model_name"):
        out["model_name"] = _active_model_name()
    return out


def get_top_risk(limit: int = 20, min_prob: float = 0.0) -> list:
    """고위험 유저 목록(19-7-1 §5.3: data=리스트). 테이블로 바로 렌더 가능."""
    return prediction_repository.top_risk(limit=limit, min_prob=min_prob)


def run_ensemble(members: list) -> dict:
    return ensemble(members or [])
