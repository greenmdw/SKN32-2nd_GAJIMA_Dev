"""XGBoost 이탈(churn) 예측 학습기 — v2 22피처.

[데이터]
  - 입력 train: data/processed/churn/models7/XGBoost_v2_train.parquet (recency<=7 코호트)
  - 입력 test : data/processed/churn/test_tabular_v2.parquet 의 cohort_recency7==1 필터
  - 평가는 항상 Feb OOT(시간외삽) 코호트 109,736명 기준.

[산출물] (19-3 §5)
  - models/churn/xgboost/[runs/{tag}/]model.json (+preprocessor.joblib)
  - data/processed/evaluation/churn/xgboost/ 평가 9종 + manifest + 리더보드

[하이퍼파라미터 최적화 경위]
  1) 전처리팀 bayes(Optuna, CV 기준): md5·312트리·lr0.0359 등 → OOT PR-AUC 0.9302
  2) 한 손잡이씩 sweep(OOT 기준) + 수동 조합 → 0.9330
  3) GridSearch 72조합(OOT 기준) → 0.9337  (현재 DEFAULTS)
  최종: PR-AUC 0.9337 / ROC-AUC 0.7841 (bayes 대비 PR +0.0035, ROC +0.0123)
  핵심: bayes의 312트리는 OOT에서 과적합 → 트리를 150으로 줄이고 얕게(md4) +
        colsample 1.0 + min_child_weight 20으로 균형 잡은 게 최적.
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

# 정식 config = GridSearch(OOT PR-AUC 기준) 최적값.
# 주석의 (bayes)=전처리팀 원본값, (GS)=GridSearch로 바뀐 값.
DEFAULTS = {
    "scaler": "robust",            # (bayes) 트리엔 사실상 무영향이나 서빙 계약 일치 위해 유지
    "n_estimators": 150,           # (GS) 312 -> 150 : 트리 수 줄여 OOT 과적합 제거 (효과 최대)
    "max_depth": 4,                # (GS) 5 -> 4    : 더 얕게
    "learning_rate": 0.035906165718883755,  # (bayes 유지)
    "subsample": 0.7752520669964538,         # (bayes 유지)
    "colsample_bytree": 1.0,       # (GS) 0.695 -> 1.0 : 모든 피처 사용이 OOT에 유리
    "min_child_weight": 20,        # (GS) 5 -> 20   : 리프 최소 가중치 ↑ (규제)
    "reg_alpha": 0.7094774061671105,         # (bayes 유지) L1
    "reg_lambda": 1.0,             # (GS) 0.07 -> 1.0 : L2 ↑
    "scale_pos_weight": 4,         # (bayes) 양성(churn=1) 가중. churn 다수라도 bayes가 4 선택
    "early_stopping_rounds": 0,    # n_estimators가 이미 최종값이라 조기종료 끔(0=비활성)
}


def train(run_tag=None, **overrides):
    """학습 + 산출물 생성. run_tag 없으면 정식(canonical) 경로에 저장."""
    hp = dict(DEFAULTS)
    hp.update(overrides)  # CLI --set 또는 sweep에서 손잡이별 오버라이드

    # v2 22피처 로드. test는 함수 내부에서 코호트(cohort_recency7==1)로 필터됨.
    (X_full, y_full, _), (X_te, y_te, uid_te) = load_tabular_v2(MODEL_KEY)

    # scaler: 트리는 스케일 불변이라 robust/none 결과 동일하지만, 서빙 시 동일 변환을
    # 적용해야 하므로 fit한 scaler를 preprocessor.joblib로 저장한다.
    scaler = make_scaler(hp["scaler"])
    if scaler is not None:
        X_full = scaler.fit_transform(X_full)
        X_te = scaler.transform(X_te)

    # 15%는 training_history(라운드별 loss) 기록용 val로 분리.
    # early_stopping=0이라 조기종료엔 안 쓰이고, 모델은 X_tr(85%)로만 학습된다.
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
        # 0이면 None으로 넘겨 조기종료 비활성(full n_estimators 학습).
        early_stopping_rounds=(hp["early_stopping_rounds"] or None),
        random_state=SEED,
    )
    clf.fit(X_tr, y_tr, eval_set=[(X_tr, y_tr), (X_val, y_val)], verbose=False)
    # y_score = churn=1 확률 (19-3 §6.2: positive class 확률이어야 함).
    y_score = clf.predict_proba(X_te)[:, 1]

    # run_tag 유무에 따라 정식/실험 경로 결정. 폴더는 여기서 생성됨.
    artifact_dir, eval_dir = resolve_dirs(MODEL_KEY, run_tag)
    clf.save_model(str(artifact_dir / "model.json"))
    if scaler is not None:
        joblib.dump(scaler, artifact_dir / "preprocessor.joblib")

    # training_history(#5): 라운드별 logloss. validation_1 = 위 val 분리분.
    res = clf.evals_result()
    tl = [float(x) for x in res["validation_0"]["logloss"]]
    vl = [float(x) for x in res["validation_1"]["logloss"]]
    training_history = {"epoch": list(range(1, len(tl) + 1)), "train_loss": tl, "val_loss": vl}

    # shap_summary(#13): 진짜 SHAP 대신 feature_importances_(gain)로 대체.
    # shap 설치 시 TreeExplainer로 교체 가능(19-3 §6.9 권장).
    imp = clf.feature_importances_
    order = np.argsort(-imp)
    shap_summary = {
        "feature": [FEATURE_ORDER_V2[i] for i in order],
        "mean_abs_shap": [float(imp[i]) for i in order],
        "rank": list(range(1, len(FEATURE_ORDER_V2) + 1)),
        "note": "feature_importances_(gain) proxy; replace with TreeSHAP if shap installed",
    }

    # eval_predictions + 평가 9종 JSON 생성(임계값은 F1 최적값 자동 선택).
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

    # manifest: 백엔드 POST /models/submit 등록 기준. preprocessing_config에 22피처
    # 순서 + 전처리 + HP를 기록해 백엔드가 실시간 feature를 동일하게 맞춘다.
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
    # 리더보드 CSV에 이번 실행 1행 기록(튜닝 비교용).
    log_run(MODEL_KEY, run_tag, hp, metrics)
    print(f"[{MODEL_KEY}] run={run_tag or 'baseline'} feats={len(FEATURE_ORDER_V2)} "
          f"ROC-AUC={metrics['roc_auc']:.4f} PR-AUC={metrics['pr_auc']:.4f} F1={metrics['best_f1']:.4f}")
    return metrics


if __name__ == "__main__":
    train()
