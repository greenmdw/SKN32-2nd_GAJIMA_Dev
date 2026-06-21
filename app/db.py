# -*- coding: utf-8 -*-
"""Anchor 운영 DB — **MySQL 전용**(우리 운영 DB). SQLite 미사용.
※ Neon(Postgres)은 별도 = simulation_site 로그 전용(여기서 안 씀).
연결: configs/.env 또는 환경변수 MYSQL_HOST/PORT/USER/PASSWORD/DATABASE.
교육과제: ①로그인 로그+최신 N제한 ②등록 중복ID ③관리자권한 ④이탈예측 저장 ⑤고위험 추천.
미연결 시 RuntimeError → 대시보드가 'MySQL 연결 필요' 경고로 처리.
"""
import os
from pathlib import Path
import numpy as np
import mysql.connector

ROOT = Path(__file__).resolve().parents[1]
LOGIN_LOG_LIMIT = 200


def _load_env():
    for p in (ROOT / ".env", ROOT / "configs" / ".env"):
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip())


def _cfg(with_db=True):
    _load_env()
    c = {"host": os.environ.get("MYSQL_HOST", "127.0.0.1"),
         "port": int(os.environ.get("MYSQL_PORT", "3306")),
         "user": os.environ.get("MYSQL_USER", "root"),
         "password": os.environ.get("MYSQL_PASSWORD", "")}
    if with_db:
        c["database"] = os.environ.get("MYSQL_DATABASE", "anchor")
    return c


def _conn(with_db=True):
    try:
        return mysql.connector.connect(**_cfg(with_db))
    except mysql.connector.Error as e:
        raise RuntimeError(f"MySQL 연결 실패 — configs/.env 설정 확인 ({e})")


def available():
    try:
        c = _conn(with_db=False); c.close(); return True
    except Exception:
        return False


def init_db():
    db = os.environ.get("MYSQL_DATABASE", "anchor")
    # 기존 DB(project2db)면 직접 연결, 없을 때만 생성 시도(제한권한 사용자 대응)
    try:
        c = _conn(with_db=True)
    except Exception:
        c0 = _conn(with_db=False); cur0 = c0.cursor()
        cur0.execute(f"CREATE DATABASE IF NOT EXISTS {db} CHARACTER SET utf8mb4")
        c0.commit(); cur0.close(); c0.close()
        c = _conn(with_db=True)
    cur = c.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS face_user(
        user_id VARCHAR(64) PRIMARY KEY, display_name VARCHAR(100), role VARCHAR(16) DEFAULT 'customer',
        embedding LONGBLOB, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP) ENGINE=InnoDB""")
    cur.execute("""CREATE TABLE IF NOT EXISTS login_log(
        id BIGINT AUTO_INCREMENT PRIMARY KEY, user_id VARCHAR(64), success TINYINT, similarity DOUBLE,
        login_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP) ENGINE=InnoDB""")
    cur.execute("""CREATE TABLE IF NOT EXISTS churn_prediction(
        id BIGINT AUTO_INCREMENT PRIMARY KEY, user_id VARCHAR(64), model_name VARCHAR(32), churn_prob DOUBLE,
        risk VARCHAR(16), action VARCHAR(255), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP) ENGINE=InnoDB""")
    cur.execute("""CREATE TABLE IF NOT EXISTS recommendation_log(
        id BIGINT AUTO_INCREMENT PRIMARY KEY, user_id VARCHAR(64), rec_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP) ENGINE=InnoDB""")
    c.commit(); cur.close(); c.close()
    if not get_user("admin"):
        register_user("admin", "관리자", "admin", None, _silent=True)


# ── 과제②: 중복 ID 체크 ──
def register_user(user_id, display_name, role="customer", embedding=None, _silent=False):
    if get_user(user_id):
        if _silent: return False
        raise ValueError(f"이미 등록된 사용자 ID: {user_id}")
    c = _conn(); cur = c.cursor()
    emb = embedding.astype(np.float32).tobytes() if embedding is not None else None
    cur.execute("INSERT INTO face_user(user_id,display_name,role,embedding) VALUES(%s,%s,%s,%s)",
                (user_id, display_name, role, emb))
    c.commit(); cur.close(); c.close(); return True


def get_user(user_id):
    c = _conn(); cur = c.cursor()
    cur.execute("SELECT user_id,display_name,role,embedding FROM face_user WHERE user_id=%s", (user_id,))
    r = cur.fetchone(); cur.close(); c.close()
    if not r: return None
    emb = np.frombuffer(r[3], dtype=np.float32) if r[3] else None
    return {"user_id": r[0], "display_name": r[1], "role": r[2], "embedding": emb}


def list_users():
    c = _conn(); cur = c.cursor()
    cur.execute("SELECT user_id,display_name,role,embedding FROM face_user")
    out = [{"user_id": r[0], "display_name": r[1], "role": r[2],
            "embedding": np.frombuffer(r[3], dtype=np.float32) if r[3] else None} for r in cur.fetchall()]
    cur.close(); c.close(); return out


# ── 과제①: 로그인 로그 + 최신 N개 제한 ──
def log_login(user_id, success, similarity=None):
    c = _conn(); cur = c.cursor()
    cur.execute("INSERT INTO login_log(user_id,success,similarity) VALUES(%s,%s,%s)",
                (user_id, int(success), similarity))
    cur.execute(f"DELETE FROM login_log WHERE id NOT IN "
                f"(SELECT id FROM (SELECT id FROM login_log ORDER BY id DESC LIMIT {LOGIN_LOG_LIMIT}) t)")
    c.commit(); cur.close(); c.close()


def recent_logins(limit=20):
    c = _conn(); cur = c.cursor()
    cur.execute(f"SELECT user_id,success,similarity,login_at FROM login_log ORDER BY id DESC LIMIT {int(limit)}")
    rows = [{"user_id": r[0], "success": r[1], "similarity": r[2], "login_at": str(r[3])} for r in cur.fetchall()]
    cur.close(); c.close(); return rows


# ── 과제④: 이탈예측 저장 ──
def save_prediction(user_id, model_name, churn_prob, risk, action):
    c = _conn(); cur = c.cursor()
    cur.execute("INSERT INTO churn_prediction(user_id,model_name,churn_prob,risk,action) VALUES(%s,%s,%s,%s,%s)",
                (user_id, model_name, float(churn_prob), risk, action))
    c.commit(); cur.close(); c.close()


def recent_predictions(limit=20):
    c = _conn(); cur = c.cursor()
    cur.execute(f"SELECT user_id,model_name,churn_prob,risk,action,created_at FROM churn_prediction ORDER BY id DESC LIMIT {int(limit)}")
    rows = [{"user_id": r[0], "model": r[1], "churn_prob": r[2], "risk": r[3], "action": r[4], "at": str(r[5])} for r in cur.fetchall()]
    cur.close(); c.close(); return rows


# ── 과제⑤: 고위험 추천 저장 ──
def save_recommendation(user_id, rec):
    import json
    c = _conn(); cur = c.cursor()
    cur.execute("INSERT INTO recommendation_log(user_id,rec_json) VALUES(%s,%s)",
                (user_id, json.dumps(rec, ensure_ascii=False)))
    c.commit(); cur.close(); c.close()
