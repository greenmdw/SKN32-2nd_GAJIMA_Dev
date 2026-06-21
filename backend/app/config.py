# -*- coding: utf-8 -*-
"""config 계층(19-2). .env 로딩·검증. MySQL은 옵션(미설정 시 memory 데모 모드)."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]          # 가지마 backend/ 루트
GAJIMA_ROOT = ROOT.parent                            # SKN32-2nd_GAJIMA_Dev/


def _load_env() -> None:
    """backend/.env → 환경변수(이미 있으면 보존). dotenv 미설치여도 동작."""
    for p in (ROOT / ".env", GAJIMA_ROOT / ".env", GAJIMA_ROOT / "configs" / ".env"):
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())


_load_env()

PORT = int(os.environ.get("PORT", "8090"))
API_KEY = os.environ.get("API_KEY", "dev-key")

# 대용량(parquet/npz/model)은 파일, DB엔 경로 (19-2 §1)
DATA_DIR = GAJIMA_ROOT / "data" / "processed"
EVAL_DIR = DATA_DIR / "evaluation"
REC_DIR = DATA_DIR / "recommendation"

# MYSQL_HOST 가 있으면 MySQL 운영 모드, 없으면 memory 폴백
MYSQL = ({
    "host": os.environ.get("MYSQL_HOST"),
    "port": int(os.environ.get("MYSQL_PORT", "3306")),
    "user": os.environ.get("MYSQL_USER", "root"),
    "password": os.environ.get("MYSQL_PASSWORD", ""),
    "database": os.environ.get("MYSQL_DATABASE", "gajima"),
} if os.environ.get("MYSQL_HOST") else None)

NEON_URL = os.environ.get("NEON_URL") or None        # 시뮬 로그 전용(외부)

# 위험등급 임계값 (domain)
RISK_HIGH = 0.65
RISK_LOW = 0.35
