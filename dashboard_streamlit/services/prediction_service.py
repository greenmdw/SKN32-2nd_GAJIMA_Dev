# -*- coding: utf-8 -*-
"""services/prediction_service — /predictions/* 호출(19-4 §7.2). 백엔드 REST."""
from services import api_client as api


def get_latest(user_id):
    return api.get(f"/predictions/latest?user_id={user_id}", mock_path="latest_prediction")


def get_top_risk(limit=20, min_prob=0.0):
    return api.get(f"/predictions/top-risk?limit={limit}&min_prob={min_prob}", mock_path="top_risk")


def predict(user_id, churn_probability, model_id=None):
    return api.post("/predict",
                    {"user_id": user_id, "churn_probability": churn_probability, "model_id": model_id})
