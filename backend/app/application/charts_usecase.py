# -*- coding: utf-8 -*-
"""application — 차트/대시보드 조회 usecase(19-4 §8). artifact-first(모델팀 산출물 우선)."""
from app.infrastructure.files import eval_artifacts as art
from app.infrastructure.files import dataset_reader as ds


def get_model_chart(model, chart_name) -> dict:
    """5~15번 모델 종속 차트. 산출물 없으면 빈 data(19-4 빈상태 규칙)."""
    out = art.model_chart(model, chart_name)
    if out is None:
        return {"_status": 404, "error": f"미지원 chart: {chart_name}"}
    return out


def get_dashboard_chart(chart_name) -> dict:
    """1~4번 모델 비종속 차트."""
    cn = chart_name.replace("_", "-")
    if cn == "baseline-comparison":
        return {"chart_name": "baseline_comparison", "chart_type": "bar", "x": "model_name",
                "y": ["roc_auc", "pr_auc", "f1"], "data": ds.baseline_comparison(),
                "meta": {"schema_version": "chart.v1", "source": "metrics_summary"}}
    if cn == "data-distribution":
        return {"chart_name": "data_distribution", "chart_type": "histogram", "x": "bin", "y": "count",
                "data": ds.data_distribution(), "meta": {"schema_version": "chart.v1", "source": "canonical"}}
    if cn == "cohort-retention":
        return {"chart_name": "cohort_retention", "chart_type": "heatmap", "x": "week_index", "y": "cohort",
                "data": [], "meta": {"schema_version": "chart.v1", "source": "pending"}}
    if cn == "system-architecture":
        return {"chart_name": "system_architecture", "chart_type": "image", "x": None, "y": None,
                "data": {"asset_path": "assets/architecture.svg"},
                "meta": {"schema_version": "chart.v1", "source": "static"}}
    return {"_status": 404, "error": f"미지원 dashboard chart: {chart_name}"}


def get_user_dashboard(user_id) -> dict:
    d = ds.user_dashboard(user_id)
    if not d:
        return {"_status": 404, "error": f"유저 데이터 없음: {user_id}"}
    return d


def get_recommendations(user_id) -> dict:
    rec = ds.recommendations(user_id)
    return {"user_id": user_id, **rec}
