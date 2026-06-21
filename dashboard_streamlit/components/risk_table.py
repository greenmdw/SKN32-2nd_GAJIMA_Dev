# -*- coding: utf-8 -*-
"""components/risk_table — 고위험 고객 테이블(19-4 §7.2)."""
import streamlit as st
import pandas as pd


def render(rows):
    """rows = top-risk users 리스트(또는 {'users':[...]} / {'rows':[...]})."""
    if isinstance(rows, dict):
        rows = rows.get("users") or rows.get("rows") or []
    if not rows:
        st.info("고위험 고객 데이터가 없습니다.")
        return
    df = pd.DataFrame(rows)
    cols = [c for c in ["user_id", "churn_probability", "risk_level",
                        "recommended_action", "created_at"] if c in df.columns]
    st.dataframe(df[cols] if cols else df, use_container_width=True)
