# -*- coding: utf-8 -*-
"""services/recommendation_service — /recommendations/*, /retention-actions(19-4 §7.2)."""
from services import api_client as api


def get_recommendations(user_id):
    return api.get(f"/recommendations/{user_id}", mock_path="recommendations")


def create_retention_action(user_id, action_type, message, prediction_id=None):
    return api.post("/retention-actions",
                    {"user_id": user_id, "action_type": action_type,
                     "message": message, "prediction_id": prediction_id})
