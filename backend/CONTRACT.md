# 백엔드 I/O 계약 (19-2 §7.4 — 불변)

서버 실행체가 Node→FastAPI로 바뀌어도 **팀 간 외부 계약은 유지**된다. 모델팀·대시보드팀·시뮬팀이 맞추는 인터페이스는 그대로다.

## 1. 모델 제출 — `POST /models/submit`
헤더: `x-api-key: <API_KEY>`
```json
{
  "model_name": "CatBoost_Churn_v2",
  "model_type": "tree",                  // tree|linear|sequence|ensemble
  "feature_schema_version": "v2",
  "label_name": "churn",
  "horizon_days": 7,
  "preprocessing_config": { "scale": "none", "feature_order": ["recency_days","tenure_days","ndays","n_events","n_view","n_cart","n_remove_from_cart","n_purchase","avg_price","purch_amt"] },
  "dataset_path": "data/processed/churn/models7",
  "artifact_path": "models/preprocessors/prep_CatBoost_v2.joblib",
  "metrics": { "roc_auc": 0.791, "pr_auc": 0.9347, "best_threshold": 0.49, "best_f1": 0.9182 },
  "evaluation": { "eval_predictions_path": "...eval_predictions.parquet", "shap_summary_path": "...feature_importance.json" },
  "is_active": true
}
```
응답: `{ "model_id": n, "eval_id": n, "mode": "mysql|memory" }`
- `is_active=true`면 같은 `model_type`의 기존 active 해제(레지스트리 단일 active 보장).

## 2. 차트 — `GET /models/{model}/charts/{name}`
`name ∈ {roc, pr, threshold, calibration, shap, feature_importance}`
응답: `{ "model", "chart", "data": <chart-ready JSON> }`
- 차트 원천 = 학습 종료 시점 산출물 파일(`data/processed/evaluation/*`). 백엔드는 재학습하지 않는다.
- `shap` 요청 시 `shap_summary.json` 없으면 `feature_importance.json`으로 자동 폴백(26-8).

## 3. 예측 — `POST /predict`
`{ "user_id", "churn_probability", "model_id" }` → `{ user_id, churn_probability, risk_level, recommended_action, horizon_days:7 }`
- 위험등급: `>=0.65 high`, `>=0.35 medium`, else `low`.
- **예측 의미 = 현재 행동 기준 향후 7일 동안 이벤트 0개일 확률.**

## 4. 운영 조회
- `GET /predictions/top-risk?limit&min_prob` → 유저별 최신 예측을 이탈확률 desc.
- `GET /predictions/latest?user_id` → 유저 최신 1건.
- `GET /dashboard/summary` → 7모델 비교(best_model/best_auc/models[]).

## 5. 대용량 데이터 원칙
`parquet/npz/model` artifact는 **DB 밖 파일**, DB엔 경로만 저장(19-2 §6.3).
