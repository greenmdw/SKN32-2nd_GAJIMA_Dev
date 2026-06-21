# -*- coding: utf-8 -*-
"""services/api_client — FastAPI 백엔드 REST 호출(19-5 §5). 백엔드가 {ok,data,meta,error} 봉투를 주므로
성공 응답은 그대로 통과(raw passthrough). mock/연결오류만 봉투를 합성한다.
대시보드는 MySQL/Neon/파일에 직접 접속하지 않고 백엔드만 호출한다."""
import json
import os
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]            # dashboard_streamlit/
MOCK_DIR = ROOT / "mocks"


def _env(k, default=None):
    for p in (ROOT / ".env", ROOT / ".env.example"):
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    kk, vv = line.split("=", 1)
                    os.environ.setdefault(kk.strip(), vv.strip())
            break
    return os.environ.get(k, default)


BASE_URL = _env("DASHBOARD_API_BASE_URL", "http://127.0.0.1:8090")
API_KEY = _env("DASHBOARD_API_KEY", "anchor-dev-key")
USE_MOCK = str(_env("DASHBOARD_USE_MOCK", "false")).lower() == "true"
TIMEOUT = float(_env("DASHBOARD_TIMEOUT_SEC", "10"))


def _ok(data, source="mock"):
    return {"ok": True, "data": data, "meta": {"schema_version": "dashboard.v1", "source": source}, "error": None}


def _err(code, msg):
    return {"ok": False, "data": None, "meta": {"schema_version": "dashboard.v1"},
            "error": {"code": code, "message": msg}}


def _read_mock(mock_path):
    p = MOCK_DIR / (mock_path + ".json")
    if p.exists():
        return _ok(json.loads(p.read_text(encoding="utf-8")), "mock")     # mock 파일=raw data → 봉투 합성
    return _err("MOCK_NOT_FOUND", f"mock 없음: {mock_path}")


def call(method, endpoint, body=None, mock_path=None):
    if USE_MOCK and mock_path:
        return _read_mock(mock_path)
    url = f"{BASE_URL}{endpoint}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json", "x-api-key": API_KEY})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return json.loads(r.read().decode("utf-8"))          # 백엔드 봉투를 그대로 통과
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode("utf-8"))          # 에러도 봉투로 옴
        except Exception:
            return _err(f"HTTP_{e.code}", str(e))
    except Exception as e:
        if mock_path:
            return _read_mock(mock_path)
        return _err("BACKEND_UNAVAILABLE", f"backend API is not reachable: {e}")


def get(endpoint, mock_path=None):
    return call("GET", endpoint, None, mock_path)


def post(endpoint, body, mock_path=None):
    return call("POST", endpoint, body, mock_path)


def health():
    return call("GET", "/health", None, mock_path=None)
