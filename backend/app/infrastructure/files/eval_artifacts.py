# -*- coding: utf-8 -*-
"""infrastructure/files — 모델팀 산출물(19-3 §6) artifact-first 리더 + 19-4 §9 chart 변환.
우선순위: per-model evaluation/churn/{key}/*.json → 집계 curves.json → 빈 상태.
백엔드는 재학습/재계산하지 않고, 학습 종료 시점 산출물을 chart-ready JSON으로 변환만 한다."""
import json
from app.config import EVAL_DIR

CHURN_DIR = EVAL_DIR / "churn"

# 모델명 → model_key (19-3)
KEY = {"catboost": "catboost", "lightgbm": "lightgbm", "xgboost": "xgboost",
       "randomforest": "randomforest", "decisiontree": "decisiontree",
       "logreg": "logreg", "transformer": "transformer"}
NAME = {"CatBoost": "catboost", "LightGBM": "lightgbm", "XGBoost": "xgboost",
        "RandomForest": "randomforest", "DecisionTree": "decisiontree",
        "LogReg": "logreg", "Transformer": "transformer"}


def _json(p):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def resolve_key(model):
    """model = 이름('CatBoost')·model_key('catboost')·등록명('CatBoost_Churn_v2') 모두 허용."""
    if model in NAME:
        return NAME[model]
    s = str(model).lower().replace("_churn_v2", "").replace("_v2", "")
    return KEY.get(s, s)


def _artifact(mkey, fname):
    return _json(CHURN_DIR / mkey / fname)


def _wrap(chart_name, chart_type, x, y, data, model=None, source="artifact", **extra):
    out = {"chart_name": chart_name, "chart_type": chart_type, "x": x, "y": y,
           "data": data, "meta": {"schema_version": "chart.v1", "source": source}}
    if model:
        out["model"] = model
    out.update(extra)
    return out


# ---------- per-model charts (19-4 §8 5~15) ----------
def model_chart(model, chart_name):
    """kebab chart_name → 19-4 §9 chart JSON. 없으면 빈 data."""
    mkey = resolve_key(model)
    cn = chart_name.replace("_", "-")

    if cn in ("roc-auc", "roc"):
        a = _artifact(mkey, "roc_curve.json")
        rows = [{"fpr": f, "tpr": t} for f, t in zip(a["fpr"], a["tpr"])] if a else []
        return _wrap("roc_auc", "line", "fpr", "tpr", rows, model)
    if cn in ("pr-auc", "pr"):
        a = _artifact(mkey, "pr_curve.json")
        rows = [{"recall": r, "precision": p} for r, p in zip(a["recall"], a["precision"])] if a else []
        return _wrap("pr_auc", "line", "recall", "precision", rows, model)
    if cn == "threshold":
        a = _artifact(mkey, "threshold_curve.json")
        rows = ([{"threshold": t, "precision": p, "recall": r, "f1": f}
                 for t, p, r, f in zip(a["threshold"], a["precision"], a["recall"], a["f1"])] if a else [])
        return _wrap("threshold", "line", "threshold", ["precision", "recall", "f1"], rows, model)
    if cn == "calibration":
        a = _artifact(mkey, "calibration_curve.json")
        rows = ([{"prob_pred": pp, "prob_true": pt, "count": c}
                 for pp, pt, c in zip(a["prob_pred"], a["prob_true"], a.get("count", [None] * len(a["prob_pred"])))]
                if a else [])
        return _wrap("calibration", "line", "prob_pred", "prob_true", rows, model)
    if cn == "confusion-matrix":
        a = _artifact(mkey, "confusion_matrix.json")
        rows = ([{"actual": 0, "predicted": 0, "count": a["tn"]}, {"actual": 0, "predicted": 1, "count": a["fp"]},
                 {"actual": 1, "predicted": 0, "count": a["fn"]}, {"actual": 1, "predicted": 1, "count": a["tp"]}]
                if a else [])
        return _wrap("confusion_matrix", "matrix", "predicted", "actual", rows, model)
    if cn == "lift":
        a = _artifact(mkey, "lift_curve.json")
        rows = ([{"top_percent": tp, "capture_rate": cr, "lift": lf}
                 for tp, cr, lf in zip(a["top_percent"], a["capture_rate"], a["lift"])] if a else [])
        return _wrap("lift", "line", "top_percent", ["capture_rate", "lift"], rows, model)
    if cn == "score-distribution":
        a = _artifact(mkey, "score_distribution.json")
        rows = ([{"bin": b, "churn_count": c, "non_churn_count": n}
                 for b, c, n in zip(a["bins"], a["churn_count"], a["non_churn_count"])] if a else [])
        return _wrap("score_distribution", "histogram", "bin", ["churn_count", "non_churn_count"], rows, model)
    if cn in ("shap-summary", "shap", "feature-importance"):
        a = _artifact(mkey, "shap_summary.json")
        rows = ([{"feature": f, "mean_abs_shap": s, "rank": r}
                 for f, s, r in zip(a["feature"], a["mean_abs_shap"], a["rank"])] if a else [])
        return _wrap("shap_summary", "bar", "feature", "mean_abs_shap", rows, model)
    if cn == "value-at-risk":
        a = _artifact(mkey, "value_at_risk.json")
        return _wrap("value_at_risk", "treemap", "segment", "value_at_risk", a or [], model)
    if cn == "revenue-recovery":
        a = _artifact(mkey, "business_value.json")
        rows = ([{"top_percent": tp, "value_at_risk": v, "expected_recovery": e}
                 for tp, v, e in zip(a["top_percent"], a["value_at_risk"], a["expected_recovery"])] if a else [])
        return _wrap("revenue_recovery", "bar", "top_percent", ["value_at_risk", "expected_recovery"], rows, model,
                     summary=(a.get("assumptions") if a else None))
    if cn in ("train-val-loss", "training-history"):
        a = _artifact(mkey, "training_history.json") or {}
        rows = [{"epoch": e, "train_loss": tl, "val_loss": vl}
                for e, tl, vl in zip(a.get("epoch", []), a.get("train_loss", []), a.get("val_loss", []))]
        return _wrap("train_val_loss", "line", "epoch", ["train_loss", "val_loss"], rows, model)
    return None


def model_metrics(model):
    return _artifact(resolve_key(model), "metrics_summary.json")


def has_artifacts(model):
    return (CHURN_DIR / resolve_key(model)).exists()
