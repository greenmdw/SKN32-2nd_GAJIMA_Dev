# -*- coding: utf-8 -*-
"""application — 대시보드 요약/차트 usecase(19-2 §9.3). 차트 원천=학습 산출물 파일."""
from app.infrastructure.files import artifact_store as art


def get_dashboard_summary() -> dict:
    """관리자 요약: 모델 비교표(파일 원천 metrics_summary.json)."""
    m = art.metrics()
    tab = []
    for k, v in m.items():
        if not isinstance(v, dict):
            continue
        auc = v.get("auc", v.get("val_auc"))           # Transformer 는 val_auc
        if auc is None:
            continue
        tab.append({"model": k, "roc_auc": auc, "pr_auc": v.get("pr_auc"),
                    "brier": v.get("brier"), "ece": v.get("ece"),
                    "f1": v.get("f1"), "threshold": v.get("threshold"),
                    "val_only": "val_auc" in v})
    tab.sort(key=lambda x: x["roc_auc"], reverse=True)
    best = tab[0] if tab else None
    return {"best_model": best["model"] if best else None,
            "best_auc": best["roc_auc"] if best else None,
            "models": tab, "label": "churn", "horizon_days": 7,
            "title": "향후 7일 이내 이탈 확률"}


def get_model_charts(model: str, name: str) -> dict:
    """PR/ROC/threshold/calibration/shap/feature_importance chart JSON(19-2 §12)."""
    data = art.chart(model, name)
    if data is None:
        return {"_status": 404, "error": f"chart 없음: {model}/{name}"}
    return {"model": model, "chart": name, "data": data}
