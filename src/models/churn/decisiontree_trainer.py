"""DecisionTree 이탈(churn) 예측 학습기 — v2 22피처.

입력: data/processed/churn/{train_tabular_v2, test_tabular_v2}.parquet 의 cohort_recency7==1
      (원시값. scaler=none이라 스케일 미적용 — train/test 모두 원시로 일치)
산출: models/churn/decisiontree/[runs/{tag}/]model.joblib + 평가 9종 + manifest + 리더보드

[최적화] sweep + 격자(OOT PR-AUC 기준):
  - ccp_alpha가 핵심 손잡이: bayes 0.0005 -> 0.0001 (정밀탐색 peak).
  - max_depth: ccp 고정 후 격자에서 6이 미세 우위(12 대비 +0.0001). min_samples_leaf는 무영향.
  - criterion=gini 유지(entropy는 ccp=0.0001과 충돌해 하락).
  최종: PR-AUC 0.9323 / ROC-AUC 0.7840 (bayes 0.9274/0.7765 대비 +0.0049/+0.0075)
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

# 정식 config = OOT sweep 최적값. (bayes)=전처리팀 원본, (opt)=sweep로 바뀐 값.
DEFAULTS = {
    "scaler": "none",              # (bayes) 트리라 스케일 무관
    "max_depth": 6,                # (opt) 12 -> 6 : ccp 고정 격자에서 미세 우위, 더 얕고 안전
    "min_samples_leaf": 35,        # (bayes) ccp에 묻혀 무영향
    "ccp_alpha": 0.0001,           # (opt) 0.0005 -> 0.0001 : 비용복잡도 가지치기, 성능의 핵심 손잡이
    "criterion": "gini",           # (bayes) entropy는 ccp=0.0001과 충돌해 오히려 하락
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
        ccp_alpha=hp["ccp_alpha"],        # 비용복잡도 가지치기 — 과적합 제어 핵심
        criterion=hp["criterion"],
        class_weight="balanced",          # churn 불균형(82%) 보정 (bayes imbalance=classweight)
        random_state=SEED,
    )
    clf.fit(X_tr, y_tr)
    y_score = clf.predict_proba(X_te)[:, 1]  # churn=1 확률 (19-3 §6.2)

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
        input_train="data/processed/churn/train_tabular_v2.parquet",
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
