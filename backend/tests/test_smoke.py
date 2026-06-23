# -*- coding: utf-8 -*-
"""스모크 테스트(19-4 봉투 + 핵심 엔드포인트 회귀). TestClient로 인프로세스 실행.
실행: cd backend && ../.venv/Scripts/python -m pytest -q"""
from fastapi.testclient import TestClient
from app.main import app
from app.config import API_KEY

client = TestClient(app)
H = {"x-api-key": API_KEY}


def _env(r):
    """응답이 {ok,data,meta,error} 봉투인지 확인하고 반환."""
    j = r.json()
    assert {"ok", "data", "meta", "error"} <= set(j), f"봉투 아님: {j}"
    return j


def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    j = _env(r)
    assert j["ok"] and j["data"]["server"] == "fastapi"


def test_auth_required_401():
    r = client.get("/models")            # 키 없음
    assert r.status_code == 401
    assert _env(r)["ok"] is False


def test_models_envelope():
    j = _env(client.get("/models", headers=H))
    assert j["ok"] and "models" in j["data"]


def test_dashboard_summary_has_models():
    j = _env(client.get("/dashboard/summary", headers=H))
    assert j["ok"] and isinstance(j["data"]["models"], list) and j["data"]["models"]


def test_baseline_chart_rowlist():
    j = _env(client.get("/dashboard/charts/baseline-comparison", headers=H))
    rows = j["data"]["data"]
    assert rows and "model_name" in rows[0] and "roc_auc" in rows[0]


def test_model_chart_roc_rowlist():
    j = _env(client.get("/models/CatBoost/charts/roc-auc", headers=H))
    d = j["data"]
    assert d["chart_name"] == "roc_auc" and d["data"] and "fpr" in d["data"][0]


def test_predict_bad_model_id_no_500():
    # FK 견고화: 미등록 model_id여도 500 없이 기록(null 처리)
    r = client.post("/predict", headers=H,
                    json={"user_id": "pytest_u", "churn_probability": 0.7, "model_id": 999999999})
    assert r.status_code == 200 and _env(r)["ok"]


def test_validation_error_envelope():
    r = client.post("/models/submit", headers=H, json={"bad": "x"})
    assert r.status_code == 422 and _env(r)["ok"] is False


def test_top_risk_shape():
    j = _env(client.get("/predictions/top-risk?limit=3", headers=H))
    assert j["ok"] and "users" in j["data"]
