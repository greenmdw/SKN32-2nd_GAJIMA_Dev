# -*- coding: utf-8 -*-
"""components/layout — 공통 레이아웃(CSS 로드, 헤더, 사이드바)."""
from pathlib import Path
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]            # dashboard_streamlit/
STYLES = ROOT / "styles" / "main.css"
ASSETS = ROOT / "assets"


def load_css():
    if STYLES.exists():
        st.markdown(f"<style>{STYLES.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
    # 대시보드 본문은 전체폭(랜딩 중앙정렬 CSS 무력화)
    st.markdown("""<style>.block-container{max-width:96% !important;min-height:auto !important;
        display:block !important;padding:24px 28px !important;}</style>""", unsafe_allow_html=True)


def logo_svg():
    p = ASSETS / "logo.svg"
    return p.read_text(encoding="utf-8") if p.exists() else ""


def require_login():
    """로그인 안 됐으면 안내 후 정지."""
    if not st.session_state.get("is_logged_in"):
        st.warning("로그인이 필요합니다. 좌측 '01 face login' 페이지에서 로그인하세요.")
        st.stop()


def sidebar_user():
    with st.sidebar:
        if st.session_state.get("is_logged_in"):
            st.write(f"**{st.session_state.get('display_name','-')}** ({st.session_state.get('role','customer')})")
            if st.button("로그아웃"):
                from services import auth_service
                auth_service.logout()
                st.rerun()
        else:
            st.caption("로그인 전")
