# -*- coding: utf-8 -*-
"""services/auth_service — 로그인/등록/세션(19-4 §7.1). 백엔드 /auth/* 만 호출.
얼굴 임베딩 추출(insightface)은 클라이언트(여기)에서 하고, 저장·매칭·로깅은 백엔드가 한다.
role 없으면 customer 기본값."""
import streamlit as st
from services import api_client as api
from services import face_auth


def _set_session(user):
    st.session_state.update(
        is_logged_in=True,
        user_id=user.get("user_id"),
        display_name=user.get("display_name") or user.get("user_id"),
        role=user.get("role") or "customer",        # 기본 customer
    )


def extract_embedding(img_bytes):
    """카메라/업로드 bytes → 512d normed 임베딩(list) 또는 None."""
    emb = face_auth.embed_from_bytes(img_bytes)
    return [float(x) for x in emb] if emb is not None else None


def register(user_id, display_name=None, role="customer", img_bytes=None):
    emb = extract_embedding(img_bytes) if img_bytes else None
    res = api.post("/auth/face/register",
                   {"user_id": user_id, "display_name": display_name, "role": role, "embedding": emb})
    return res


def login_with_id(user_id, role="customer"):
    res = api.post("/auth/face/login", {"user_id": user_id})
    if res.get("ok"):
        u = res["data"]
        u.setdefault("role", role)
        _set_session(u)
    return res


def login_with_face(img_bytes):
    emb = extract_embedding(img_bytes)
    if emb is None:
        return {"ok": False, "error": {"code": "NO_FACE", "message": "얼굴을 인식하지 못했습니다."}}
    res = api.post("/auth/face/login", {"embedding": emb})
    if res.get("ok"):
        _set_session(res["data"])
    return res


def has_face_model():
    return face_auth.HAS_FACE


def logout():
    for k in ("is_logged_in", "user_id", "display_name", "role"):
        st.session_state.pop(k, None)
    st.session_state.is_logged_in = False
