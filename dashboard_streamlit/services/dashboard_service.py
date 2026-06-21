# -*- coding: utf-8 -*-
"""services/dashboard_service — /dashboard/*, /models/* 호출(19-4 §5·§7.2). 백엔드 REST(봉투)."""
from services import api_client as api


def get_summary():
    return api.get("/dashboard/summary", mock_path="dashboard_summary")


def get_models():
    return api.get("/models", mock_path="models")


def get_active_models():
    return api.get("/models/active", mock_path="models")


def get_model_evaluation(model_id):
    return api.get(f"/models/{model_id}/evaluation", mock_path="model_evaluation")


def get_model_chart(model, chart_name):
    """모델 종속 차트(kebab): pr-auc·roc-auc·threshold·calibration·confusion-matrix·lift·
    score-distribution·shap-summary·value-at-risk·revenue-recovery·train-val-loss."""
    return api.get(f"/models/{model}/charts/{chart_name}", mock_path=f"charts/{chart_name}")


def get_dashboard_chart(chart_name):
    """모델 비종속 차트: system-architecture·data-distribution·cohort-retention·baseline-comparison."""
    return api.get(f"/dashboard/charts/{chart_name}", mock_path=f"charts/{chart_name}")


def get_user(user_id):
    return api.get(f"/dashboard/user/{user_id}", mock_path="user_dashboard")
