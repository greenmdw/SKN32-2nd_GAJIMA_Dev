# -*- coding: utf-8 -*-
"""src/build_eval_artifacts — 모델팀 산출물(19-3 §6)을 집계본에서 생성.
입력: data/processed/evaluation/{curves.json, metrics_summary.json, feature_importance.json, eval_predictions.parquet}
출력: data/processed/evaluation/churn/{model_key}/  (per-model 19-3 §6 파일 + model_run_manifest.json)
실행: python src/build_eval_artifacts.py
※ 모델팀이 실제 산출물을 내면 같은 경로/스키마로 덮어쓰면 된다(백엔드는 artifact-first로 그걸 우선 사용).
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "data" / "processed" / "evaluation"
OUT = EVAL / "churn"

KEY = {"CatBoost": "catboost", "LightGBM": "lightgbm", "XGBoost": "xgboost",
       "RandomForest": "randomforest", "DecisionTree": "decisiontree",
       "LogReg": "logreg", "Transformer": "transformer"}
TYPE = {"CatBoost": "tree", "LightGBM": "tree", "XGBoost": "tree", "RandomForest": "tree",
        "DecisionTree": "tree", "LogReg": "linear", "Transformer": "sequence"}
FEATURE_ORDER = ["recency_days", "tenure_days", "ndays", "n_events", "n_view", "n_cart",
                 "n_remove_from_cart", "n_purchase", "avg_price", "purch_amt"]


def _w(d, name, obj):
    (d / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def confusion(y_true, y_pred):
    tp = int(((y_true == 1) & (y_pred == 1)).sum()); tn = int(((y_true == 0) & (y_pred == 0)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum()); fn = int(((y_true == 1) & (y_pred == 0)).sum())
    return {"tn": tn, "fp": fp, "fn": fn, "tp": tp}


def score_dist(df, nbins=10):
    bins = np.linspace(0, 1, nbins + 1)
    idx = np.clip(np.digitize(df.y_score, bins) - 1, 0, nbins - 1)
    ch = [int(((idx == b) & (df.y_true == 1)).sum()) for b in range(nbins)]
    nch = [int(((idx == b) & (df.y_true == 0)).sum()) for b in range(nbins)]
    return {"bins": [round(float(x), 2) for x in bins[:-1]], "churn_count": ch, "non_churn_count": nch}


def lift(df, pcts=(1, 5, 10, 20, 30, 50)):
    d = df.sort_values("y_score", ascending=False).reset_index(drop=True)
    total_pos = max(int((d.y_true == 1).sum()), 1); n = len(d)
    tp, cap, lf = [], [], []
    for p in pcts:
        k = max(int(n * p / 100), 1)
        captured = int((d.y_true.iloc[:k] == 1).sum())
        cr = captured / total_pos
        tp.append(p); cap.append(round(cr, 4)); lf.append(round(cr / (p / 100), 3))
    return {"top_percent": list(tp), "capture_rate": cap, "lift": lf}


def value_at_risk(df):
    seg = {"high": (df.y_score >= 0.65), "medium": (df.y_score >= 0.35) & (df.y_score < 0.65),
           "low": (df.y_score < 0.35)}
    rows = []
    for name, mask in seg.items():
        sub = df[mask]
        rows.append({"segment": name, "users": int(len(sub)),
                     "value_at_risk": float(round((sub.revenue * sub.y_score).sum(), 2))})
    return rows


def business_value(df, pcts=(5, 10, 20), coupon_cost=3000, save_rate=0.08):
    d = df.sort_values("y_score", ascending=False).reset_index(drop=True); n = len(d)
    avg_rev = float(d.revenue[d.revenue > 0].mean() or 0)
    tp, tu, var, rec = [], [], [], []
    for p in pcts:
        k = max(int(n * p / 100), 1); sub = d.iloc[:k]
        v = float((sub.revenue * sub.y_score).sum())
        tp.append(p); tu.append(k); var.append(round(v, 2)); rec.append(round(v * save_rate, 2))
    return {"assumptions": {"coupon_cost": coupon_cost, "save_rate": save_rate, "avg_revenue": round(avg_rev, 2)},
            "top_percent": list(tp), "target_users": tu, "value_at_risk": var, "expected_recovery": rec}


def main():
    curves = json.loads((EVAL / "curves.json").read_text(encoding="utf-8"))
    metrics = json.loads((EVAL / "metrics_summary.json").read_text(encoding="utf-8"))
    fi = json.loads((EVAL / "feature_importance.json").read_text(encoding="utf-8"))
    preds = pd.read_parquet(EVAL / "eval_predictions.parquet")

    made = []
    for model, mkey in KEY.items():
        d = OUT / mkey; d.mkdir(parents=True, exist_ok=True)
        m = metrics.get(model, {})
        thr = m.get("threshold", 0.5)
        df = preds[preds.model_name == model].copy()

        # metrics_summary.json (19-3 §6.3)
        cm = confusion(df.y_true.values, df.y_pred.values) if len(df) else {}
        _w(d, "metrics_summary.json", {
            "model_name": f"{model}_Churn_v2", "model_key": mkey, "model_type": TYPE[model],
            "label_name": "churn", "horizon_days": 7,
            "n_test": int(len(df)), "positive_rate": round(float(df.y_true.mean()), 4) if len(df) else None,
            "roc_auc": m.get("auc", m.get("val_auc")), "pr_auc": m.get("pr_auc"),
            "best_threshold": thr, "f1": m.get("f1"), "brier": m.get("brier"), "ece": m.get("ece"),
            "confusion_matrix": cm})

        cv = curves.get(model, {})
        # curve 파일들 (집계 → per-model)
        if cv.get("roc"):
            _w(d, "roc_curve.json", {"fpr": cv["roc"]["fpr"], "tpr": cv["roc"]["tpr"]})
        if cv.get("pr"):
            _w(d, "pr_curve.json", {"recall": cv["pr"]["recall"], "precision": cv["pr"]["precision"]})
        if cv.get("threshold"):
            tl = cv["threshold"]
            _w(d, "threshold_curve.json", {"threshold": [r["t"] for r in tl],
                "precision": [r["precision"] for r in tl], "recall": [r["recall"] for r in tl],
                "f1": [r["f1"] for r in tl]})
        if cv.get("calibration"):
            cal = cv["calibration"]
            _w(d, "calibration_curve.json", {"prob_pred": cal["pred"], "prob_true": cal["true"],
                "count": [None] * len(cal["pred"])})

        if len(df):
            _w(d, "confusion_matrix.json", cm)
            _w(d, "score_distribution.json", score_dist(df))
            _w(d, "lift_curve.json", lift(df))
            _w(d, "value_at_risk.json", value_at_risk(df))
            _w(d, "business_value.json", business_value(df))
            df.assign(threshold=thr, model_name=model).to_parquet(d / "eval_predictions.parquet", index=False)

        # shap 대안(feature importance, 19-3 §6.9)
        if fi.get(model):
            items = sorted(fi[model].items(), key=lambda x: -x[1])
            _w(d, "shap_summary.json", {"feature": [k for k, _ in items],
                "mean_abs_shap": [round(v, 4) for _, v in items],
                "rank": list(range(1, len(items) + 1))})

        # DL training_history (ML은 빈 값)
        _w(d, "training_history.json", {"epoch": [], "train_loss": [], "val_loss": []})

        # model_run_manifest.json (19-3 §6.1)
        ev = {f"{n}_path": f"data/processed/evaluation/churn/{mkey}/{n}.json"
              for n in ["metrics_summary", "roc_curve", "pr_curve", "threshold_curve",
                        "confusion_matrix", "calibration_curve", "lift_curve", "score_distribution",
                        "shap_summary", "value_at_risk", "business_value", "training_history"]}
        ev["eval_predictions_path"] = f"data/processed/evaluation/churn/{mkey}/eval_predictions.parquet"
        _w(d, "model_run_manifest.json", {
            "model_name": f"{model}_Churn_v2", "model_key": mkey, "model_type": TYPE[model],
            "label_name": "churn", "horizon_days": 7, "feature_schema_version": "v2",
            "dataset_path": f"data/processed/churn/models7/{model}_v2_train.parquet",
            "artifact_path": (f"models/preprocessors/prep_{model}_v2.joblib" if TYPE[model] != "sequence"
                              else "models/sequence/Transformer_train_seq.npz"),
            "preprocessing_config": {"input_format": "parquet", "scale": "none",
                "feature_order": FEATURE_ORDER, "id_column": "user_id", "target_column": "churn"},
            "metrics": {"roc_auc": m.get("auc", m.get("val_auc")), "pr_auc": m.get("pr_auc"),
                        "best_threshold": thr, "best_f1": m.get("f1")},
            "evaluation": ev, "is_active_candidate": (model == "CatBoost")})
        made.append(mkey)
        print(f"  [OK] {model:13s} → evaluation/churn/{mkey}/ ({len(list(d.glob('*')))} files)")
    print(f"\n생성 완료: {len(made)} 모델 → {OUT}")


if __name__ == "__main__":
    main()
