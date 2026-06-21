# -*- coding: utf-8 -*-
"""dashboard_streamlit 진입점(19-4 §3). 랜딩 + 세션 초기화 + 공통 layout.
표시 계층 전용: 데이터는 services/api_client → FastAPI 백엔드. DB/파일 직접 접속 안 함(진단 차트는 개발 허용).
실행: cd dashboard_streamlit && streamlit run app.py"""
import streamlit as st
from components import layout

st.set_page_config(page_title="Anchor — 이탈 분석", page_icon="⚓", layout="wide")


def init_session():
    st.session_state.setdefault("is_logged_in", False)
    st.session_state.setdefault("role", "customer")


def main():
    init_session()
    layout.load_css()
    layout.sidebar_user()

    st.markdown(f'<div class="logo">{layout.logo_svg()}</div>', unsafe_allow_html=True)
    st.title("Anchor")
    st.caption("실시간 고객 이탈 분석 시스템 · 향후 7일 이탈확률")

    if st.session_state.get("is_logged_in"):
        st.success(f"로그인됨: {st.session_state.get('display_name','-')} ({st.session_state.get('role')})")
        if st.button("📊 통합 대시보드로 이동", type="primary"):
            st.switch_page("pages/02_dashboard.py")
    else:
        st.info("좌측 사이드바의 **01 face login** 페이지에서 얼굴/아이디 로그인 후 대시보드를 이용하세요.")
        if st.button("🔐 로그인 시작", type="primary"):
            st.switch_page("pages/01_face_login.py")

    st.divider()
    st.caption("Powered by Anchor AI · 백엔드 FastAPI(REST) · 운영 DB MySQL")


if __name__ == "__main__":
    main()
else:
    main()
