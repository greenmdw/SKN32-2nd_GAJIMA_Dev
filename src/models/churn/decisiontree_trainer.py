"""DecisionTree 이탈 예측 학습기 — v2 22피처 + 전처리팀 bayes HP.

입력: data/processed/churn/models7/DecisionTree_v2_train.parquet (recency<=7 코호트)
      data/processed/churn/test_tabular_v2.parquet (cohort_recency7==1 필터)
산출: models/churn/decisiontree/[runs/{tag}/]model.joblib + 평가 9종 + manifest + 리더보드
bayes(v4 DecisionTree_v2): scaler=none, imbalance=classweight,
                           max_depth=12, min_samples_leaf=35, ccp_alpha=5.08e-4
"""
import joblib
import numpy as np
from sklearn.tree import DecisionTreeClassifier

from src.common.data import FEATURE_ORDER_V2, load_tabular_v2, make_scaler
from src.common.evaluation import evaluate_and_save
from src.common.manifest import write_manifest
from src.common.registry import artifact_rel_path, log_run, resolve_dirs

MODEL_KEY = "decisiontree"
MODEL_NAME = "DecisionTree_Churn_v2"
MODEL_TYPE = "tree"
SEED = 42
DEFAULTS = {
    "scaler": "none",
    "max_depth": 12,
    "min_samples_leaf": 35,
    "ccp_alpha": 0.0005083825348819038,
    "criterion": "gini",
}


def train(run_tag=None, **overrides):
    hp = dict(DEFAULTS)
    hp.update(overrides)

    (X_tr, y_tr, _), (X_te, y_te, uid_te) = load_tabular_v2(MODEL_KEY)

    scaler = make_scaler(hp["scaler"])
    if scaler is not None:
        X_tr = scaler.fit_transform(X_tr)
        X_te = scaler.transform(X_te)

    clf = DecisionTreeClassifier(
        max_depth=hp["max_depth"],
        min_samples_leaf=hp["min_samples_leaf"],
        ccp_alpha=hp["ccp_alpha"],
        criterion=hp["criterion"],
        class_weight="balanced",
        random_state=SEED,
    )
    clf.fit(X_tr, y_tr)
    y_score = clf.predict_proba(X_te)[:, 1]

    artifact_dir, eval_dir = resolve_dirs(MODEL_KEY, run_tag)
    joblib.dump(clf, artifact_dir / "model.joblib")
    if scaler is not None:
        joblib.dump(scaler, artifact_dir / "preprocessor.joblib")

    imp = clf.feature_importances_
    order = np.argsort(-imp)
    shap_summary = {
        "feature": [FEATURE_ORDER_V2[i] for i in order],
        "mean_abs_shap": [float(imp[i]) for i in order],
        "rank": list(range(1, len(FEATURE_ORDER_V2) + 1)),
        "note": "feature_importances_ proxy; replace with TreeSHAP if shap installed",
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
        shap_summary=shap_summary,
    )

    write_manifest(
        eval_dir,
        model_name=MODEL_NAME,
        model_key=MODEL_KEY,
        model_type=MODEL_TYPE,
        input_train="data/processed/churn/models7/DecisionTree_v2_train.parquet",
        input_test="data/processed/churn/test_tabular_v2.parquet",
        artifact_path=artifact_rel_path(MODEL_KEY, run_tag, "model.joblib"),
        metrics=metrics,
        preprocessing_config={
            "input_format": "parquet",
            "scale": hp["scaler"],
            "feature_order": FEATURE_ORDER_V2,
            "id_column": "user_id",
            "target_column": "churn",
            "imbalance": "classweight",
            "max_depth": hp["max_depth"],
            "min_samples_leaf": hp["min_samples_leaf"],
            "ccp_alpha": hp["ccp_alpha"],
            "criterion": hp["criterion"],
        },
    )
    log_run(MODEL_KEY, run_tag, hp, metrics)
    print(f"[{MODEL_KEY}] run={run_tag or 'baseline'} feats={len(FEATURE_ORDER_V2)} hp={hp} "
          f"ROC-AUC={metrics['roc_auc']:.4f} PR-AUC={metrics['pr_auc']:.4f} F1={metrics['best_f1']:.4f}")
    return metrics


if __name__ == "__main__":
    train()
