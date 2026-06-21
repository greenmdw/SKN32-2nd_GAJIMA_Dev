# -*- coding: utf-8 -*-
"""components/error_state — API 실패/빈 데이터 상태 UI(19-4 §6). 계산으로 메우지 않는다."""
import streamlit as st


def show(res, empty_msg="데이터가 없습니다."):
    """api_client wrapper(res) 검사. ok면 data 반환, 아니면 빈 상태 UI 표시 후 None."""
    if not isinstance(res, dict):
        st.error("응답 형식 오류"); return None
    if res.get("ok"):
        data = res.get("data")
        if data in (None, [], {}):
            st.info(empty_msg); return None
        return data
    err = res.get("error") or {}
    code = err.get("code", "ERROR")
    if code == "BACKEND_UNAVAILABLE":
        st.warning("백엔드에 연결할 수 없습니다. (DASHBOARD_USE_MOCK=true 로 개발 모드 가능)")
    else:
        st.error(f"[{code}] {err.get('message','오류')}")
    return None
