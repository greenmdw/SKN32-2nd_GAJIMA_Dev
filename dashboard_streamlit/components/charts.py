# -*- coding: utf-8 -*-
"""components/charts — 차트 렌더(19-4 §8·§9 / 19-5 §15).
1순위: 백엔드 chart JSON(행리스트) 렌더(`render_chart_json`).
보조: 관리자 진단 등 풍부한 시각화는 chart_service(eval 파일, 개발 허용)."""
import pandas as pd
import altair as alt
import streamlit as st
from services import chart_service as cs


# ---------- 백엔드 chart JSON(19-4 §9) 렌더 ----------
def render_chart_json(res, title=None):
    """res = api_client 봉투. data = {chart_name,chart_type,x,y,data:[rows],...}."""
    if not res or not res.get("ok"):
        st.info("데이터를 불러오지 못했습니다."); return
    chart = res["data"]
    rows = chart.get("data") or []
    if not rows:
        st.info(f"{title or chart.get('chart_name','')}: 표시할 데이터 없음(산출물 대기)"); return
    df = pd.DataFrame(rows)
    ctype, x, y = chart.get("chart_type"), chart.get("x"), chart.get("y")
    if title:
        st.caption(title)
    ys = y if isinstance(y, list) else [y]
    try:
        if ctype == "line":
            long = df.melt(id_vars=[x], value_vars=[c for c in ys if c in df.columns],
                           var_name="series", value_name="value")
            ch = alt.Chart(long).mark_line().encode(x=x, y="value", color="series")
        elif ctype in ("bar", "histogram"):
            yy = ys[0]
            ch = alt.Chart(df).mark_bar().encode(x=x, y=yy)
        elif ctype == "matrix":
            ch = alt.Chart(df).mark_rect().encode(x=f"{x}:O", y=f"{chart.get('y')}:O",
                                                  color="count:Q")
        else:
            st.dataframe(df, use_container_width=True); return
        st.altair_chart(ch, use_container_width=True)
    except Exception:
        st.dataframe(df, use_container_width=True)


# ---------- chart_service 보조(관리자 진단 등) ----------
def _show(chart, msg="데이터 없음(eval 산출물 확인)"):
    st.info(msg) if chart is None else st.altair_chart(chart, use_container_width=True)


def render_baseline_comparison():
    df = cs.comparison_table()
    if df.empty:
        st.info("metrics 없음"); return
    st.dataframe(df.style.highlight_max(subset=["ROC_AUC", "PR_AUC", "Recall", "F1"], color="#D7E3F4")
                 .highlight_min(subset=["Brier", "ECE"], color="#D7E3F4"), use_container_width=True)


def render_auc_bar(): _show(cs.chart_auc_bar())
def render_roc(models): _show(cs.chart_roc(models))
def render_pr(models): _show(cs.chart_pr(models))
def render_calibration(models): _show(cs.chart_calibration(models))
def render_threshold(model): _show(cs.chart_threshold(model))
def render_score_distribution(model): _show(cs.chart_score_dist(model))
def render_lift(model): _show(cs.chart_lift(model))
def render_data_distribution(col): _show(cs.chart_data_distribution(col))
def render_shap_summary(model): _show(cs.chart_shap(model), "중요도 산출물 없음")
def render_value_at_risk(model): _show(cs.chart_var_treemap(model))
def render_session_replay(events): _show(cs.chart_session_replay(events))


def render_confusion_matrix(model):
    cm = cs.confusion(model)
    st.table(cm) if cm is not None else st.info("confusion 없음")
