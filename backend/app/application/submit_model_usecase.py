# -*- coding: utf-8 -*-
"""application — 모델 등록/조회 usecase(19-2 §9.1). 도메인+repository 조립, SQL 직접 안 함."""
from app.infrastructure.mysql.session import (model_repository, evaluation_repository, mode)
from app.validators.model_submit_validator import validate_model_submit


def submit_model(body: dict) -> dict:
    err = validate_model_submit(body)
    if err:
        return {"_status": 400, "error": err}
    reg = model_repository.upsert(body)
    eval_id = None
    if body.get("evaluation") or body.get("metrics"):
        m = body.get("metrics") or {}
        ev = body.get("evaluation") or {}
        eval_id = evaluation_repository.insert(reg["model_id"], {
            "dataset_tag": body.get("label_name", "churn"),
            "roc_auc": m.get("roc_auc"), "pr_auc": m.get("pr_auc"),
            "best_threshold": m.get("best_threshold"), "best_f1": m.get("best_f1"),
            "eval_predictions_path": ev.get("eval_predictions_path"),
            "shap_summary_path": ev.get("shap_summary_path"),
        })["eval_id"]
    return {"model_id": reg["model_id"], "eval_id": eval_id, "mode": reg["mode"]}


def list_models() -> dict:
    return {"models": model_repository.list() or [], "mode": mode()}


def list_active() -> dict:
    return {"models": model_repository.active() or [], "mode": mode()}


def get_model_evaluation(model_id) -> dict:
    try:
        mid = int(model_id)
    except (ValueError, TypeError):
        # 이름이 오면 artifact metrics로 대체
        from app.infrastructure.files import eval_artifacts as art
        m = art.model_metrics(model_id)
        return {"model_id": model_id, "evaluations": ([m] if m else [])}
    rows = evaluation_repository.for_model(mid)
    return {"model_id": mid, "evaluations": rows or []}
