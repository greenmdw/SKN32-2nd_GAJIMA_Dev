"""
고객 이탈 방지 시뮬레이션 페이지 모듈
- render_simulation_page()       : 이탈 기준 선택 목록 페이지
- render_simulation_detail_page(): 선택된 기준별 고객 현황 + 액션 페이지

비즈니스 로직(필터 조건, 액션 정의)은 simulation_logic.py 에 있습니다.
이 파일은 UI 표현(아이콘, 색상, 표시 컬럼)만 담당합니다.
"""

from pathlib import Path

import pandas as pd
import streamlit as st

from simulation_logic import (
    OPTION_REGISTRY,
    ActionType,
    filter_customers,
    build_action_payload,
)

_BASE_DIR = Path(__file__).resolve().parent
_DATA_DIR = _BASE_DIR / "data" / "processed" / "churn"
_EVAL_DIR = _BASE_DIR / "data" / "processed" / "evaluation" / "churn" / "lightgbm"


def _go(page: str) -> None:
    st.session_state.page = page


# ── UI 전용 설정 ───────────────────────────────────────────────────────────────
# 비즈니스 로직(필터 조건, 액션 타입)은 OPTION_REGISTRY 에 있으며,
# 여기서는 화면에 표시할 아이콘·색상·컬럼 정보만 정의합니다.

_ACTION_LABELS: dict[ActionType, tuple[str, str]] = {
    ActionType.EMAIL   : ("이메일 발송",   "재방문 유도 이메일을 발송합니다."),
    ActionType.PUSH    : ("푸시 알림 발송", "앱 재참여 유도 푸시 알림을 발송합니다."),
    ActionType.COUPON  : ("할인 쿠폰 발급", "구매 전환 유도를 위한 할인 쿠폰을 발급합니다."),
    ActionType.DISCOUNT: ("할인 혜택 제공", "맞춤형 할인 혜택 알림을 발송합니다."),
}

_UI_CONFIG: dict[str, dict] = {
    "inactive_4d": {
        "badge"         : "장기 이탈 위험",
        "action_icon"   : "📧",
        "color"         : "#ff6b6b",
        "display_cols"  : ["user_id", "recency_days", "tenure_days", "n_events", "n_sessions"],
        "col_labels"    : {
            "user_id": "사용자 ID", "recency_days": "미접속 일수",
            "tenure_days": "가입일수", "n_events": "이벤트 수", "n_sessions": "세션 수",
        },
        "sort_col"      : "recency_days",
        "sort_asc"      : False,
        "key_stat"      : "recency_days",
        "key_stat_label": "평균 미접속 일수",
    },
    "inactive_3d": {
        "badge"         : "이탈 주의",
        "action_icon"   : "📬",
        "color"         : "#ffa07a",
        "display_cols"  : ["user_id", "recency_days", "tenure_days", "n_events", "n_sessions"],
        "col_labels"    : {
            "user_id": "사용자 ID", "recency_days": "미접속 일수",
            "tenure_days": "가입일수", "n_events": "이벤트 수", "n_sessions": "세션 수",
        },
        "sort_col"      : "recency_days",
        "sort_asc"      : False,
        "key_stat"      : "recency_days",
        "key_stat_label": "평균 미접속 일수",
    },
    "low_activity": {
        "badge"         : "활동 저조",
        "action_icon"   : "🔔",
        "color"         : "#ffd700",
        "display_cols"  : ["user_id", "recency_days", "n_events", "n_sessions", "events_per_session"],
        "col_labels"    : {
            "user_id": "사용자 ID", "recency_days": "미접속 일수",
            "n_events": "이벤트 수", "n_sessions": "세션 수", "events_per_session": "세션당 이벤트",
        },
        "sort_col"      : "n_events",
        "sort_asc"      : True,
        "key_stat"      : "n_events",
        "key_stat_label": "평균 이벤트 수",
    },
    "cart_no_purchase": {
        "badge"         : "구매 전환 필요",
        "action_icon"   : "🛒",
        "color"         : "#c8ff3e",
        "display_cols"  : ["user_id", "n_cart", "n_view", "n_purchase", "avg_price"],
        "col_labels"    : {
            "user_id": "사용자 ID", "n_cart": "장바구니 수",
            "n_view": "조회 수", "n_purchase": "구매 수", "avg_price": "평균 가격(원)",
        },
        "sort_col"      : "n_cart",
        "sort_asc"      : False,
        "key_stat"      : "n_cart",
        "key_stat_label": "평균 장바구니 수",
    },
    "view_no_purchase": {
        "badge"         : "관심 고객",
        "action_icon"   : "👀",
        "color"         : "#4ecdc4",
        "display_cols"  : ["user_id", "n_view", "n_cart", "n_purchase", "avg_price"],
        "col_labels"    : {
            "user_id": "사용자 ID", "n_view": "조회 수",
            "n_cart": "장바구니 수", "n_purchase": "구매 수", "avg_price": "평균 가격(원)",
        },
        "sort_col"      : "n_view",
        "sort_asc"      : False,
        "key_stat"      : "n_view",
        "key_stat_label": "평균 조회 수",
    },
}


def _merged_opt(key: str) -> dict | None:
    """OPTION_REGISTRY 의 비즈니스 정보와 _UI_CONFIG 의 표현 정보를 합쳐서 반환합니다."""
    registry = OPTION_REGISTRY.get(key)
    ui       = _UI_CONFIG.get(key)
    if not registry or not ui:
        return None
    action_label, action_desc = _ACTION_LABELS[registry["action_type"]]
    return {
        "key"         : key,
        "label"       : registry["label"],
        "description" : registry["description"],
        "action_type" : registry["action_type"],
        "action_label": action_label,
        "action_desc" : action_desc,
        **ui,
    }


# ── data ───────────────────────────────────────────────────────────────────────

@st.cache_data
def load_test_data() -> pd.DataFrame:
    test_path = _DATA_DIR / "test_tabular_v2.parquet"
    if not test_path.exists():
        return pd.DataFrame()
    df = pd.read_parquet(test_path)
    pred_path = _EVAL_DIR / "eval_predictions.parquet"
    if pred_path.exists():
        try:
            pred_df = pd.read_parquet(pred_path)
            if (
                "user_id" in pred_df.columns
                and "user_id" in df.columns
                and "churn_proba" in pred_df.columns
            ):
                df = df.merge(pred_df[["user_id", "churn_proba"]], on="user_id", how="left")
        except Exception:
            pass
    return df


# ── page renders ───────────────────────────────────────────────────────────────

def render_simulation_page() -> None:
    """이탈 기준 선택 목록 페이지"""
    st.markdown(
        "<style>.block-container{max-width:720px!important}</style>",
        unsafe_allow_html=True,
    )

    st.markdown('<h2 style="margin-bottom:4px">고객 이탈 방지 시뮬레이션</h2>', unsafe_allow_html=True)
    st.markdown(
        '<p style="color:rgba(245,246,248,0.62);margin-bottom:28px">'
        "이탈 기준을 선택하면 해당 고객 현황과 대응 액션을 확인할 수 있습니다</p>",
        unsafe_allow_html=True,
    )

    for key in OPTION_REGISTRY:
        opt = _merged_opt(key)
        if not opt:
            continue
        col_info, col_btn = st.columns([4, 1])
        with col_info:
            st.markdown(
                f"""<div style="padding:14px 18px;background:rgba(255,255,255,0.04);
                border:1px solid rgba(255,255,255,0.08);border-radius:14px;margin-bottom:8px">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:5px">
                    <span style="font-size:17px">{opt['action_icon']}</span>
                    <span style="font-weight:600;font-size:15px">{opt['label']}</span>
                    <span style="background:{opt['color']}22;color:{opt['color']};
                    font-size:11px;padding:2px 8px;border-radius:20px;font-weight:600">{opt['badge']}</span>
                </div>
                <p style="color:rgba(245,246,248,0.62);font-size:13px;margin:0">{opt['description']}</p>
                </div>""",
                unsafe_allow_html=True,
            )
        with col_btn:
            st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
            if st.button("선택 →", key=f"sim_{key}", use_container_width=True):
                st.session_state.sim_option = key
                _go("simulation_detail")
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("← 대시보드로 돌아가기"):
        _go("dashboard")
        st.rerun()


def render_simulation_detail_page() -> None:
    """선택된 이탈 기준별 고객 현황 + 액션 페이지"""
    st.markdown(
        "<style>.block-container{max-width:960px!important}</style>",
        unsafe_allow_html=True,
    )

    option_key = st.session_state.get("sim_option")
    opt = _merged_opt(option_key)
    if not opt:
        _go("simulation")
        st.rerun()
        return

    with st.spinner("고객 데이터 로딩 중..."):
        df = load_test_data()

    if df.empty:
        st.error("데이터 파일을 찾을 수 없습니다: data/processed/churn/test_tabular_v2.parquet")
        if st.button("← 돌아가기"):
            _go("simulation")
            st.rerun()
        return

    filtered  = filter_customers(df, option_key)   # simulation_logic 필터 사용
    total     = len(filtered)

    # ── 헤더 ─────────────────────────────────────────────────
    col_title, col_back = st.columns([5, 1])
    with col_title:
        st.markdown(
            f"""<div style="display:flex;align-items:center;gap:10px;margin-bottom:4px">
            <span style="font-size:26px">{opt['action_icon']}</span>
            <h2 style="margin:0">{opt['label']}</h2>
            <span style="background:{opt['color']}22;color:{opt['color']};
            font-size:12px;padding:3px 10px;border-radius:20px;font-weight:600">{opt['badge']}</span>
            </div>
            <p style="color:rgba(245,246,248,0.62);margin-bottom:24px">{opt['description']}</p>""",
            unsafe_allow_html=True,
        )
    with col_back:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        if st.button("← 목록", use_container_width=True):
            _go("simulation")
            st.rerun()

    # ── 요약 지표 ─────────────────────────────────────────────
    key_col  = opt["key_stat"]
    key_avg  = filtered[key_col].mean() if (key_col in filtered.columns and total > 0) else 0.0
    has_proba = "churn_proba" in filtered.columns and total > 0

    if has_proba:
        m1, m2, m3 = st.columns(3)
    else:
        m1, m2 = st.columns(2)

    m1.metric("대상 고객 수", f"{total:,}명")
    m2.metric(opt["key_stat_label"], f"{key_avg:.1f}")
    if has_proba:
        m3.metric("평균 이탈 확률", f"{filtered['churn_proba'].mean():.1%}")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 고객 테이블 ───────────────────────────────────────────
    display_cols = [c for c in opt["display_cols"] if c in filtered.columns]
    if has_proba:
        display_cols = display_cols + ["churn_proba"]

    if total > 0 and display_cols:
        sort_col = opt["sort_col"] if opt["sort_col"] in display_cols else display_cols[0]
        show_df  = (
            filtered[display_cols]
            .sort_values(sort_col, ascending=opt["sort_asc"])
            .head(20)
            .copy()
        )
        labels = {**opt["col_labels"], "churn_proba": "이탈 확률"}
        show_df.columns = [labels.get(c, c) for c in show_df.columns]
        st.dataframe(show_df, use_container_width=True, hide_index=True)
        if total > 20:
            st.caption(f"상위 20명 표시 중 (전체 {total:,}명)")
    else:
        st.info("해당 기준에 해당하는 고객이 없습니다.")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 액션 영역 ─────────────────────────────────────────────
    st.markdown(
        f"""<div style="background:rgba(255,255,255,0.04);border:1px solid {opt['color']}44;
        border-radius:14px;padding:18px 20px;margin-bottom:14px">
        <div style="font-weight:600;margin-bottom:4px">{opt['action_icon']} {opt['action_label']}</div>
        <div style="color:rgba(245,246,248,0.62);font-size:13px">{opt['action_desc']}</div>
        </div>""",
        unsafe_allow_html=True,
    )

    col_act, col_dl = st.columns([2, 1])
    with col_act:
        btn_label = (
            f"{opt['action_icon']} {opt['action_label']} ({total:,}명)"
            if total > 0
            else f"{opt['action_icon']} {opt['action_label']}"
        )
        if st.button(btn_label, use_container_width=True, disabled=(total == 0), type="primary"):
            payload = build_action_payload(filtered, option_key)  # simulation_logic 액션 빌더 사용
            st.success(f"✅ {payload.user_count:,}명 고객에게 {opt['action_label']} 완료!")
            with st.expander("백엔드 전달 payload 확인"):
                st.json(payload.request)

    with col_dl:
        if total > 0 and display_cols:
            csv_data = filtered[display_cols].to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "⬇ CSV 다운로드",
                data=csv_data,
                file_name=f"{option_key}_targets.csv",
                mime="text/csv",
                use_container_width=True,
            )
