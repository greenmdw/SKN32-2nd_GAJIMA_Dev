# -*- coding: utf-8 -*-
"""pages/02_dashboard — 단일 통합 대시보드(19-4 §7.2 / 19-5 §16~17).
데이터는 백엔드 REST(services). 모델 진단 차트는 백엔드 chart JSON(artifact-first)을 render_chart_json으로 그린다.
세션/추천 일부는 chart_service(개발 허용 경로) 보조."""
import streamlit as st
import pandas as pd
from components import layout, kpi_cards, risk_table, charts, error_state
from services import dashboard_service as dsvc
from services import prediction_service as psvc
from services import recommendation_service as rsvc
from services import api_client
from services import chart_service as cs

layout.load_css()
layout.sidebar_user()
layout.require_login()

role = st.session_state.get("role", "customer")
user_id = st.session_state.get("user_id", "demo01")
st.title("Anchor — 실시간 고객 이탈 분석")

# active 모델(차트 파라미터)
act = dsvc.get_active_models()
active_model = "CatBoost"
if act.get("ok") and act["data"].get("models"):
    active_model = act["data"]["models"][0].get("model_name", "CatBoost")

base = ["개요(Overview)", "고객 이탈 조회", "실시간 세션/바운스", "추천(Recommendation)"]
admin_tabs = ["모델 진단(15시각화)", "관리자 로그/이력"]
names = base + (admin_tabs if role == "admin" else [])
tabs = st.tabs(names)

# ── 0. 개요 ── 백엔드 summary + baseline-comparison(REST)
with tabs[0]:
    st.subheader("개요 — 7모델 한눈 비교 (백엔드 REST)")
    summary = error_state.show(dsvc.get_summary(), "요약 없음")
    if summary:
        kpi_cards.render(summary)
    charts.render_chart_json(dsvc.get_dashboard_chart("baseline-comparison"), "베이스라인 비교(PR/ROC/F1)")
    c1, c2 = st.columns(2)
    with c1: charts.render_chart_json(dsvc.get_model_chart(active_model, "roc-auc"), f"ROC — {active_model}")
    with c2: charts.render_chart_json(dsvc.get_model_chart(active_model, "pr-auc"), f"PR — {active_model}")
    st.caption("불균형(이탈 82%)이라 PR-AUC는 높음 → 분별력 주지표는 ROC-AUC.")

# ── 1. 고객 이탈 조회 ── 백엔드 /dashboard/user + /predict
with tabs[1]:
    st.subheader("고객 이탈 조회 · 자동 추천 (백엔드 REST)")
    models = cs.model_list()
    model = st.selectbox("모델", models, index=len(models) - 1, key="cc_model")
    c1, c2 = st.columns(2)
    uid_sel = c1.selectbox("고객 선택(user_id)", cs.sample_user_ids(model), key="cc_user")
    uid_manual = c2.text_input("또는 user_id 직접 입력", "", key="cc_user_manual")
    uid = uid_manual.strip() or str(uid_sel)
    if st.button("이탈 분석 실행"):
        ud = error_state.show(dsvc.get_user(uid), "해당 고객 데이터 없음")
        if ud:
            lp = ud.get("latest_prediction", {})
            d1, d2, d3 = st.columns(3)
            d1.metric("이탈 확률", f"{lp.get('churn_probability',0):.3f}")
            d2.metric("위험 등급", {"high": "고위험", "medium": "중위험", "low": "정상"}.get(lp.get("risk_level"), "-"))
            d3.metric("관심 브랜드", str(lp.get("top_brand", "-")))
            # 추천(백엔드) + 예측 로그 저장(백엔드)
            rec = error_state.show(rsvc.get_recommendations(uid))
            if rec and rec.get("categories"):
                st.markdown("**추천(유사 카테고리)**")
                st.dataframe(pd.DataFrame(rec["categories"]), use_container_width=True)
            res = psvc.predict(uid, float(lp.get("churn_probability", 0)), None)
            st.success("이탈예측을 백엔드(prediction_log)에 저장했습니다.") if res.get("ok") else st.info("백엔드 미연결 — 저장 보류.")

# ── 2. 실시간 세션/바운스 ── chart_service(세션 샘플, 개발 경로)
with tabs[2]:
    st.subheader("실시간 세션 이탈 / 바운스")
    meta = cs.session_bounce_meta(); samples = cs.session_samples()
    if not samples:
        st.info("세션 바운스 산출물 없음")
    else:
        st.caption(f"라벨 {meta.get('label','-')} · 모델 {meta.get('model','-')} · AUC {meta.get('auc','-')}")
        label = {"BOUNCE": "바운스(단발)", "CART_ABANDON": "장바구니 이탈", "PURCHASE": "구매 세션"}
        tag = st.selectbox("시뮬 세션 유형", list(samples), format_func=lambda t: label.get(t, t))
        ev = samples[tag]
        if ev:
            step = 1 if len(ev) == 1 else st.slider("실시간 재생", 1, len(ev), 1)
            upto = ev[:step]; cur = upto[-1]
            e1, e2, e3 = st.columns(3)
            e1.metric("현재 바운스 확률", f"{cur['bounce_prob']:.3f}")
            e2.metric("현재 행동", cur["event"])
            e3.metric("위험", "고위험" if cur["bounce_prob"] >= 0.65 else "관찰" if cur["bounce_prob"] >= 0.35 else "안정")
            charts.render_session_replay(upto)
            if cur["bounce_prob"] >= 0.65:
                st.warning("⚠ 이탈 위험 높음 → 실시간 쿠폰/리마인드 권고")

# ── 3. 추천 ── 백엔드 /recommendations
with tabs[3]:
    st.subheader("추천 — 유사 카테고리(백엔드 REST)")
    ruid = st.text_input("user_id", str(cs.sample_user_ids(active_model)[0]) if cs.sample_user_ids(active_model) else "")
    if st.button("추천 조회") and ruid:
        rec = error_state.show(rsvc.get_recommendations(ruid.strip()), "추천 없음")
        if rec and rec.get("categories"):
            st.dataframe(pd.DataFrame(rec["categories"]), use_container_width=True)
        elif rec:
            st.info("유사 카테고리 없음")

# ── 4·5. 관리자 ── 모델 진단(백엔드 chart JSON) + 로그
if role == "admin":
    with tabs[4]:
        st.subheader("Model Diagnostics — 백엔드 chart JSON(artifact-first)")
        ev = error_state.show(dsvc.get_active_models())
        ms = [m["model_name"] for m in (ev["data"]["models"] if ev else [])] or [active_model]
        one = st.selectbox("모델", ms, index=0)
        grid = [("roc-auc", "ROC"), ("pr-auc", "PR"), ("calibration", "Calibration"),
                ("threshold", "Threshold P/R/F1"), ("score-distribution", "스코어 분포"),
                ("lift", "Lift"), ("confusion-matrix", "Confusion"), ("shap-summary", "피처중요도(SHAP대안)"),
                ("value-at-risk", "Value at Risk"), ("revenue-recovery", "Revenue Recovery")]
        for i in range(0, len(grid), 2):
            cols = st.columns(2)
            for col, (cn, title) in zip(cols, grid[i:i + 2]):
                with col:
                    charts.render_chart_json(dsvc.get_model_chart(one, cn), title)
        st.markdown("#### 데이터 분포(모델 비종속)")
        charts.render_chart_json(dsvc.get_dashboard_chart("data-distribution"), "recency_days 분포")

    with tabs[5]:
        st.subheader("관리자 — 로그 / 예측 이력 (백엔드 REST)")
        a, b = st.columns(2)
        with a:
            st.markdown("**얼굴 로그인 로그(최신 200)**")
            logs = error_state.show(api_client.get("/auth/logins?limit=20"), "로그 없음")
            if logs:
                st.dataframe(pd.DataFrame(logs.get("logins", [])), use_container_width=True)
        with b:
            st.markdown("**고위험 예측 이력(top-risk)**")
            tr = error_state.show(psvc.get_top_risk(20), "예측 이력 없음")
            if tr:
                risk_table.render(tr)
else:
    st.caption("ℹ 모델 진단·로그 이력은 **관리자 전용**입니다. (교육과제 ③)")
