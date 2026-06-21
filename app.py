from pathlib import Path

import streamlit as st

from app.dashboard import render_dashboard
from app import db as adb
from app import face_auth


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

    if "role" not in st.session_state:
        st.session_state.role = "customer"


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
    try:
        adb.init_db()
    except Exception:
        pass
    db_on = adb.available()
    if not db_on:
        st.warning("MySQL 미연결 — 로그인은 되나 로그 저장(과제①)은 configs/.env 설정 후. (Neon은 시뮬 전용)")
    if st.button("← 뒤로 (랜딩)", key="login_back_top"):
        go_to("landing"); st.rerun()
    st.title("로그인")

    # 1) 아이디 로그인 (기본·우선)
    uid = st.text_input("아이디 (user_id)", value="demo01", key="login_uid")
    role = st.radio("역할", ["customer", "admin"], horizontal=True, key="login_role",
                    help="관리자만 모델 진단(15시각화)·로그 열람 — 교육과제 ③")
    if st.button("로그인", type="primary", key="login_btn"):
        if not uid:
            st.error("아이디를 입력하세요.")
        else:
            try:
                if db_on and not adb.get_user(uid):
                    adb.register_user(uid, uid, role, None, _silent=True)
                if db_on:
                    adb.log_login(uid, success=True, similarity=None)                      # 과제①
            except Exception as e:
                st.warning(f"DB 기록 생략(MySQL 미연결): {e}")
            st.session_state.update(is_logged_in=True, role=role, login_user=uid)
            go_to("dashboard"); st.rerun()

    # 2) 얼굴 로그인 (보조, 펼침)
    with st.expander("얼굴 로그인 (insightface)"):
        if face_auth.HAS_FACE:
            img = st.camera_input("얼굴 촬영") or st.file_uploader("사진 업로드", type=["jpg", "png", "jpeg"])
            if img is not None and st.button("얼굴로 로그인", key="face_login_btn"):
                emb = face_auth.embed_from_bytes(img.getvalue())
                f_uid, f_role, sim = face_auth.match(emb, adb.list_users() if db_on else [])
                try:
                    if db_on: adb.log_login(f_uid or "unknown", success=bool(f_uid), similarity=round(sim, 3))
                except Exception: pass
                if f_uid:
                    st.session_state.update(is_logged_in=True, role=f_role, login_user=f_uid)
                    go_to("dashboard"); st.rerun()
                else:
                    st.error(f"일치하는 얼굴 없음(유사도 {sim:.2f}). 회원가입에서 얼굴 등록 후 이용.")
        else:
            st.info("insightface 미설치 — 아이디 로그인을 사용하세요.")

    st.divider()
    if st.button("회원가입으로", key="login_to_register"):
        go_to("register"); st.rerun()


def render_dashboard_page() -> None:
    if not st.session_state.is_logged_in:
        go_to("login")
        st.rerun()

    with st.sidebar:
        st.write(f"**역할**: {st.session_state.role}")
        if st.button("로그아웃"):
            st.session_state.is_logged_in = False
            go_to("landing")
            st.rerun()

    render_dashboard(role=st.session_state.role, login_user=st.session_state.get("login_user", "demo"))


def render_register_page() -> None:
    try:
        adb.init_db()
    except Exception:
        st.warning("MySQL 미연결 — 등록은 configs/.env 설정 후 가능. (Neon은 시뮬 전용)")
    if st.button("← 뒤로 (랜딩)", key="reg_back_top"):
        go_to("landing"); st.rerun()
    st.title("회원가입")
    uid = st.text_input("아이디 (user_id)", key="reg_uid")
    name = st.text_input("이름")
    role = st.radio("역할", ["customer", "admin"], horizontal=True)
    emb = None
    if face_auth.HAS_FACE:
        img = st.camera_input("얼굴 등록(선택)") or st.file_uploader("얼굴 사진(선택)", type=["jpg", "png", "jpeg"])
        if img is not None:
            emb = face_auth.embed_from_bytes(img.getvalue())
            st.caption("얼굴 임베딩 추출 " + ("성공" if emb is not None else "실패(얼굴 미검출)"))
    if st.button("등록"):
        if not uid:
            st.error("user_id를 입력하세요")
        else:
            try:
                adb.register_user(uid, name or uid, role, emb)          # 과제②: 중복 시 예외
                st.success(f"등록 완료: {uid}")
            except ValueError as e:
                st.error(str(e))                                        # 과제②: 중복 ID 차단
            except Exception as e:
                st.warning(f"MySQL 미연결로 등록 보류: {e}")
    if st.button("랜딩으로"):
        go_to("landing"); st.rerun()


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
        render_register_page()
    elif page == "password_reset":
        render_placeholder_page("Password Reset", "비밀번호 찾기 기능이 연결될 페이지입니다.")
    else:
        go_to("landing")
        st.rerun()


def main() -> None:
    st.set_page_config(page_title="Anchor — 이탈 분석", page_icon="A", layout="wide")
    load_css(STYLES_DIR / "main.css")
    init_session_state()
    render_current_page()
    print('test test test')


if __name__ == "__main__":
    main()
