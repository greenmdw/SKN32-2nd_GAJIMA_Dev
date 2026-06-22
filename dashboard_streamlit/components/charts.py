import pandas as pd
import streamlit as st


def render_chart_payload(payload: dict) -> None:
    title = payload.get("title") or payload.get("chart_name", "chart")
    st.subheader(title)
    data = payload.get("data")
    chart_type = payload.get("chart_type")
    # 이미지/단일 객체 차트(예: system-architecture → {asset_path})는 행리스트가 아니므로
    # pd.DataFrame 으로 그리면 'all scalar values' 오류. chart_type 으로 분기한다.
    if chart_type == "image" or isinstance(data, dict):
        asset = data.get("asset_path") if isinstance(data, dict) else None
        if asset:
            st.caption(f"🖼️ 다이어그램 asset: `{asset}`")
        else:
            st.json(data or {})
        return
    if not data:
        st.info("차트 데이터가 없습니다.")
        return
    st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
