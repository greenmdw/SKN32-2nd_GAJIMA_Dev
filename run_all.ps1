# 가지마 동시 기동 — FastAPI 백엔드(:8090) + Streamlit 대시보드(:8501)
# 실행:  .\run_all.ps1      (가지마 루트에서)
# 종료:  Ctrl+C  → 대시보드 종료 시 백엔드도 자동 정리
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$py   = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }   # .venv 없으면 시스템 python

Write-Host "[run] 백엔드 기동 → http://127.0.0.1:8090  (docs: /docs)" -ForegroundColor Cyan
$backend = Start-Process -FilePath $py `
  -ArgumentList "-m","uvicorn","app.main:app","--host","127.0.0.1","--port","8090" `
  -WorkingDirectory (Join-Path $root "backend") -PassThru

# 백엔드 health 대기(최대 ~15초)
$ok = $false
for ($i = 0; $i -lt 30; $i++) {
  try { Invoke-WebRequest "http://127.0.0.1:8090/health" -TimeoutSec 2 -UseBasicParsing | Out-Null; $ok = $true; break }
  catch { Start-Sleep -Milliseconds 500 }
}
if ($ok) { Write-Host "[run] 백엔드 OK" -ForegroundColor Green }
else     { Write-Host "[run] 백엔드 응답 지연 — 그래도 대시보드 진행" -ForegroundColor Yellow }

Write-Host "[run] 대시보드 기동 → http://localhost:8501" -ForegroundColor Cyan
try {
  & $py -m streamlit run (Join-Path $root "dashboard_streamlit\app.py")
}
finally {
  Write-Host "[run] 종료 — 백엔드 정리" -ForegroundColor Yellow
  if ($backend -and -not $backend.HasExited) { Stop-Process -Id $backend.Id -Force }
}
