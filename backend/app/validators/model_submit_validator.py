# -*- coding: utf-8 -*-
"""validators — 제출 payload 추가 검증(경량). Node `validators/schemas.js` 포팅.
Pydantic 스키마 외에 도메인 규칙(model_type 허용값 등)을 검증한다."""

ALLOWED_TYPES = ("tree", "linear", "sequence", "ensemble")


def validate_model_submit(b: dict):
    if not isinstance(b, dict):
        return "body 없음"
    for k in ("model_name", "model_type", "artifact_path"):
        if not b.get(k):
            return f"필수 누락: {k}"
    if b["model_type"] not in ALLOWED_TYPES:
        return f"model_type 허용값 아님(허용: {ALLOWED_TYPES})"
    if b.get("metrics") is not None and not isinstance(b["metrics"], dict):
        return "metrics 는 객체"
    if b.get("evaluation") is not None and not isinstance(b["evaluation"], dict):
        return "evaluation 은 객체"
    return None
