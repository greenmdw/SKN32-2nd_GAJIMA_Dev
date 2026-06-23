# -*- coding: utf-8 -*-
"""infrastructure/mysql — 운영 DB 풀 + repository. MySQL 미설정/미연결 시 memory 폴백(데모).
Node `infrastructure/mysql/pool.js` 포팅(mysql.connector 사용)."""
import json
from app.config import MYSQL

_pool = None
_mode = "memory"
_mem = {"models": [], "evals": [], "predictions": []}


def _get_pool():
    global _pool, _mode
    if _pool is not None or not MYSQL:
        return _pool
    try:
        import mysql.connector.pooling as pooling
        _pool = pooling.MySQLConnectionPool(pool_name="gajima", pool_size=5,
                                            charset="utf8mb4", **MYSQL)
        _mode = "mysql"
    except Exception:
        _pool = None
    return _pool


def mode() -> str:
    return "mysql" if (MYSQL and _get_pool()) else "memory"


def _q(sql, params=(), fetch=False):
    p = _get_pool()
    if not p:
        return None
    conn = p.get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params)
        if fetch:
            rows = cur.fetchall()
            cur.close()
            return rows
        conn.commit()
        last = cur.lastrowid
        cur.close()
        return last
    finally:
        conn.close()


# ---------------- model_registry ----------------
class ModelRepository:
    def upsert(self, m: dict) -> dict:
        if mode() == "mysql":
            _q("""INSERT INTO model_registry
                  (model_name,model_type,feature_schema_version,label_name,horizon_days,
                   preprocessing_config,dataset_path,artifact_path,metrics_json,is_active)
                  VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                  ON DUPLICATE KEY UPDATE model_type=VALUES(model_type),
                   preprocessing_config=VALUES(preprocessing_config),dataset_path=VALUES(dataset_path),
                   artifact_path=VALUES(artifact_path),metrics_json=VALUES(metrics_json),
                   is_active=VALUES(is_active)""",
                (m["model_name"], m["model_type"], m.get("feature_schema_version", "v2"),
                 m.get("label_name", "churn"), m.get("horizon_days", 7),
                 json.dumps(m.get("preprocessing_config") or {}), m.get("dataset_path"),
                 m["artifact_path"], json.dumps(m.get("metrics") or {}),
                 1 if m.get("is_active") else 0))
            rows = _q("SELECT model_id FROM model_registry WHERE model_name=%s",
                      (m["model_name"],), fetch=True)
            mid = rows[0]["model_id"] if rows else None
            if m.get("is_active"):
                _q("UPDATE model_registry SET is_active=0 WHERE model_type=%s AND model_name<>%s",
                   (m["model_type"], m["model_name"]))
            return {"model_id": mid, "mode": "mysql"}
        # memory
        existing = next((x for x in _mem["models"] if x["model_name"] == m["model_name"]), None)
        if existing:
            existing.update(m)
            mid = existing["model_id"]
        else:
            mid = len(_mem["models"]) + 1
            _mem["models"].append({"model_id": mid, **m,
                                   "is_active": 1 if m.get("is_active") else 0})
        if m.get("is_active"):
            for x in _mem["models"]:
                if x["model_type"] == m["model_type"] and x["model_name"] != m["model_name"]:
                    x["is_active"] = 0
        return {"model_id": mid, "mode": "memory"}

    def list(self):
        if mode() == "mysql":
            return _q("SELECT * FROM model_registry ORDER BY model_id DESC", fetch=True) or []
        return list(reversed(_mem["models"]))

    def active(self):
        if mode() == "mysql":
            return _q("SELECT * FROM model_registry WHERE is_active=1", fetch=True) or []
        return [x for x in _mem["models"] if x.get("is_active")]

    def exists(self, model_id) -> bool:
        if model_id is None:
            return False
        if mode() == "mysql":
            rows = _q("SELECT 1 FROM model_registry WHERE model_id=%s", (model_id,), fetch=True)
            return bool(rows)
        return any(x["model_id"] == model_id for x in _mem["models"])


# ---------------- model_evaluation ----------------
class EvaluationRepository:
    def insert(self, model_id, e: dict) -> dict:
        if mode() == "mysql":
            # 갱신 정책: 재제출 시 모델별 평가는 최신 1건만 유지(무한 누적 방지)
            _q("DELETE FROM model_evaluation WHERE model_id=%s", (model_id,))
            eid = _q("""INSERT INTO model_evaluation
                        (model_id,dataset_tag,split_name,roc_auc,pr_auc,best_threshold,best_f1,
                         eval_predictions_path,shap_summary_path)
                        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                     (model_id, e.get("dataset_tag", "churn"), e.get("split_name", "test"),
                      e.get("roc_auc"), e.get("pr_auc"), e.get("best_threshold"), e.get("best_f1"),
                      e.get("eval_predictions_path"), e.get("shap_summary_path")))
            return {"eval_id": eid}
        _mem["evals"] = [x for x in _mem["evals"] if x["model_id"] != model_id]  # 모델별 최신만
        eid = len(_mem["evals"]) + 1
        _mem["evals"].append({"eval_id": eid, "model_id": model_id, **e})
        return {"eval_id": eid}

    def for_model(self, model_id):
        if mode() == "mysql":
            return _q("SELECT * FROM model_evaluation WHERE model_id=%s ORDER BY eval_id DESC",
                      (model_id,), fetch=True) or []
        return [e for e in _mem["evals"] if e["model_id"] == model_id]


# ---------------- prediction_log ----------------
class PredictionRepository:
    def log(self, p: dict):
        if mode() == "mysql":
            _q("""INSERT INTO prediction_log
                  (model_id,user_id,churn_probability,risk_level,horizon_days,recommended_action)
                  VALUES(%s,%s,%s,%s,%s,%s)""",
               (p.get("model_id"), p["user_id"], p["churn_probability"], p["risk_level"],
                p.get("horizon_days", 7), p.get("recommended_action")))
        else:
            _mem["predictions"].append(p)
            _mem["predictions"][:] = _mem["predictions"][-10000:]   # memory 폴백 RAM 상한

    def latest(self, user_id):
        if mode() == "mysql":
            rows = _q("SELECT * FROM prediction_log WHERE user_id=%s ORDER BY prediction_id DESC LIMIT 1",
                      (user_id,), fetch=True)
            return rows[0] if rows else None
        return next((x for x in reversed(_mem["predictions"]) if x["user_id"] == user_id), None)

    def top_risk(self, limit=20, min_prob=0.0):
        """고위험 유저 목록(향후 7일 이내 이탈 확률 내림차순). 유저별 최신 1건 기준."""
        if mode() == "mysql":
            return _q("""SELECT p.* FROM prediction_log p
                         JOIN (SELECT user_id, MAX(prediction_id) mid
                               FROM prediction_log GROUP BY user_id) last
                           ON p.prediction_id = last.mid
                         WHERE p.churn_probability >= %s
                         ORDER BY p.churn_probability DESC LIMIT %s""",
                      (min_prob, int(limit)), fetch=True) or []
        latest = {}
        for x in _mem["predictions"]:
            latest[x["user_id"]] = x          # 마지막이 최신
        rows = [x for x in latest.values() if x["churn_probability"] >= min_prob]
        rows.sort(key=lambda x: x["churn_probability"], reverse=True)
        return rows[:int(limit)]

    def summary_stats(self) -> dict:
        """운영 요약 집계(19-7-1 /dashboard/summary): 전체수·고위험수·평균확률·최신시각."""
        if mode() == "mysql":
            try:
                r = _q("""SELECT COUNT(*) total,
                                 SUM(CASE WHEN risk_level='high' THEN 1 ELSE 0 END) high_risk,
                                 AVG(churn_probability) avg_p, MAX(created_at) latest_at
                          FROM prediction_log""", fetch=True)
                row = r[0] if r else {}
                return {"total": int(row.get("total") or 0),
                        "high_risk": int(row.get("high_risk") or 0),
                        "avg": round(float(row.get("avg_p") or 0), 4),
                        "latest_at": (str(row["latest_at"]) if row.get("latest_at") else None)}
            except Exception:
                return {"total": 0, "high_risk": 0, "avg": 0.0, "latest_at": None}
        preds = _mem["predictions"]
        total = len(preds)
        high = sum(1 for x in preds if x.get("risk_level") == "high")
        avg = round(sum(float(x.get("churn_probability", 0)) for x in preds) / total, 4) if total else 0.0
        return {"total": total, "high_risk": high, "avg": avg, "latest_at": None}


# ---------------- sim_event_log (26-9 P2 실시간 루프) ----------------
class SimEventRepository:
    def log(self, e: dict):
        if mode() == "mysql":
            _q("""INSERT INTO sim_event_log
                  (user_id,session_id,event_type,product_id,category_id,brand,price,churn_prob,risk_level)
                  VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
               (e["user_id"], e["session_id"], e["event_type"], e.get("product_id"),
                e.get("category_id"), e.get("brand"), e.get("price"),
                e.get("churn_prob"), e.get("risk_level")))
        else:
            _mem.setdefault("sim_events", []).append(e)
            _mem["sim_events"][:] = _mem["sim_events"][-5000:]   # memory 폴백 RAM 상한


model_repository = ModelRepository()
evaluation_repository = EvaluationRepository()
prediction_repository = PredictionRepository()
sim_event_repository = SimEventRepository()
