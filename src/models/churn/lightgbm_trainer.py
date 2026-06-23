
import os
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, precision_score, recall_score, f1_score, roc_auc_score, auc, ConfusionMatrixDisplay
import lightgbm as lgb
import time
import json
import matplotlib.pyplot as plt

print("라이브러리 불러오기 완료.")

# Define path for LightGBM training file
LGBM_TRAIN_PATH = '/content/LightGBM_v2_train.parquet'

try:
    # Load LightGBM training data
    if not os.path.exists(LGBM_TRAIN_PATH):
        print(f"경고: '{LGBM_TRAIN_PATH}' 파일을 찾을 수 없습니다. 더미 데이터를 생성합니다.")
        dummy_data = {
            'feature_1': [i for i in range(100)],
            'feature_2': [i * 1.5 for i in range(100)],
            'churn': [i % 2 for i in range(100)],
            'user_id': [f'user_{i}' for i in range(100)]
        }
        lgbm_train_df = pd.DataFrame(dummy_data)
        lgbm_train_df.to_parquet(LGBM_TRAIN_PATH)
        print(f"더미 LightGBM 훈련 데이터 '{LGBM_TRAIN_PATH}' 생성 완료.")

    lgbm_train_df = pd.read_parquet(LGBM_TRAIN_PATH)
    print(f"LightGBM 훈련 데이터 로드 완료. 크기: {lgbm_train_df.shape}")

except FileNotFoundError as e:
    print(e)
except Exception as e:
    print(f"데이터 로드 중 오류가 발생했습니다: {e}")

TARGET_COLUMN = 'churn'

if TARGET_COLUMN in lgbm_train_df.columns:
    X_train_lgbm_raw = lgbm_train_df.drop(columns=[TARGET_COLUMN, 'user_id'], errors='ignore')
    y_train_lgbm_raw = lgbm_train_df[TARGET_COLUMN]
    print(f"LightGBM 훈련 특성(X_train_lgbm_raw)과 타겟(y_train_lgbm_raw) 분리 완료. Shape: {X_train_lgbm_raw.shape}")
else:
    print(f"오류: LightGBM 훈련 데이터에서 타겟 컬럼 '{TARGET_COLUMN}'을(를) 찾을 수 없습니다.")

X_test = pd.DataFrame()
y_test = pd.Series()
print("주의: 새로운 파일에 대한 테스트 데이터가 제공되지 않았습니다. 최종 테스트를 위해 별도로 로드해야 합니다.")

X_train_split_lgbm, X_val_lgbm, y_train_split_lgbm, y_val_lgbm = train_test_split(X_train_lgbm_raw, y_train_lgbm_raw, test_size=0.05, random_state=43, stratify=y_train_lgbm_raw)
print(f"LightGBM 훈련 세트: {X_train_split_lgbm.shape}, 검증 세트: {X_val_lgbm.shape}")

lgbm_model = lgb.LGBMClassifier(objective='binary', random_state=42, n_jobs=-1)

start_time_lgbm = time.time()
lgbm_model.fit(X_train_split_lgbm, y_train_split_lgbm)
end_time_lgbm = time.time()
lgbm_train_time_sec = end_time_lgbm - start_time_lgbm

print("LightGBM 모델 훈련 완료.")
print(f"LightGBM 모델 학습 시간: {lgbm_train_time_sec:.2f} 초")

y_pred_lgbm_eval = lgbm_model.predict(X_val_lgbm)

print("
--- LightGBM 모델 성능 평가 (검증 세트) ---")

lgbm_accuracy = accuracy_score(y_val_lgbm, y_pred_lgbm_eval)
print(f"LightGBM 모델 정확도 (Accuracy): {lgbm_accuracy:.4f}")

print("
Classification Report (정밀도, 재현율, F1-Score):")
print(classification_report(y_val_lgbm, y_pred_lgbm_eval))

if hasattr(lgbm_model, 'predict_proba'):
    y_proba_lgbm_eval = lgbm_model.predict_proba(X_val_lgbm)
    if y_proba_lgbm_eval.shape[1] == 2:
        y_proba_positive_lgbm_eval = y_proba_lgbm_eval[:, 1]

        try:
            lgbm_roc_auc = roc_auc_score(y_val_lgbm, y_proba_positive_lgbm_eval)
            print(f"ROC AUC: {lgbm_roc_auc:.4f}")
        except ValueError:
            print("ROC AUC를 계산할 수 없습니다. 타겟 클래스 분포를 확인하세요.")

        precision_lgbm_eval, recall_lgbm_eval, _ = precision_recall_curve(y_val_lgbm, y_proba_positive_lgbm_eval)
        lgbm_pr_auc = auc(recall_lgbm_eval, precision_lgbm_eval)
        print(f"PR AUC: {lgbm_pr_auc:.4f}")
    else:
        print("predict_proba가 다중 클래스 예측을 반환합니다. ROC AUC와 PR AUC는 이진 분류에 일반적으로 사용됩니다.")
else:
    print("모델이 확률 예측(predict_proba)을 지원하지 않습니다. ROC AUC와 PR AUC를 계산할 수 없습니다.")

print("
Confusion Matrix (혼동 행렬):")
fig_lgbm_cm, ax_lgbm_cm = plt.subplots(figsize=(6, 6))
ConfusionMatrixDisplay.from_estimator(lgbm_model, X_val_lgbm, y_val_lgbm, cmap=plt.cm.Blues, ax=ax_lgbm_cm)
plt.title('Confusion Matrix (LightGBM Validation Set)')
plt.show()

lgbm_accuracy_final = accuracy_score(y_val_lgbm, y_pred_lgbm_eval)
lgbm_precision_final = precision_score(y_val_lgbm, y_pred_lgbm_eval)
lgbm_recall_final = recall_score(y_val_lgbm, y_pred_lgbm_eval)
lgbm_f1_final = f1_score(y_val_lgbm, y_pred_lgbm_eval)
lgbm_roc_auc_final = roc_auc_score(y_val_lgbm, y_proba_positive_lgbm_eval)
lgbm_pr_auc_final = auc(recall_lgbm_eval, precision_lgbm_eval)

results_df = pd.DataFrame({
    'model': ['LightGBM'],
    'accuracy': [lgbm_accuracy_final],
    'precision': [lgbm_precision_final],
    'recall': [lgbm_recall_final],
    'f1': [lgbm_f1_final],
    'roc_auc': [lgbm_roc_auc_final],
    'pr_auc': [lgbm_pr_auc_final],
    'train_time_sec': [lgbm_train_time_sec]
})

print("
--- LightGBM 모델 성능 요약 (검증 세트) ---")
# display(results_df.round(4)) # Colab 환경이 아니므로 display 대신 print 사용
print(results_df.round(4).to_string())

manifest_data = {
    'model_type': 'LightGBM',
    'target_column': TARGET_COLUMN,
    'feature_columns': X_train_lgbm_raw.columns.tolist(),
    'metrics': results_df.drop(columns=['model']).to_dict(orient='records')[0],
    'training_details': {
        'training_time_seconds': float(lgbm_train_time_sec)
    }
}

MANIFEST_FILE_PATH = 'model_run_manifest.json'

with open(MANIFEST_FILE_PATH, 'w') as f:
    json.dump(manifest_data, f, indent=4)

