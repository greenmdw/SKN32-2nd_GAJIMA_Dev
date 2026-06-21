# -*- coding: utf-8 -*-
"""application — 얼굴 인증 usecase(19-4 §5·§7.1). 등록/로그인/조회.
임베딩 추출(insightface)은 대시보드(클라이언트)에서 하고, 백엔드는 저장·매칭·로깅을 담당."""
from app.domain.face_match import best_match
from app.infrastructure.mysql import face_repository as repo


def register_face(user_id, display_name=None, role="customer", embedding=None) -> dict:
    if not user_id:
        return {"_status": 400, "error": "user_id 필수"}
    ok = repo.register(user_id, display_name, role or "customer", embedding)
    if not ok:
        return {"_status": 409, "error": f"이미 등록된 사용자 ID: {user_id}"}   # 과제②
    return {"user_id": user_id, "display_name": display_name or user_id,
            "role": role or "customer", "has_face": embedding is not None}


def login_face(embedding=None, user_id=None) -> dict:
    """얼굴 임베딩으로 매칭하거나(우선), user_id로 직접 로그인(폴백)."""
    if embedding:
        user, sim = best_match(embedding, repo.list_users())
        if user:
            repo.log_login(user["user_id"], True, round(sim, 3))                  # 과제①
            return {"user_id": user["user_id"], "display_name": user["display_name"],
                    "role": user.get("role", "customer"), "similarity": round(sim, 3)}
        repo.log_login(user_id or "unknown", False, round(sim, 3), "no_match")
        return {"_status": 401, "error": f"일치하는 얼굴 없음(유사도 {sim:.2f})", "similarity": round(sim, 3)}
    # user_id 직접 로그인(없으면 customer로 생성)
    if not user_id:
        return {"_status": 400, "error": "embedding 또는 user_id 필요"}
    u = repo.get_user(user_id)
    if not u:
        repo.register(user_id, user_id, "customer", None)
        u = repo.get_user(user_id)
    repo.log_login(user_id, True, None)
    return {"user_id": u["user_id"], "display_name": u["display_name"],
            "role": u.get("role", "customer"), "similarity": None}


def get_me(user_id) -> dict:
    u = repo.get_user(user_id)
    if not u:
        return {"_status": 404, "error": f"사용자 없음: {user_id}"}
    return {"user_id": u["user_id"], "display_name": u["display_name"],
            "role": u.get("role", "customer")}


def recent_logins(limit=20) -> dict:
    return {"logins": repo.recent_logins(limit)}
