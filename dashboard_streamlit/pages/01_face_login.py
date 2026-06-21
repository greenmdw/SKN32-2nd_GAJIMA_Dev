# -*- coding: utf-8 -*-
"""pages/01_face_login — 얼굴/아이디 로그인 + 회원가입(19-4 §7.1).
백엔드 /auth/face/* 만 호출. 성공 시 session_state(user_id, role=customer 기본) 저장 후 대시보드로."""
import streamlit as st
from components import layout
from services import auth_service, api_client

layout.load_css()
layout.sidebar_user()
st.title("로그인 / 회원가입")

# 백엔드 상태 표시
hb = api_client.health()
if hb.get("ok"):
    st.caption(f"백엔드 연결됨 · db_mode={hb['data'].get('db_mode')}")
elif api_client.USE_MOCK:
    st.caption("개발(mock) 모드 — 백엔드 없이 화면 확인")
else:
    st.warning("백엔드 미연결 — .env의 DASHBOARD_API_BASE_URL 확인 또는 DASHBOARD_USE_MOCK=true")

tab_login, tab_register = st.tabs(["로그인", "회원가입"])

with tab_login:
    st.subheader("아이디 로그인")
    with st.form("login_form"):
        uid = st.text_input("아이디 (user_id)", value="demo01")
        role = st.radio("역할", ["customer", "admin"], horizontal=True,
                        help="관리자만 모델 진단(15시각화)·로그 열람 (교육과제 ③)")
        ok = st.form_submit_button("로그인", type="primary")
    if ok:
        if not uid.strip():
            st.error("아이디(user_id)를 입력하세요.")
        else:
            res = auth_service.login_with_id(uid.strip(), role)
            if res.get("ok"):
                st.success(f"로그인 성공: {uid.strip()}")
                st.switch_page("pages/02_dashboard.py")
            else:
                st.error((res.get("error") or {}).get("message", "로그인 실패"))

    st.divider()
    with st.expander("얼굴 로그인 (insightface)"):
        if auth_service.has_face_model():
            img = st.camera_input("얼굴 촬영") or st.file_uploader("사진 업로드", type=["jpg", "jpeg", "png"])
            if img is not None and st.button("얼굴로 로그인"):
                res = auth_service.login_with_face(img.getvalue())
                if res.get("ok"):
                    st.success(f"얼굴 로그인 성공 (유사도 {res['data'].get('similarity')})")
                    st.switch_page("pages/02_dashboard.py")
                else:
                    st.error((res.get("error") or {}).get("message", "얼굴 일치 없음"))
        else:
            st.info("insightface 미설치 — 아이디 로그인을 사용하세요.")

with tab_register:
    st.subheader("회원가입")
    with st.form("register_form"):
        ruid = st.text_input("아이디 (user_id) — 필수")
        rname = st.text_input("이름")
        rrole = st.radio("역할", ["customer", "admin"], horizontal=True, key="reg_role")
        rimg = st.camera_input("얼굴 등록(선택)") if auth_service.has_face_model() else None
        rok = st.form_submit_button("등록")
    if rok:
        if not ruid.strip():
            st.error("아이디(user_id)는 필수입니다. ('이름'이 아니라 '아이디' 칸)")
        else:
            res = auth_service.register(ruid.strip(), rname or ruid.strip(), rrole,
                                        rimg.getvalue() if rimg is not None else None)
            if res.get("ok"):
                st.success(f"등록 완료: {ruid.strip()} ({rrole})")
            else:
                st.error((res.get("error") or {}).get("message", "등록 실패(중복 ID 등)"))   # 과제②
