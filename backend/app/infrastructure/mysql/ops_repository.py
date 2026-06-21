# -*- coding: utf-8 -*-
"""infrastructure/mysql — 리텐션/추천 액션 적재(19-2 §6.1). memory 폴백."""
import json
from app.infrastructure.mysql.session import mode, _q, _mem

_mem.setdefault("retention_actions", [])
_mem.setdefault("recommendations", [])


def add_retention_action(user_id, action_type, message, prediction_id=None) -> dict:
    if mode() == "mysql":
        aid = _q("""INSERT INTO retention_action_log(prediction_id,user_id,action_type,action_message,status)
                    VALUES(%s,%s,%s,%s,'suggested')""",
                 (prediction_id, user_id, action_type, message))
        return {"action_id": aid, "user_id": user_id, "action_type": action_type, "status": "suggested"}
    aid = len(_mem["retention_actions"]) + 1
    rec = {"action_id": aid, "user_id": user_id, "action_type": action_type,
           "action_message": message, "status": "suggested"}
    _mem["retention_actions"].append(rec)
    return rec


def save_recommendation(user_id, rec_items, rec_categories, model_id=None) -> dict:
    if mode() == "mysql":
        rid = _q("""INSERT INTO recommendation(user_id,model_id,rec_items_json,rec_categories_json)
                    VALUES(%s,%s,%s,%s)""",
                 (user_id, model_id, json.dumps(rec_items, ensure_ascii=False),
                  json.dumps(rec_categories, ensure_ascii=False)))
        return {"rec_id": rid, "user_id": user_id}
    rid = len(_mem["recommendations"]) + 1
    _mem["recommendations"].append({"rec_id": rid, "user_id": user_id,
                                    "items": rec_items, "categories": rec_categories})
    return {"rec_id": rid, "user_id": user_id}
