from pathlib import Path

import streamlit as st


BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
STYLES_DIR = BASE_DIR / "styles"


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_css(path: Path) -> None:
    css = load_text(path)
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def go_to(page_name: str) -> None:
    st.session_state.page = page_name


def init_session_state() -> None:
    if "page" not in st.session_state:
        st.session_state.page = "landing"

    if "is_logged_in" not in st.session_state:
        st.session_state.is_logged_in = False


def render_landing_page() -> None:
    logo_svg = load_text(ASSETS_DIR / "logo.svg")

    st.markdown(f'<div class="logo">{logo_svg}</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="brand-title">Anchor</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="brand-sub">실시간 고객 이탈률 분석 시스템</p>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="button-wrap">', unsafe_allow_html=True)
    if st.button("얼굴 로그인", use_container_width=True, key="btn_face"):
        go_to("login");
        st.rerun()
    if st.button("회원가입", use_container_width=True, key="btn_register"):
        go_to("register");
        st.rerun()
    if st.button("비밀번호 찾기", use_container_width=True, key="btn_reset"):
        go_to("password_reset");
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="foot">Powered by Anchor AI</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_login_page() -> None:
    st.title("Login")
    st.caption("얼굴 로그인 기능이 연결될 페이지입니다.")

    if st.button("로그인 완료 테스트"):
        st.session_state.is_logged_in = True
        go_to("dashboard")
        st.rerun()

    if st.button("랜딩 페이지로 돌아가기"):
        go_to("landing")
        st.rerun()


def render_dashboard_page() -> None:
    if not st.session_state.is_logged_in:
        go_to("login")
        st.rerun()

    st.title("Dashboard")
    st.caption("Machine learning 분석 지표가 표시될 페이지입니다.")

    metric_1, metric_2, metric_3 = st.columns(3)
    metric_1.metric("Model Score", "0.92")
    metric_2.metric("Risk Index", "Low")
    metric_3.metric("Updated", "Today")

    if st.button("로그아웃"):
        st.session_state.is_logged_in = False
        go_to("landing")
        st.rerun()


def render_placeholder_page(title: str, description: str) -> None:
    st.title(title)
    st.caption(description)

    if st.button("랜딩 페이지로 돌아가기"):
        go_to("landing")
        st.rerun()


def render_current_page() -> None:
    page = st.session_state.page

    if page == "landing":
        render_landing_page()
    elif page == "login":
        render_login_page()
    elif page == "dashboard":
        render_dashboard_page()
    elif page == "register":
        render_placeholder_page("Register", "회원가입 기능이 연결될 페이지입니다.")
    elif page == "password_reset":
        render_placeholder_page("Password Reset", "비밀번호 찾기 기능이 연결될 페이지입니다.")
    else:
        go_to("landing")
        st.rerun()


def main() -> None:
    st.set_page_config(page_title="GAJIMA", page_icon="G", layout="centered")
    load_css(STYLES_DIR / "main.css")
    init_session_state()
    render_current_page()
    Print('test test test')


if __name__ == "__main__":
    main()
