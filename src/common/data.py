"""공통 데이터 로딩.

입력 정본은 19-3 §3 스키마를 따른다. 실제 파일은 레포의 `processed_5m/`에 있다.
- 트리 모델(DecisionTree/XGBoost): recency<=7 코호트 raw tabular
- Transformer: recency<=7 코호트 raw 시퀀스(seq_len=4)
"""
import os
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler, RobustScaler, StandardScaler

# src/common/data.py -> parents[2] = 레포 루트
ROOT = Path(__file__).resolve().parents[2]
# 로컬 기본값은 레포의 processed_5m/. Colab 등에서는 CHURN_DATA_DIR 환경변수로
# Google Drive 경로를 지정하면 코드 수정 없이 데이터 위치만 바꿀 수 있다.
DATA_DIR = Path(os.environ.get("CHURN_DATA_DIR", ROOT / "processed_5m"))

# 19-3 §3.1 — feature 순서 고정. user_id는 feature 금지, churn이 target.
FEATURE_ORDER = [
    "recency_days",
    "tenure_days",
    "ndays",
    "n_events",
    "n_view",
    "n_cart",
    "n_remove_from_cart",
    "n_purchase",
    "avg_price",
    "purch_amt",
]
TARGET = "churn"
ID_COL = "user_id"

# 시퀀스 채널(19-3 §3.3, 17-5-1: view/cart/purchase 계열)
SEQ_FEATURES = ["view", "cart", "purchase"]

# === v2 (22피처) — 전처리팀 v4 산출물 (data/processed/churn) ===
# 기존 10피처 + category/brand/session/price 12피처. 범주형 ID는 제외된 순수 숫자형.
V2_DIR = ROOT / "data" / "processed" / "churn"
V2_MODELS7 = V2_DIR / "models7"
FEATURE_ORDER_V2 = FEATURE_ORDER + [
    "min_price",
    "max_price",
    "std_price",
    "purchase_avg_price",
    "remove_ratio",
    "cart_purchase_ratio",
    "n_categories",
    "cat_entropy",
    "n_brands",
    "brand_loyalty",
    "n_sessions",
    "events_per_session",
]
# model_key -> models7 파일 접두어 (CamelCase)
V2_FILE = {
    "decisiontree": "DecisionTree",
    "xgboost": "XGBoost",
    "randomforest": "RandomForest",
    "logreg": "LogReg",
    "catboost": "CatBoost",
    "lightgbm": "LightGBM",
}


def make_scaler(name):
    """전처리 config의 scaler 이름 -> sklearn 변환기 (none은 None)."""
    return {
        "none": None,
        "robust": RobustScaler(),
        "standard": StandardScaler(),
        "minmax": MinMaxScaler(),
    }[name]


def load_tabular(path):
    """tabular parquet -> (X[float64, 컬럼순서 고정], y[int32], user_id[int64])."""
    df = pd.read_parquet(path)
    X = df[FEATURE_ORDER].astype("float64")
    y = df[TARGET].astype("int32")
    uid = df[ID_COL].astype("int64")
    return X, y, uid


def load_sequence(path):
    """시퀀스 npz -> (X[float32, (N, seq_len, n_features)], y[int32], user_id[int64])."""
    z = np.load(path)
    X = z["X"].astype("float32")
    y = z["churn"].astype("int32")
    uid = z["user_id"].astype("int64")
    return X, y, uid


def load_tabular_v2(model_key):
    """v2 22피처 로드 -> (X_tr, y_tr, uid_tr), (X_te, y_te, uid_te).

    train: models7/{Model}_v2_train.parquet (recency<=7 코호트)
    test : test_tabular_v2.parquet 에서 cohort_recency7==1 로 코호트 필터
    """
    name = V2_FILE[model_key]
    tr = pd.read_parquet(V2_MODELS7 / f"{name}_v2_train.parquet")
    te = pd.read_parquet(V2_DIR / "test_tabular_v2.parquet")
    te = te[te["cohort_recency7"] == 1]

    def split(df):
        return (
            df[FEATURE_ORDER_V2].astype("float64"),
            df[TARGET].astype("int32"),
            df[ID_COL].astype("int64"),
        )

    return split(tr), split(te)
