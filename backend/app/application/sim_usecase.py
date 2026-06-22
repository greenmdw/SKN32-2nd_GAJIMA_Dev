# -*- coding: utf-8 -*-
"""application — 시뮬 사이트 실시간 이탈예측 루프(26-9 P2, 19-2 §9.2).
유저 세션 행동(view/cart/remove/purchase) → v2 피처 집계 → 활성 모델 직접 추론 → 위험등급 →
리텐션/추천 push. 세션은 메모리(점수 권위), 이벤트는 sim_event_log·예측은 prediction_log에 영속.
피처는 응답에 그대로 노출(전처리 투명성)."""
from app.domain.risk_level import risk_level, retention_action
from app.domain import session_hazard
from app.config import MODELS_DIR, DATA_DIR
from app.infrastructure.files import catalog_store as cat
from app.infrastructure.model_inference import python_model_loader as loader
from app.infrastructure.mysql.session import (sim_event_repository, prediction_repository,
                                              model_repository)

FEATURE_ORDER = ["recency_days", "tenure_days", "ndays", "n_events", "n_view", "n_cart",
                 "n_remove_from_cart", "n_purchase", "avg_price", "purch_amt",
                 "min_price", "max_price", "std_price", "purchase_avg_price",
                 "remove_ratio", "cart_purchase_ratio", "n_categories", "cat_entropy",
                 "n_brands", "brand_loyalty", "n_sessions", "events_per_session"]   # v2 22피처 전체

# 프로필 베이스라인(recency_days, tenure_days, ndays, n_sessions). recency가 7일 이탈을 지배 → 프로필로 시드.
PROFILES = {
    "new":       {"recency_days": 0, "tenure_days": 1,   "ndays": 1,  "n_sessions": 1},
    "returning": {"recency_days": 1, "tenure_days": 30,  "ndays": 6,  "n_sessions": 6},
    "loyal":     {"recency_days": 0, "tenure_days": 180, "ndays": 42, "n_sessions": 42},
    "lapsing":   {"recency_days": 6, "tenure_days": 90,  "ndays": 9,  "n_sessions": 9},  # 식어가는 유저(고위험 베이스)
}

import math
import time
from collections import OrderedDict
_SESSIONS = OrderedDict()   # session_id -> {user_id, profile, events:[...], _ts}  (LRU + idle TTL)
MAX_SESSIONS = 500          # 동시 세션 상한(초과 시 가장 오래된 것 evict)
MAX_EVENTS = 300            # 세션당 이벤트 상한(최근 것만 유지)
SESSION_IDLE_SEC = 1800     # 세션 idle 타임아웃(30분 무활동 시 만료)


def sweep_sessions(idle_sec=SESSION_IDLE_SEC) -> int:
    """idle 초과 세션 제거(스케줄러가 주기 호출). 제거 수 반환."""
    now = time.monotonic()
    stale = [k for k, v in _SESSIONS.items() if now - v.get("_ts", now) > idle_sec]
    for k in stale:
        _SESSIONS.pop(k, None)
    return len(stale)


def _active_model():
    try:
        rows = model_repository.active()
        if rows:
            return str(rows[0]["model_name"]).replace("_Churn_v2", "").replace("_v2", "")
    except Exception:
        pass
    return "CatBoost"


def _session(session_id, user_id=None, profile="returning"):
    s = _SESSIONS.get(session_id)
    if not s:
        while len(_SESSIONS) >= MAX_SESSIONS:        # 가장 오래된 세션 evict(LRU)
            _SESSIONS.popitem(last=False)
        s = {"user_id": user_id or session_id, "profile": profile, "events": [], "_ts": time.monotonic()}
        _SESSIONS[session_id] = s
    else:
        _SESSIONS.move_to_end(session_id)            # 최근 사용 표시
    s["_ts"] = time.monotonic()                       # idle TTL 갱신
    return s


def reset(session_id):
    _SESSIONS.pop(session_id, None)
    return {"session_id": session_id, "reset": True}


def _entropy(items):
    """카테고리 분포 Shannon 엔트로피(자연로그)."""
    if not items:
        return 0.0
    from collections import Counter
    n = len(items)
    return float(-sum((c / n) * math.log(c / n) for c in Counter(items).values()))


def _max_share(items):
    """최빈 항목 점유율(브랜드 충성도 proxy)."""
    if not items:
        return 0.0
    from collections import Counter
    return max(Counter(items).values()) / len(items)


def _features(s):
    """세션 이벤트 → v2 22피처 집계(모델 기대치 전체). 누락=NaN 방지 위해 22개 모두 채운다."""
    ev = s["events"]
    n_view = sum(1 for e in ev if e["type"] == "view")
    n_cart = sum(1 for e in ev if e["type"] == "cart")
    n_remove = sum(1 for e in ev if e["type"] == "remove")
    n_purchase = sum(1 for e in ev if e["type"] == "purchase")
    prices = [float(e["price"]) for e in ev if e.get("price")]
    purch = [float(e["price"]) for e in ev if e["type"] == "purchase" and e.get("price")]
    cats = [e["category_id"] for e in ev if e.get("category_id")]
    brands = [e["brand"] for e in ev if e.get("brand")]

    base = dict(PROFILES.get(s["profile"], PROFILES["returning"]))
    if n_purchase:                                   # 구매=강한 인게이지먼트 → 방금 활동
        base["recency_days"] = 0

    n_events = len(ev)
    n_sessions = base.get("n_sessions", 1) or 1
    avg_price = sum(prices) / len(prices) if prices else 0.0
    std_price = (sum((p - avg_price) ** 2 for p in prices) / len(prices)) ** 0.5 if len(prices) > 1 else 0.0

    return {
        "recency_days": base["recency_days"], "tenure_days": base["tenure_days"], "ndays": base["ndays"],
        "n_events": n_events, "n_view": n_view, "n_cart": n_cart,
        "n_remove_from_cart": n_remove, "n_purchase": n_purchase,
        "avg_price": round(avg_price, 2), "purch_amt": round(sum(purch), 2),
        "min_price": round(min(prices), 2) if prices else 0.0,
        "max_price": round(max(prices), 2) if prices else 0.0,
        "std_price": round(std_price, 2),
        "purchase_avg_price": round(sum(purch) / len(purch), 2) if purch else 0.0,
        "remove_ratio": round(n_remove / n_cart, 4) if n_cart else 0.0,
        "cart_purchase_ratio": round(n_purchase / n_cart, 4) if n_cart else 0.0,
        "n_categories": len(set(cats)), "cat_entropy": round(_entropy(cats), 4),
        "n_brands": len(set(brands)), "brand_loyalty": round(_max_share(brands), 4),
        "n_sessions": n_sessions, "events_per_session": round(n_events / n_sessions, 4),
    }


def _top_category(s):
    cnt = {}
    for e in s["events"]:
        if e.get("category_id"):
            cnt[e["category_id"]] = cnt.get(e["category_id"], 0) + 1
    return max(cnt, key=cnt.get) if cnt else None


def score_session(session_id, model=None):
    s = _SESSIONS.get(session_id)
    if not s or not s["events"]:
        return {"_status": 404, "error": "세션 이벤트 없음(먼저 행동을 기록하세요)"}
    model = model or _active_model()
    if not loader.available(model):
        return {"_status": 503, "error": f"모델 번들 로드 불가: {model}"}
    import pandas as pd
    feats = _features(s)
    X = pd.DataFrame([feats])[FEATURE_ORDER]
    probs = loader.score(model, X)
    if not probs:
        return {"_status": 500, "error": "추론 실패"}
    p = round(float(probs[0]), 4)
    r = risk_level(p)
    act = retention_action(p)
    # 추천: 세션 최다 관심 카테고리 → 유사 카테고리(고위험일 때 리텐션 push)
    recs = []
    tc = _top_category(s)
    if tc:
        recs = cat.similar_categories(tc, k=3)
    # 영속: 예측 로그(top-risk/대시보드 반영)
    prediction_repository.log({"model_id": None, "user_id": str(s["user_id"]),
                               "churn_probability": p, "risk_level": r,
                               "recommended_action": act["action_message"]})
    return {"session_id": session_id, "user_id": s["user_id"], "model": model,
            "churn_probability": p, "risk_level": r, "horizon_days": 7,
            "recommended_action": act["action_message"],
            "push_retention": (r == "high"),
            "recommendations": recs, "features": feats, "event_count": len(s["events"]),
            "source": "live-session-inference"}


def score_from_events(session_id, user_id, events):
    """배치 이벤트로 세션을 채워 채점(시뮬 사이트 /api/churn/predict 어댑터용). sim_event_log엔 기록 안 함."""
    s = _session(session_id, user_id)
    for e in (events or []):
        s["events"].append({"type": e.get("event_type"), "price": e.get("price"),
                            "category_id": e.get("category_id"), "brand": e.get("brand")})
    if len(s["events"]) > MAX_EVENTS:
        s["events"][:] = s["events"][-MAX_EVENTS:]
    return score_session(session_id)


# ── 실시간 세션 이탈값: 3단 폴백 체인 (B-모델 → B-데이터백업 → A-하자드) ──────────
# B 는 모델팀(모델 브런치) 산출물 파일이 있을 때만 동작(임의 구현 X). 없으면 A(하자드).
_SESSION_MODEL_PATH = MODELS_DIR / "churn" / "_realtime" / "session_model.joblib"
_SESSION_DATA_PATH = DATA_DIR / "realtime" / "session_predictions.json"


def _parse_ts(s):
    """ISO 문자열 → epoch sec. 실패 시 None."""
    if not s:
        return None
    try:
        from datetime import datetime
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).timestamp()
    except Exception:
        return None


def _session_feature_row(evs):
    """세션 이벤트 → 흔한 세션 피처 dict(모델 tier 가 bundle['feat']로 골라 씀)."""
    import math
    n = len(evs)
    ts = [e["ts"] for e in evs if e.get("ts") is not None]
    last_gap = (ts[-1] - ts[-2]) if len(ts) >= 2 else 0.0
    prices = [float(e["price"]) for e in evs if e.get("price")]
    def c(t): return sum(1 for e in evs if e["type"] == t)
    return {
        "step": n, "dt_prev_log": math.log1p(max(last_gap, 0.0)),
        "n_view": c("view"), "n_cart": c("cart"), "n_purchase": c("purchase"),
        "n_view_sf": c("view"), "n_cart_sf": c("cart"), "n_purchase_sf": c("purchase"),
        "price_log": math.log1p(prices[-1]) if prices else 0.0,
        "price_mean_sf_log": math.log1p(sum(prices) / len(prices)) if prices else 0.0,
        "is_first": 1 if n <= 1 else 0,
    }


def _b_model_tier(evs):
    """B-주: 모델팀 세션모델(models/churn/_realtime/session_model.joblib). 없으면 None.
    계약: {pipeline, feat:[...]}. 파일 있을 때만 추론(임의 구현 아님). 불일치/오류 시 None→다음 tier."""
    if not _SESSION_MODEL_PATH.exists():
        return None
    try:
        import joblib, pandas as pd
        b = joblib.load(_SESSION_MODEL_PATH)
        feat = b.get("feat") or []
        row = _session_feature_row(evs)
        X = pd.DataFrame([{k: row.get(k, 0.0) for k in feat}])
        p = float(b["pipeline"].predict_proba(X)[:, 1][0])
        return {"p": round(p, 4), "risk_level": session_hazard._level(p), "source": "model"}
    except Exception:
        return None


def _b_data_tier(evs):
    """B-백업: data/ 폴더 precomputed(data/realtime/session_predictions.json). 없으면 None."""
    if not _SESSION_DATA_PATH.exists():
        return None
    try:
        import json
        data = json.loads(_SESSION_DATA_PATH.read_text(encoding="utf-8"))
        # 계약(활성화 시): step→확률 룩업 등. 미정의면 None.
        key = str(len(evs))
        if isinstance(data, dict) and key in data:
            p = float(data[key])
            return {"p": round(p, 4), "risk_level": session_hazard._level(p), "source": "data"}
    except Exception:
        pass
    return None


def realtime_session_score(session_id, user_id, events):
    """시뮬 실시간 세션 이탈값. B-모델 → B-데이터백업 → A-하자드 순 폴백."""
    evs = []
    for e in (events or []):
        evs.append({"type": e.get("event_type"), "price": e.get("price"),
                    "category_id": e.get("category_id"), "brand": e.get("brand"),
                    "ts": _parse_ts(e.get("timestamp"))})
    evs.sort(key=lambda x: (x["ts"] is None, x["ts"] or 0))   # 시간순(ts 없으면 뒤로)
    r = _b_model_tier(evs) or _b_data_tier(evs)
    if r is None:
        from datetime import datetime, timezone
        r = session_hazard.session_risk(evs, now_ts=datetime.now(timezone.utc).timestamp())
    return {"churn_probability": r["p"], "risk_level": r["risk_level"],
            "source": r["source"], "detail": r.get("detail")}


def session_analytics(session_id):
    """세션 이벤트 요약(시뮬 사이트 /api/analytics 어댑터용)."""
    s = _SESSIONS.get(session_id)
    evs = s["events"] if s else []
    bd = {}
    for e in evs:
        bd[e["type"]] = bd.get(e["type"], 0) + 1
    return {"total_events": len(evs), "event_breakdown": bd,
            "products_viewed": bd.get("view", 0), "products_in_cart": bd.get("cart", 0),
            "purchases": bd.get("purchase", 0)}


def record_event(session_id, user_id, event_type, product_id=None, category_id=None,
                 brand=None, price=None, profile="returning"):
    s = _session(session_id, user_id, profile)
    if profile:
        s["profile"] = profile
    s["events"].append({"type": event_type, "price": price, "category_id": category_id, "brand": brand})
    if len(s["events"]) > MAX_EVENTS:                 # 세션당 이벤트 상한
        s["events"][:] = s["events"][-MAX_EVENTS:]
    scored = score_session(session_id)
    # 이벤트 영속(점수 스냅샷 동반)
    sim_event_repository.log({
        "user_id": str(s["user_id"]), "session_id": session_id, "event_type": event_type,
        "product_id": product_id, "category_id": category_id, "brand": brand, "price": price,
        "churn_prob": scored.get("churn_probability"), "risk_level": scored.get("risk_level")})
    return scored
