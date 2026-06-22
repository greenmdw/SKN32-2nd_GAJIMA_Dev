"""
simulation_logic.py
====================
고객 이탈 방지 시뮬레이션 — 백엔드 인계용 순수 로직 모듈
Streamlit 등 UI 프레임워크 의존성 없음. pandas 만 사용.

==========================================================================
[백엔드 팀 구현 필요 API]

  POST /api/actions/email
    Request  : { "user_ids": ["u1", "u2", ...], "template": str }
    Response : { "sent_count": int, "failed_ids": [...] }

  POST /api/actions/push
    Request  : { "user_ids": ["u1", "u2", ...], "template": str }
    Response : { "sent_count": int, "failed_ids": [...] }

  POST /api/actions/coupon
    Request  : { "targets": [{ "user_id": str, "grade": "20%" | "10%" | "5%" }, ...] }
    Response : { "issued_count": int, "failed_ids": [...] }

  POST /api/actions/discount
    Request  : { "user_ids": ["u1", "u2", ...], "discount_type": str }
    Response : { "sent_count": int, "failed_ids": [...] }
==========================================================================

[입력 데이터 스펙]  (test_tabular_v2.parquet 기준)

  필수 컬럼
  ┌─────────────────┬──────────┬────────────────────────────────────┐
  │ 컬럼명          │ 타입     │ 설명                               │
  ├─────────────────┼──────────┼────────────────────────────────────┤
  │ user_id         │ str/int  │ 고객 고유 ID                       │
  │ recency_days    │ int      │ 마지막 활동으로부터 경과 일수       │
  │ n_events        │ int      │ 전체 이벤트 수                     │
  │ n_view          │ int      │ 상품 조회 수                       │
  │ n_cart          │ int      │ 장바구니 추가 수                   │
  │ n_purchase      │ int      │ 구매 수                            │
  │ n_sessions      │ int      │ 세션 수                            │
  │ avg_price       │ float    │ 조회 상품 평균 가격                │
  │ tenure_days     │ int      │ 가입 후 경과 일수                  │
  ├─────────────────┼──────────┼────────────────────────────────────┤
  │ churn_proba     │ float    │ 이탈 예측 확률 (0~1, 선택)         │
  └─────────────────┴──────────┴────────────────────────────────────┘
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import pandas as pd


# ── 액션 타입 ──────────────────────────────────────────────────────────────────

class ActionType(str, Enum):
    EMAIL    = "email"
    PUSH     = "push"
    COUPON   = "coupon"
    DISCOUNT = "discount"


# ── 옵션 레지스트리 ────────────────────────────────────────────────────────────
#
# 각 key는 프론트엔드 sim_option 값과 일치해야 합니다.
# filter_spec 은 직렬화 가능한 dict 으로 정의하여 DB 저장 / API 전달에 사용 가능.

OPTION_REGISTRY: dict[str, dict[str, Any]] = {
    "inactive_4d": {
        "label"           : "4일 미접속",
        "description"     : "최근 4일 이상 접속 기록이 없는 고객",
        "required_columns": ["user_id", "recency_days"],
        "filter_spec"     : {"column": "recency_days", "op": "gte", "value": 4},
        "action_type"     : ActionType.EMAIL,
        "action_params"   : {"template": "reactivation_long"},
    },
    "inactive_3d": {
        "label"           : "3일 미접속",
        "description"     : "최근 3일 이상 접속 기록이 없는 고객",
        "required_columns": ["user_id", "recency_days"],
        "filter_spec"     : {"column": "recency_days", "op": "gte", "value": 3},
        "action_type"     : ActionType.EMAIL,
        "action_params"   : {"template": "reactivation_short"},
    },
    "low_activity": {
        "label"           : "어제 접속 후 활동 없음",
        "description"     : "어제 접속했지만 이벤트가 2건 이하인 고객",
        "required_columns": ["user_id", "recency_days", "n_events"],
        # 복합 조건: recency_days == 1 AND n_events <= 2
        "filter_spec"     : {
            "op"  : "and",
            "conditions": [
                {"column": "recency_days", "op": "eq",  "value": 1},
                {"column": "n_events",     "op": "lte", "value": 2},
            ],
        },
        "action_type"     : ActionType.PUSH,
        "action_params"   : {"template": "re_engagement"},
    },
    "cart_no_purchase": {
        "label"           : "장바구니 담기 후 미구매",
        "description"     : "장바구니에 2개 이상 담았으나 구매하지 않은 고객",
        "required_columns": ["user_id", "n_cart", "n_purchase"],
        "filter_spec"     : {
            "op"  : "and",
            "conditions": [
                {"column": "n_cart",     "op": "gte", "value": 2},
                {"column": "n_purchase", "op": "eq",  "value": 0},
            ],
        },
        "action_type"     : ActionType.COUPON,
        "action_params"   : {},  # 쿠폰 등급은 build_action_payload() 에서 동적으로 결정
    },
    "view_no_purchase": {
        "label"           : "제품 조회 후 미구매",
        "description"     : "제품 상세페이지를 3회 이상 조회했지만 구매하지 않은 고객",
        "required_columns": ["user_id", "n_view", "n_purchase"],
        "filter_spec"     : {
            "op"  : "and",
            "conditions": [
                {"column": "n_view",     "op": "gte", "value": 3},
                {"column": "n_purchase", "op": "eq",  "value": 0},
            ],
        },
        "action_type"     : ActionType.DISCOUNT,
        "action_params"   : {"discount_type": "product_view_incentive"},
    },
}


# ── 쿠폰 등급 ──────────────────────────────────────────────────────────────────

def assign_coupon_grade(churn_proba: float) -> str:
    """이탈 확률에 따라 쿠폰 등급을 반환합니다.

    Returns:
        "20%"  — 긴급 (이탈 확률 80% 이상)
        "10%"  — 주의 (이탈 확률 60~80%)
        "5%"   — 관심 (이탈 확률 60% 미만)
    """
    if churn_proba >= 0.80:
        return "20%"
    if churn_proba >= 0.60:
        return "10%"
    return "5%"


# ── 필터링 ─────────────────────────────────────────────────────────────────────

def filter_customers(df: pd.DataFrame, option_key: str) -> pd.DataFrame:
    """선택된 이탈 기준 key로 고객 DataFrame을 필터링합니다.

    Args:
        df         : 입력 고객 데이터 (필수 컬럼이 모두 포함되어야 함)
        option_key : OPTION_REGISTRY 의 key 값

    Returns:
        필터링된 DataFrame (원본 인덱스 유지).
        필수 컬럼이 없거나 key가 유효하지 않으면 빈 DataFrame 반환.

    Example:
        df = pd.read_parquet("test_tabular_v2.parquet")
        targets = filter_customers(df, "cart_no_purchase")
        print(targets[["user_id", "n_cart"]].head())
    """
    if option_key not in OPTION_REGISTRY:
        return df.iloc[0:0]

    config = OPTION_REGISTRY[option_key]
    required = config["required_columns"]
    if not set(required).issubset(df.columns):
        missing = set(required) - set(df.columns)
        raise ValueError(f"[{option_key}] 필수 컬럼 누락: {missing}")

    mask = _build_mask(df, config["filter_spec"])
    return df[mask].copy()


def _build_mask(df: pd.DataFrame, spec: dict) -> pd.Series:
    """filter_spec dict를 pandas boolean mask로 변환합니다."""
    op = spec["op"]

    if op == "and":
        mask = pd.Series(True, index=df.index)
        for cond in spec["conditions"]:
            mask &= _build_mask(df, cond)
        return mask

    if op == "or":
        mask = pd.Series(False, index=df.index)
        for cond in spec["conditions"]:
            mask |= _build_mask(df, cond)
        return mask

    col, val = spec["column"], spec["value"]
    if op == "eq":  return df[col] == val
    if op == "gte": return df[col] >= val
    if op == "lte": return df[col] <= val
    if op == "gt":  return df[col] >  val
    if op == "lt":  return df[col] <  val

    raise ValueError(f"지원하지 않는 연산자: {op}")


# ── 액션 페이로드 빌더 ─────────────────────────────────────────────────────────

@dataclass
class ActionPayload:
    """백엔드 API에 전달할 액션 페이로드.

    Attributes:
        option_key  : 시뮬레이션 옵션 key
        action_type : ActionType enum
        user_count  : 대상 고객 수
        request     : 백엔드 API body로 그대로 전달 가능한 dict
    """
    option_key  : str
    action_type : ActionType
    user_count  : int
    request     : dict[str, Any] = field(default_factory=dict)


def build_action_payload(filtered_df: pd.DataFrame, option_key: str) -> ActionPayload:
    """필터링된 고객 DataFrame으로 백엔드 전달용 ActionPayload를 생성합니다.

    Args:
        filtered_df : filter_customers() 의 반환값
        option_key  : OPTION_REGISTRY 의 key 값

    Returns:
        ActionPayload — .request 를 해당 API endpoint 에 POST하면 됩니다.

    Example:
        df       = pd.read_parquet("test_tabular_v2.parquet")
        targets  = filter_customers(df, "cart_no_purchase")
        payload  = build_action_payload(targets, "cart_no_purchase")
        # requests.post("/api/actions/coupon", json=payload.request)
    """
    if option_key not in OPTION_REGISTRY:
        raise ValueError(f"알 수 없는 option_key: {option_key}")

    config      = OPTION_REGISTRY[option_key]
    action_type = config["action_type"]
    user_ids    = filtered_df["user_id"].astype(str).tolist()

    if action_type == ActionType.EMAIL:
        request = {
            "user_ids": user_ids,
            "template": config["action_params"]["template"],
        }

    elif action_type == ActionType.PUSH:
        request = {
            "user_ids": user_ids,
            "template": config["action_params"]["template"],
        }

    elif action_type == ActionType.COUPON:
        # 이탈 확률이 있으면 등급 분류, 없으면 기본 등급(10%) 적용
        if "churn_proba" in filtered_df.columns:
            targets = [
                {"user_id": str(row.user_id), "grade": assign_coupon_grade(row.churn_proba)}
                for row in filtered_df[["user_id", "churn_proba"]].itertuples(index=False)
            ]
        else:
            targets = [{"user_id": str(uid), "grade": "10%"} for uid in user_ids]
        request = {"targets": targets}

    elif action_type == ActionType.DISCOUNT:
        request = {
            "user_ids"     : user_ids,
            "discount_type": config["action_params"]["discount_type"],
        }

    else:
        raise ValueError(f"지원하지 않는 ActionType: {action_type}")

    return ActionPayload(
        option_key  = option_key,
        action_type = action_type,
        user_count  = len(user_ids),
        request     = request,
    )


# ── 유틸 ───────────────────────────────────────────────────────────────────────

def get_option_info(option_key: str) -> dict[str, Any]:
    """단일 옵션의 메타 정보를 반환합니다."""
    if option_key not in OPTION_REGISTRY:
        raise KeyError(f"알 수 없는 option_key: {option_key}")
    return OPTION_REGISTRY[option_key]


def list_options() -> list[dict[str, str]]:
    """모든 옵션의 key/label/action_type 목록을 반환합니다."""
    return [
        {
            "key"        : k,
            "label"      : v["label"],
            "action_type": v["action_type"].value,
        }
        for k, v in OPTION_REGISTRY.items()
    ]
