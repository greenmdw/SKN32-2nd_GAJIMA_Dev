# -*- coding: utf-8 -*-
"""infrastructure/model_inference — prep_{Model}_v2.joblib 번들 직접 로드·점수(19-2 §10).
번들 = 전처리 파이프라인 + 모델 + isotonic 보정 + feature_order + threshold.
서빙: calibrator.predict_proba(원본 v2 피처) → churn=1 확률. 무거운 라이브러리는 첫 호출 시 lazy 로드."""
import warnings
from functools import lru_cache
from app.config import MODELS_DIR

NAME = {"catboost": "CatBoost", "lightgbm": "LightGBM", "xgboost": "XGBoost",
        "randomforest": "RandomForest", "decisiontree": "DecisionTree", "logreg": "LogReg"}


def _resolve_name(model):
    s = str(model).lower().replace("_churn_v2", "").replace("_v2", "")
    return NAME.get(s, model if model in NAME.values() else None)


@lru_cache(maxsize=8)
def load_bundle(model):
    """prep_{Name}_v2.joblib 로드(캐시). 번들 dict 반환 또는 None."""
    name = _resolve_name(model)
    if not name:
        return None
    p = MODELS_DIR / "preprocessors" / f"prep_{name}_v2.joblib"
    if not p.exists():
        return None
    import joblib
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return joblib.load(p)


def available(model):
    return load_bundle(model) is not None


def score(model, features_df):
    """features_df(1행 이상, v2 피처) → churn=1 확률 리스트. 실패 시 None."""
    bundle = load_bundle(model)
    if bundle is None:
        return None
    import pandas as pd  # noqa
    feat_order = bundle.get("feature_order")
    X = features_df.reindex(columns=feat_order) if feat_order else features_df
    est = bundle.get("calibrator") or bundle.get("model")
    if est is None or not hasattr(est, "predict_proba"):
        return None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        proba = est.predict_proba(X)[:, 1]
    return [float(x) for x in proba]


def threshold(model, default=0.5):
    b = load_bundle(model)
    return (b.get("threshold", default) if b else default)
