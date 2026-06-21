# -*- coding: utf-8 -*-
"""domain 계층 — 순수 규칙(위험등급·리텐션·앙상블). DB/HTTP 의존 없음.
Node `domain/rules.js` 의 1:1 포팅."""
from app.config import RISK_HIGH, RISK_LOW


def risk_level(p: float) -> str:
    return "high" if p >= RISK_HIGH else ("medium" if p >= RISK_LOW else "low")


def retention_action(p: float) -> dict:
    r = risk_level(p)
    if r == "high":
        return {"action_type": "coupon", "action_message": "쿠폰 발송 + 재방문 알림(고위험)"}
    if r == "medium":
        return {"action_type": "remind", "action_message": "장바구니 리마인드/맞춤추천(중위험)"}
    return {"action_type": "none", "action_message": "정상 유지"}


def ensemble(members: list) -> dict:
    """members: [{model_id?, prob, weight?}, ...] → 가중평균 + 개선점."""
    members = members or []
    if not members:
        return {"prob_ensemble": 0.0, "risk_level": "low", "improvement": "구성 모델 없음", "members": []}
    tw = sum(m.get("weight", 1) for m in members) or 1
    prob = sum(m["prob"] * m.get("weight", 1) for m in members) / tw
    spread = max(m["prob"] for m in members) - min(m["prob"] for m in members)
    improvement = (
        "모델 간 편차 큼 → 보정·임계값 재조정·약한모델 가중↓"
        if spread > 0.2 else "모델 합의 양호"
    )
    return {"prob_ensemble": prob, "risk_level": risk_level(prob),
            "improvement": improvement, "members": members}
