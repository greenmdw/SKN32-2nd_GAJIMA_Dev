# -*- coding: utf-8 -*-
"""infrastructure/files — 운영 조회용 데이터셋 reader(유저 대시보드·추천·데이터분포).
eval_predictions/recommendation 카탈로그를 읽어 chart-ready로 변환. 캐시(lru)."""
import json
from functools import lru_cache
from app.config import EVAL_DIR, REC_DIR, DATA_DIR

CHURN_DIR = DATA_DIR / "churn"
RISK_HIGH, RISK_LOW = 0.65, 0.35


@lru_cache(maxsize=1)
def _preds():
    import pandas as pd
    p = EVAL_DIR / "eval_predictions.parquet"
    return pd.read_parquet(p) if p.exists() else pd.DataFrame()


@lru_cache(maxsize=1)
def _metrics():
    p = EVAL_DIR / "metrics_summary.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def baseline_comparison():
    """모델 비교(베이스라인): metrics_summary → 행리스트."""
    m = _metrics(); rows = []
    for k, v in m.items():
        if not isinstance(v, dict):
            continue
        auc = v.get("auc", v.get("val_auc"))
        if auc is None:
            continue
        rows.append({"model_name": k, "roc_auc": auc, "pr_auc": v.get("pr_auc"), "f1": v.get("f1")})
    rows.sort(key=lambda r: r["roc_auc"], reverse=True)
    return rows


def data_distribution(feature="recency_days", nbins=20):
    """canonical tabular의 피처 히스토그램(없으면 빈 리스트)."""
    import pandas as pd, numpy as np
    p = CHURN_DIR / "train_tabular_v2.parquet"
    if not p.exists():
        return []
    df = pd.read_parquet(p, columns=[feature]) if feature else pd.read_parquet(p)
    if feature not in df.columns:
        return []
    s = df[feature].astype(float)
    lo, hi = float(s.quantile(0.01)), float(s.quantile(0.99))
    if hi <= lo:
        hi = lo + 1
    edges = np.linspace(lo, hi, nbins + 1)
    cnt, _ = np.histogram(s.clip(lo, hi), bins=edges)
    return [{"feature": feature, "bin": round(float(edges[i]), 3), "count": int(cnt[i])} for i in range(nbins)]


def _risk(p):
    return "high" if p >= RISK_HIGH else ("medium" if p >= RISK_LOW else "low")


def user_dashboard(user_id, model="CatBoost"):
    """유저 최신 이탈확률(active 모델 기준) — eval_predictions에서 조회."""
    df = _preds()
    if df.empty:
        return None
    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        uid = user_id
    sub = df[(df.user_id == uid) & (df.model_name == model)]
    if sub.empty:
        sub = df[df.user_id == uid]
    if sub.empty:
        return None
    r = sub.iloc[0]
    p = float(r.y_score)
    return {"user_id": user_id, "model": str(r.model_name),
            "latest_prediction": {"churn_probability": round(p, 4), "risk_level": _risk(p),
                                  "top_category": int(r.get("top_category", 0)) if "top_category" in sub.columns else None,
                                  "top_brand": (str(r.top_brand) if "top_brand" in sub.columns else None)}}


def recommendations(user_id, model="CatBoost", topn=5):
    """유저 관심 카테고리(eval_predictions.top_category) → category_similar 유사 카테고리."""
    import pandas as pd
    df = _preds()
    sim_p = REC_DIR / "category_similar.parquet"
    cat_p = REC_DIR / "category_catalog.parquet"
    if df.empty or not sim_p.exists():
        return {"items": [], "categories": []}
    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        uid = user_id
    sub = df[df.user_id == uid]
    if sub.empty or "top_category" not in sub.columns:
        return {"items": [], "categories": []}
    seed = int(sub.iloc[0].top_category)
    sim = pd.read_parquet(sim_p)
    rows = sim[sim.category_id == seed].head(topn)
    cats = []
    catalog = pd.read_parquet(cat_p) if cat_p.exists() else pd.DataFrame()
    for _, r in rows.iterrows():
        cid = int(r.get("similar_category_id", 0))
        name = None
        if not catalog.empty and "category_id" in catalog.columns:
            hit = catalog[catalog.category_id == cid]
            if not hit.empty and "category_code" in hit.columns:
                name = hit.iloc[0].get("category_code")
        cats.append({"category_id": cid, "name": (str(name) if name is not None else str(cid)),
                     "score": round(float(r.get("cosine", 0)), 4)})
    return {"items": [], "categories": cats, "seed_category": seed}
