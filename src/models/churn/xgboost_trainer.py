"""XGBoost 이탈 예측 학습기 — v2 22피처 + 전처리팀 bayes HP.

입력: data/processed/churn/models7/XGBoost_v2_train.parquet (recency<=7 코호트)
      data/processed/churn/test_tabular_v2.parquet (cohort_recency7==1 필터)
산출: models/churn/xgboost/[runs/{tag}/]model.json (+preprocessor.joblib) + 평가 9종 + manifest + 리더보드
bayes(v4 XGBoost_v2): scaler=robust, imbalance=classweight(scale_pos_weight=4),
    n_est=312, max_depth=5, lr=0.0359, subsample=0.775, colsample=0.695,
    min_child_weight=5, reg_alpha=0.709, reg_lambda=0.070
"""
import joblib
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split

from src.common.data import FEATURE_ORDER_V2, load_tabular_v2, make_scaler
from src.common.evaluation import evaluate_and_save
from src.common.manifest import write_manifest
from src.common.registry import artifact_rel_path, log_run, resolve_dirs

MODEL_KEY = "xgboost"
MODEL_NAME = "XGBoost_Churn_v2"
MODEL_TYPE = "tree"
SEED = 42
DEFAULTS = {
    "scaler": "robust",
    "n_estimators": 312,
    "max_depth": 5,
    "learning_rate": 0.035906165718883755,
    "subsample": 0.7752520669964538,
    "colsample_bytree": 0.694827223643275,
    "min_child_weight": 5,
    "reg_alpha": 0.7094774061671105,
    "reg_lambda": 0.0699226965154636,
    "scale_pos_weight": 4,
    "early_stopping_rounds": 0,
}


def train(run_tag=None, **overrides):
    hp = dict(DEFAULTS)
    hp.update(overrides)

    (X_full, y_full, _), (X_te, y_te, uid_te) = load_tabular_v2(MODEL_KEY)

    scaler = make_scaler(hp["scaler"])
    if scaler is not None:
        X_full = scaler.fit_transform(X_full)
        X_te = scaler.transform(X_te)

    X_tr, X_val, y_tr, y_val = train_test_split(
        X_full, y_full, test_size=0.15, stratify=y_full, random_state=SEED
    )

    clf = xgb.XGBClassifier(
        n_estimators=hp["n_estimators"],
        max_depth=hp["max_depth"],
        learning_rate=hp["learning_rate"],
        subsample=hp["subsample"],
        colsample_bytree=hp["colsample_bytree"],
        min_child_weight=hp["min_child_weight"],
        reg_alpha=hp["reg_alpha"],
        reg_lambda=hp["reg_lambda"],
        scale_pos_weight=hp["scale_pos_weight"],
        objective="binary:logistic",
        eval_metric="logloss",
        tree_method="hist",
        early_stopping_rounds=(hp["early_stopping_rounds"] or None),
        random_state=SEED,
    )
    clf.fit(X_tr, y_tr, eval_set=[(X_tr, y_tr), (X_val, y_val)], verbose=False)
    y_score = clf.predict_proba(X_te)[:, 1]

    artifact_dir, eval_dir = resolve_dirs(MODEL_KEY, run_tag)
    clf.save_model(str(artifact_dir / "model.json"))
    if scaler is not None:
        joblib.dump(scaler, artifact_dir / "preprocessor.joblib")

    res = clf.evals_result()
    tl = [float(x) for x in res["validation_0"]["logloss"]]
    vl = [float(x) for x in res["validation_1"]["logloss"]]
    training_history = {"epoch": list(range(1, len(tl) + 1)), "train_loss": tl, "val_loss": vl}

    imp = clf.feature_importances_
    order = np.argsort(-imp)
    shap_summary = {
        "feature": [FEATURE_ORDER_V2[i] for i in order],
        "mean_abs_shap": [float(imp[i]) for i in order],
        "rank": list(range(1, len(FEATURE_ORDER_V2) + 1)),
        "note": "feature_importances_(gain) proxy; replace with TreeSHAP if shap installed",
    }

    metrics = evaluate_and_save(
        eval_dir,
        model_name=MODEL_NAME,
        model_key=MODEL_KEY,
        model_type=MODEL_TYPE,
        user_id=uid_te,
        y_true=y_te,
        y_score=y_score,
        n_train=len(y_tr),
        training_history=training_history,
        shap_summary=shap_summary,
    )

    write_manifest(
        eval_dir,
        model_name=MODEL_NAME,
        model_key=MODEL_KEY,
        model_type=MODEL_TYPE,
        input_train="data/processed/churn/models7/XGBoost_v2_train.parquet",
        input_test="data/processed/churn/test_tabular_v2.parquet",
        artifact_path=artifact_rel_path(MODEL_KEY, run_tag, "model.json"),
        metrics=metrics,
        preprocessing_config={
            "input_format": "parquet",
            "scale": hp["scaler"],
            "feature_order": FEATURE_ORDER_V2,
            "id_column": "user_id",
            "target_column": "churn",
            "objective": "binary:logistic",
            "imbalance": "classweight",
            **{k: hp[k] for k in (
                "n_estimators", "max_depth", "learning_rate", "subsample",
                "colsample_bytree", "min_child_weight", "reg_alpha", "reg_lambda",
                "scale_pos_weight")},
        },
    )
    log_run(MODEL_KEY, run_tag, hp, metrics)
    print(f"[{MODEL_KEY}] run={run_tag or 'baseline'} feats={len(FEATURE_ORDER_V2)} "
          f"ROC-AUC={metrics['roc_auc']:.4f} PR-AUC={metrics['pr_auc']:.4f} F1={metrics['best_f1']:.4f}")
    return metrics


if __name__ == "__main__":
    train()
