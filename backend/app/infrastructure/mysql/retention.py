# -*- coding: utf-8 -*-
"""infrastructure/mysql — 로그성 테이블 보존정책(현업 방식: 시간 기반 TTL + 주기 정리).
insert 경로에서 정리하지 않고(요청 지연 0), 스케줄러가 주기적으로 만료분을 삭제한다.
보존기간은 테이블 성격에 맞게 차등(감사성=길게, 휘발성=짧게)."""
import os
from app.infrastructure.mysql.session import mode, _q

# table: (timestamp_col, default_days)  — 05-6-5 보존기간 명세서와 일치
RETENTION = {
    "prediction_log":        ("created_at", int(os.environ.get("RET_PREDICTION_DAYS", "90"))),
    "sim_event_log":         ("event_time", int(os.environ.get("RET_SIM_DAYS", "7"))),     # 시뮬=휘발성
    "retention_action_log":  ("created_at", int(os.environ.get("RET_ACTION_DAYS", "365"))), # 감사=장기
    "recommendation":        ("created_at", int(os.environ.get("RET_REC_DAYS", "90"))),
    "face_login_log":        ("login_at",   int(os.environ.get("RET_LOGIN_DAYS", "90"))),
    "feature_user_snapshot": ("created_at", int(os.environ.get("RET_SNAPSHOT_DAYS", "90"))), # 예측시점 스냅샷
}


def cleanup_db() -> dict:
    """만료(보존기간 초과) 행 삭제. 테이블/컬럼은 내부 상수만 사용(SQL injection 무관)."""
    if mode() != "mysql":
        return {}
    out = {}
    for table, (col, days) in RETENTION.items():
        try:
            _q(f"DELETE FROM {table} WHERE {col} < (NOW() - INTERVAL %s DAY)", (days,))
            out[table] = days
        except Exception:
            pass          # 테이블 없거나 일시 오류는 무시(다음 주기 재시도)
    return out
