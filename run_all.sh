#!/usr/bin/env bash
# 가지마 동시 기동 — FastAPI 백엔드(:8090) + Streamlit 대시보드(:8501)
# 실행:  bash run_all.sh     (가지마 루트에서)
# 종료:  Ctrl+C  → 백엔드도 자동 정리
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="$ROOT/.venv/Scripts/python.exe"
[ -x "$PY" ] || PY="$ROOT/.venv/bin/python"
[ -x "$PY" ] || PY="python"

echo "[run] 백엔드 기동 → http://127.0.0.1:8090 (docs: /docs)"
"$PY" -m uvicorn app.main:app --host 127.0.0.1 --port 8090 --app-dir "$ROOT/backend" &
BACKEND_PID=$!
trap 'echo "[run] 종료 — 백엔드 정리"; kill $BACKEND_PID 2>/dev/null' EXIT INT TERM

# 백엔드 health 대기(최대 ~15초)
for i in $(seq 1 30); do
  "$PY" -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8090/health',timeout=2)" 2>/dev/null && { echo "[run] 백엔드 OK"; break; }
  sleep 0.5
done

echo "[run] 대시보드 기동 → http://localhost:8501"
"$PY" -m streamlit run "$ROOT/dashboard_streamlit/app.py"
