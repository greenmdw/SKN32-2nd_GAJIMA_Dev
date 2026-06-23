# -*- coding: utf-8 -*-
"""src/convert_raw_model_run — 모델팀 단일모델 raw 산출물 → 백엔드 per-model 스키마 변환.

입력(raw, 단일 모델): eval_predictions.parquet(user_id,y_true,y_pred,y_score) [+ metrics_summary.json]
출력: data/processed/evaluation/churn/{model_key}/  (백엔드 artifact-first 리더가 읽는 19-3 §6 파일)

raw 예측만으로 계산 가능한 파일만 생성한다. revenue/feature_importance가 없으면
value_at_risk·business_value·shap_summary 는 생성하지 않고, 백엔드 리더가 _fallback 으로 대체한다.

실행: python src/convert_raw_model_run.py --src .tmp_model1 --model LightGBM
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (roc_curve, precision_recall_curve, roc_auc_score,
                             average_precision_score, f1_score, brier_score_loss)
from sklearn.calibration import calibration_curve

ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = ROOT / "data" / "processed" / "evaluation" / "churn"

KEY = {"CatBoost": "catboost", "LightGBM": "lightgbm", "XGBoost": "xgboost",
       "RandomForest": "randomforest", "DecisionTree": "decisiontree",
       "LogReg": "logreg", "Transformer": "transformer"}
TYPE = {"CatBoost": "tree", "LightGBM": "tree", "XGBoost": "tree", "RandomForest": "tree",
        "DecisionTree": "tree", "LogReg": "linear", "Transformer": "sequence"}
FEATURE_ORDER = ["recency_days", "tenure_days", "ndays", "n_events", "n_view", "n_cart",
                 "n_remove_from_cart", "n_purchase", "avg_price", "purch_amt"]


def _w(d, name, obj):
    (d / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _downsample(*arrays, n=130):
    """엔드포인트 보존 균등 다운샘플. 길이 <= n 이면 그대로."""
    L = len(arrays[0])
    if L <= n:
        return [list(a) for a in arrays]
    idx = np.unique(np.linspace(0, L - 1, n).round().astype(int))
    return [[float(a[i]) for i in idx] for a in arrays]


def confusion(y_true, y_pred):
    tp = int(((y_true == 1) & (y_pred == 1)).sum()); tn = int(((y_true == 0) & (y_pred == 0)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum()); fn = int(((y_true == 1) & (y_pred == 0)).sum())
    return {"tn": tn, "fp": fp, "fn": fn, "tp": tp}


def threshold_sweep(y_true, y_score, n=39):
    ts = np.linspace(0.025, 0.975, n)
    thr, prec, rec, f1 = [], [], [], []
    pos = max(int((y_true == 1).sum()), 1)
    for t in ts:
        yp = (y_score >= t).astype(int)
        tp = int(((y_true == 1) & (yp == 1)).sum()); fp = int(((y_true == 0) & (yp == 1)).sum())
        p = tp / (tp + fp) if (tp + fp) else 0.0
        r = tp / pos
        thr.append(round(float(t), 4)); prec.append(round(p, 4)); rec.append(round(r, 4))
        f1.append(round(2 * p * r / (p + r), 4) if (p + r) else 0.0)
    return {"threshold": thr, "precision": prec, "recall": rec, "f1": f1}


def score_dist(y_true, y_score, nbins=10):
    bins = np.linspace(0, 1, nbins + 1)
    idx = np.clip(np.digitize(y_score, bins) - 1, 0, nbins - 1)
    ch = [int(((idx == b) & (y_true == 1)).sum()) for b in range(nbins)]
    nch = [int(((idx == b) & (y_true == 0)).sum()) for b in range(nbins)]
    return {"bins": [round(float(x), 2) for x in bins[:-1]], "churn_count": ch, "non_churn_count": nch}


def lift(y_true, y_score, pcts=(1, 5, 10, 20, 30, 50)):
    order = np.argsort(-y_score)
    yt = y_true[order]
    total_pos = max(int((yt == 1).sum()), 1); n = len(yt)
    tp, cap, lf = [], [], []
    for p in pcts:
        k = max(int(n * p / 100), 1)
        cr = int((yt[:k] == 1).sum()) / total_pos
        tp.append(p); cap.append(round(cr, 4)); lf.append(round(cr / (p / 100), 3))
    return {"top_percent": list(tp), "capture_rate": cap, "lift": lf}


def calibration(y_true, y_score, nbins=10):
    prob_true, prob_pred = calibration_curve(y_true, y_score, n_bins=nbins, strategy="uniform")
    edges = np.linspace(0, 1, nbins + 1)
    counts_all = np.histogram(y_score, bins=edges)[0]
    # calibration_curve 는 비어있는 bin 을 건너뛴다 → pred 위치로 bin 매핑해 count 정렬
    count = []
    for pp in prob_pred:
        b = min(int(pp * nbins), nbins - 1)
        count.append(int(counts_all[b]))
    return {"prob_pred": [round(float(x), 4) for x in prob_pred],
            "prob_true": [round(float(x), 4) for x in prob_true], "count": count}, (prob_true, prob_pred, counts_all)


def ece_score(prob_true, prob_pred, counts_all, n_total):
    # 채워진 bin 만으로 가중 ECE 근사
    w = []
    for pp in prob_pred:
        b = min(int(pp * len(counts_all)), len(counts_all) - 1)
        w.append(counts_all[b] / max(n_total, 1))
    return float(round(np.sum(np.abs(np.array(prob_true) - np.array(prob_pred)) * np.array(w)), 4))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="raw 산출물 폴더(eval_predictions.parquet 포함)")
    ap.add_argument("--model", required=True, choices=list(KEY.keys()))
    args = ap.parse_args()

    src = Path(args.src)
    model, mkey = args.model, KEY[args.model]
    df = pd.read_parquet(src / "eval_predictions.parquet")
    y_true = df["y_true"].to_numpy().astype(int)
    y_score = df["y_score"].to_numpy().astype(float)
    y_pred = (df["y_pred"].to_numpy().astype(int) if "y_pred" in df.columns
              else (y_score >= 0.5).astype(int))

    d = OUT_ROOT / mkey
    d.mkdir(parents=True, exist_ok=True)

    # --- 곡선 ---
    fpr, tpr, _ = roc_curve(y_true, y_score)
    fpr, tpr = _downsample(fpr, tpr, n=130)
    _w(d, "roc_curve.json", {"fpr": fpr, "tpr": tpr})

    prec, rec, _ = precision_recall_curve(y_true, y_score)
    rec, prec = _downsample(rec, prec, n=110)
    _w(d, "pr_curve.json", {"recall": rec, "precision": prec})

    _w(d, "threshold_curve.json", threshold_sweep(y_true, y_score))

    cal, (pt, pp, counts_all) = calibration(y_true, y_score)
    _w(d, "calibration_curve.json", cal)

    # --- 예측 기반 ---
    cm = confusion(y_true, y_pred)
    _w(d, "confusion_matrix.json", cm)
    _w(d, "score_distribution.json", score_dist(y_true, y_score))
    _w(d, "lift_curve.json", lift(y_true, y_score))

    # --- metrics_summary (백엔드 객체 스키마) ---
    sweep = threshold_sweep(y_true, y_score)
    best_i = int(np.argmax(sweep["f1"]))
    best_thr = sweep["threshold"][best_i]
    roc_auc = float(round(roc_auc_score(y_true, y_score), 4))
    pr_auc = float(round(average_precision_score(y_true, y_score), 4))
    _w(d, "metrics_summary.json", {
        "model_name": f"{model}_Churn_v2", "model_key": mkey, "model_type": TYPE[model],
        "label_name": "churn", "horizon_days": 7,
        "n_test": int(len(df)), "positive_rate": round(float(y_true.mean()), 4),
        "roc_auc": roc_auc, "pr_auc": pr_auc,
        "best_threshold": best_thr, "f1": float(round(f1_score(y_true, y_pred), 4)),
        "brier": float(round(brier_score_loss(y_true, y_score), 4)),
        "ece": ece_score(pt, pp, counts_all, len(df)),
        "confusion_matrix": cm,
        "source": f"raw:{src.name}"})

    # DL 아님 → 빈 training_history
    _w(d, "training_history.json", {"epoch": [], "train_loss": [], "val_loss": []})

    # --- model_run_manifest ---
    ev = {f"{n}_path": f"data/processed/evaluation/churn/{mkey}/{n}.json"
          for n in ["metrics_summary", "roc_curve", "pr_curve", "threshold_curve",
                    "confusion_matrix", "calibration_curve", "lift_curve", "score_distribution",
                    "training_history"]}
    ev["eval_predictions_path"] = f"data/processed/evaluation/churn/{mkey}/eval_predictions.parquet"
    _w(d, "model_run_manifest.json", {
        "model_name": f"{model}_Churn_v2", "model_key": mkey, "model_type": TYPE[model],
        "label_name": "churn", "horizon_days": 7, "feature_schema_version": "v2",
        "dataset_path": f"data/processed/churn/models7/{model}_v2_train.parquet",
        "artifact_path": f"models/preprocessors/prep_{model}_v2.joblib",
        "preprocessing_config": {"input_format": "parquet", "scale": "none",
            "feature_order": FEATURE_ORDER, "id_column": "user_id", "target_column": "churn"},
        "metrics": {"roc_auc": roc_auc, "pr_auc": pr_auc, "best_threshold": best_thr,
                    "best_f1": float(round(f1_score(y_true, y_pred), 4))},
        "evaluation": ev, "source": f"raw:{src.name}",
        "note": "value_at_risk·business_value·shap_summary 는 raw 미포함 → _fallback 사용"})

    # eval_predictions.parquet (백엔드 컬럼 정렬 + model_name/threshold)
    out_df = df.copy()
    out_df["model_name"] = model
    out_df["threshold"] = best_thr
    out_df.to_parquet(d / "eval_predictions.parquet", index=False)

    # raw 에서 만들 수 없는 파일은 primary 에서 제거 → _fallback 으로 대체되게
    for missing in ("value_at_risk.json", "business_value.json", "shap_summary.json"):
        p = d / missing
        if p.exists():
            p.unlink()

    made = sorted(x.name for x in d.glob("*"))
    print(f"[OK] {model} → evaluation/churn/{mkey}/ ({len(made)} files)")
    print("     " + ", ".join(made))
    print(f"     roc_auc={roc_auc} pr_auc={pr_auc} best_thr={best_thr} n_test={len(df)}")
    print("     fallback(미생성): value_at_risk.json, business_value.json, shap_summary.json")


if __name__ == "__main__":
    main()
