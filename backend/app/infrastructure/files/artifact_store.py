# -*- coding: utf-8 -*-
"""infrastructure/files — eval 산출물(차트 원천) 파일 reader. 백엔드는 재학습 안 함(19-2 §9.3).
Node `infrastructure/files/artifactStore.js` 의 포팅 + feature_importance 폴백."""
import json
from app.config import EVAL_DIR


def _json(p):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def metrics() -> dict:
    return _json(EVAL_DIR / "metrics_summary.json") or {}


def curves() -> dict:
    return _json(EVAL_DIR / "curves.json") or {}


def shap_summary() -> dict:
    return _json(EVAL_DIR / "shap_summary.json") or {}


def feature_importance() -> dict:
    return _json(EVAL_DIR / "feature_importance.json") or {}


def chart(model: str, name: str):
    """모델별 차트 JSON. name ∈ {roc,pr,threshold,calibration,shap,feature_importance}.
    SHAP 없으면 feature_importance 로 폴백(26-8)."""
    if name == "shap":
        s = shap_summary().get(model)
        if s is not None:
            return s
        return feature_importance().get(model)        # 폴백
    if name == "feature_importance":
        return feature_importance().get(model)
    return (curves().get(model) or {}).get(name)


def eval_exists() -> bool:
    return (EVAL_DIR / "metrics_summary.json").exists()
