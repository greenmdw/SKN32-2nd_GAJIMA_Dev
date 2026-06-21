# -*- coding: utf-8 -*-
"""schemas — Pydantic 요청/응답 모델(19-2 §5). POST /models/submit payload(§7.3)."""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class MetricsIn(BaseModel):
    roc_auc: Optional[float] = None
    pr_auc: Optional[float] = None
    best_threshold: Optional[float] = None
    best_f1: Optional[float] = None


class EvaluationIn(BaseModel):
    eval_predictions_path: Optional[str] = None
    shap_summary_path: Optional[str] = None


class ModelSubmitIn(BaseModel):
    model_name: str
    model_type: str = Field(description="tree|linear|sequence|ensemble")
    feature_schema_version: str = "v2"
    label_name: str = "churn"
    horizon_days: int = 7
    preprocessing_config: Optional[Dict[str, Any]] = None
    dataset_path: Optional[str] = None
    artifact_path: str
    metrics: Optional[MetricsIn] = None
    evaluation: Optional[EvaluationIn] = None
    is_active: bool = False

    model_config = {"protected_namespaces": ()}      # model_* 필드명 허용


class PredictIn(BaseModel):
    user_id: str
    churn_probability: float
    model_id: Optional[int] = None


class EnsembleMember(BaseModel):
    model_id: Optional[int] = None
    prob: float
    weight: float = 1.0

    model_config = {"protected_namespaces": ()}


class EnsembleIn(BaseModel):
    members: List[EnsembleMember]
