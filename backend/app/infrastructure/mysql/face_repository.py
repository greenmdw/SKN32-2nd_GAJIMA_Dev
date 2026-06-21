# -*- coding: utf-8 -*-
"""infrastructure/mysql — 얼굴 사용자/로그인 로그 repository(19-4 §7.1).
대시보드는 DB 직접 접속 금지 → 얼굴 등록/로그인은 백엔드가 face_user/face_login_log를 읽고 쓴다.
임베딩은 float32 bytes로 저장(insightface 512d). memory 폴백 지원."""
import struct
from app.infrastructure.mysql.session import mode, _q, _mem

LOGIN_LOG_LIMIT = 200
_mem.setdefault("face_users", [])      # [{user_id,display_name,role,embedding(list|None)}]
_mem.setdefault("face_logins", [])     # [{user_id,success,similarity,...}]


def _to_bytes(emb):
    if emb is None:
        return None
    return struct.pack(f"{len(emb)}f", *[float(x) for x in emb])


def _to_list(b):
    if not b:
        return None
    n = len(b) // 4
    return list(struct.unpack(f"{n}f", b))


def get_user(user_id):
    if mode() == "mysql":
        rows = _q("SELECT user_id,display_name,role,embedding FROM face_user WHERE user_id=%s",
                  (user_id,), fetch=True)
        if not rows:
            return None
        r = rows[0]
        return {"user_id": r["user_id"], "display_name": r["display_name"],
                "role": r["role"], "embedding": _to_list(r["embedding"])}
    return next((dict(u) for u in _mem["face_users"] if u["user_id"] == user_id), None)


def list_users():
    if mode() == "mysql":
        rows = _q("SELECT user_id,display_name,role,embedding FROM face_user", fetch=True) or []
        return [{"user_id": r["user_id"], "display_name": r["display_name"], "role": r["role"],
                 "embedding": _to_list(r["embedding"])} for r in rows]
    return [dict(u) for u in _mem["face_users"]]


def register(user_id, display_name, role="customer", embedding=None):
    """과제②: 중복 ID면 False. 신규면 생성."""
    if get_user(user_id):
        return False
    if mode() == "mysql":
        _q("INSERT INTO face_user(user_id,display_name,role,embedding) VALUES(%s,%s,%s,%s)",
           (user_id, display_name or user_id, role, _to_bytes(embedding)))
    else:
        _mem["face_users"].append({"user_id": user_id, "display_name": display_name or user_id,
                                   "role": role, "embedding": list(embedding) if embedding else None})
    return True


def log_login(user_id, success, similarity=None, failure_reason=None):
    """과제①: 로그인 로그 + 최신 N(200) 유지. face_login_log(19-4)."""
    if mode() == "mysql":
        _q("""INSERT INTO face_login_log(user_id,success,similarity,failure_reason)
              VALUES(%s,%s,%s,%s)""", (user_id, 1 if success else 0, similarity, failure_reason))
        _q("""DELETE FROM face_login_log WHERE login_id NOT IN
              (SELECT login_id FROM (SELECT login_id FROM face_login_log
               ORDER BY login_id DESC LIMIT %s) t)""", (LOGIN_LOG_LIMIT,))
    else:
        _mem["face_logins"].append({"user_id": user_id, "success": bool(success),
                                    "similarity": similarity, "failure_reason": failure_reason})
        _mem["face_logins"][:] = _mem["face_logins"][-LOGIN_LOG_LIMIT:]


def recent_logins(limit=20):
    if mode() == "mysql":
        return _q("""SELECT user_id,success,similarity,failure_reason,login_at
                     FROM face_login_log ORDER BY login_id DESC LIMIT %s""",
                  (int(limit),), fetch=True) or []
    return list(reversed(_mem["face_logins"]))[:int(limit)]
