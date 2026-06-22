
import pandas as pd
import lightgbm as lgb
import matplotlib.pyplot as plt
import matplotlib

matplotlib.rcParams['font.family'] = 'Malgun Gothic'
matplotlib.rcParams['axes.unicode_minus'] = False

# --- 데이터 로드 ---
LGBM_TRAIN_PATH = r'c:\SKN_2nd_pj\data\processed\churn\train_tabular_v2.parquet'
LGBM_TEST_PATH  = r'c:\SKN_2nd_pj\data\processed\churn\test_tabular_v2.parquet'

lgbm_train_df = pd.read_parquet(LGBM_TRAIN_PATH)
for col in lgbm_train_df.select_dtypes(include='object').columns:
    lgbm_train_df[col] = lgbm_train_df[col].astype('category')

lgbm_test_df = pd.read_parquet(LGBM_TEST_PATH)
for col in lgbm_test_df.select_dtypes(include='object').columns:
    lgbm_test_df[col] = lgbm_test_df[col].astype('category')

# --- 피처 엔지니어링 ---
def add_features(df):
    df = df.copy()
    df['cart_to_view_ratio']     = df['n_cart']             / (df['n_view'] + 1)
    df['purchase_to_cart_ratio'] = df['n_purchase']         / (df['n_cart'] + 1)
    df['remove_to_cart_ratio']   = df['n_remove_from_cart'] / (df['n_cart'] + 1)
    df['activity_per_day']       = df['n_events']           / (df['ndays'] + 1)
    df['price_range']            = df['max_price']          - df['min_price']
    df['session_depth']          = df['n_events']           / (df['n_sessions'] + 1)
    return df

TARGET_COLUMN = 'churn'
DROP_COLUMNS  = [TARGET_COLUMN, 'user_id', 'churn_no_purchase']

drop_cols        = [c for c in DROP_COLUMNS if c in lgbm_train_df.columns]
X_train_lgbm_raw = add_features(lgbm_train_df.drop(columns=drop_cols))
y_train_lgbm_raw = lgbm_train_df[TARGET_COLUMN]

test_base    = lgbm_test_df.drop(columns=[TARGET_COLUMN, 'churn_no_purchase', 'user_id'], errors='ignore')
feature_cols = X_train_lgbm_raw.columns.tolist()
X_test = add_features(test_base)[feature_cols]
y_test = lgbm_test_df[TARGET_COLUMN]

# --- 언더샘플링 (이탈 90% 비율) ---
train_all = X_train_lgbm_raw.copy()
train_all['__target__'] = y_train_lgbm_raw.values
churn_df   = train_all[train_all['__target__'] == 1]
nochurn_df = train_all[train_all['__target__'] == 0]
churn_sampled  = churn_df.sample(n=min(len(nochurn_df) * 9, len(churn_df)), random_state=42)
train_balanced = pd.concat([churn_sampled, nochurn_df]).sample(frac=1, random_state=42)
X_train = train_balanced.drop(columns=['__target__'])
y_train  = train_balanced['__target__']

# --- 모델 학습 ---
best_lgbm_model = lgb.LGBMClassifier(
    objective='binary', random_state=42, n_jobs=-1,
    n_estimators=500, learning_rate=0.05,
    num_leaves=63, max_depth=-1,
    min_child_samples=50, subsample=0.8,
    colsample_bytree=0.8, reg_alpha=0.1, reg_lambda=0.1,
    verbose=-1
)
best_lgbm_model.fit(X_train, y_train)


# === 장바구니 2개 이상 고객 대상 이탈 방지 할인 쿠폰 대상자 식별 ===
print("=" * 60)
print("  장바구니 2개 이상 고객 대상 이탈 방지 할인 쿠폰 대상자 식별")
print("=" * 60)

coupon_df = lgbm_test_df[['user_id', 'n_cart', 'churn']].copy()
coupon_df['churn_proba'] = best_lgbm_model.predict_proba(X_test)[:, 1]
coupon_df['churn_pred']  = best_lgbm_model.predict(X_test)

high_cart_df = coupon_df[coupon_df['n_cart'] >= 2].copy()

print(f"\n[대상 고객 현황]")
print(f"  n_cart >= 2 전체 고객 수 : {len(high_cart_df):,}명")
print(f"  이탈 예측 고객           : {(high_cart_df['churn_pred'] == 1).sum():,}명")
print(f"  비이탈 예측 고객         : {(high_cart_df['churn_pred'] == 0).sum():,}명")

def assign_coupon(prob):
    if prob >= 0.8:
        return '20% 할인 (긴급)'
    elif prob >= 0.6:
        return '10% 할인 (주의)'
    else:
        return '5% 할인 (관심)'

high_cart_df['coupon_grade'] = high_cart_df['churn_proba'].apply(assign_coupon)
coupon_targets = high_cart_df[high_cart_df['churn_pred'] == 1].sort_values('churn_proba', ascending=False)

print(f"\n[쿠폰 지급 대상자: 총 {len(coupon_targets):,}명]")
print(f"  20% 할인 (긴급) - 이탈 확률 80% 이상 : {(coupon_targets['coupon_grade'] == '20% 할인 (긴급)').sum():,}명")
print(f"  10% 할인 (주의) - 이탈 확률 60~80%   : {(coupon_targets['coupon_grade'] == '10% 할인 (주의)').sum():,}명")
print(f"   5% 할인 (관심) - 이탈 확률 50~60%   : {(coupon_targets['coupon_grade'] == '5% 할인 (관심)').sum():,}명")

print(f"\n[이탈 확률 상위 10명]")
print(coupon_targets[['user_id', 'n_cart', 'churn_proba', 'coupon_grade']].head(10).to_markdown(index=False))

OUTPUT_PATH = r'c:\SKN_2nd_pj\coupon_targets.csv'
coupon_targets.to_csv(OUTPUT_PATH, index=False)
print(f"\n쿠폰 대상자 목록 저장 완료 → {OUTPUT_PATH}")
print("=" * 60)

# --- 시각화 ---
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

axes[0].hist(high_cart_df['churn_proba'], bins=50, color='steelblue', edgecolor='white')
axes[0].set_title('n_cart >= 2 고객 이탈 확률 분포')
axes[0].set_xlabel('이탈 확률')
axes[0].set_ylabel('고객 수')
axes[0].axvline(0.5, color='red', linestyle='--', label='임계값 0.5')
axes[0].legend()

coupon_targets['coupon_grade'].value_counts().plot(
    kind='bar', ax=axes[1], color=['#d32f2f', '#f57c00', '#388e3c'], edgecolor='white'
)
axes[1].set_title('쿠폰 등급별 대상 고객 수')
axes[1].set_xlabel('쿠폰 등급')
axes[1].set_ylabel('고객 수')
axes[1].tick_params(axis='x', rotation=15)

plt.tight_layout()
plt.show()
