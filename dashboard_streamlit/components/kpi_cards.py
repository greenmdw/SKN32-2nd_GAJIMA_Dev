# -*- coding: utf-8 -*-
"""components/kpi_cards — KPI metric 카드(19-4 §7.2)."""
import streamlit as st


def render(summary):
    """summary = /dashboard/summary data. best_model/best_auc/models."""
    best = summary.get("best_model", "-")
    auc = summary.get("best_auc")
    n_models = len(summary.get("models", []))
    c1, c2, c3 = st.columns(3)
    c1.metric("최고 모델 (ROC-AUC)", str(best), f"{auc:.4f}" if isinstance(auc, (int, float)) else "-")
    c2.metric("등록 모델 수", f"{n_models}개")
    c3.metric("예측 의미", "향후 7일 이탈확률", help=summary.get("title", ""))
