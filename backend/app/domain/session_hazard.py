# -*- coding: utf-8 -*-
"""domain — 실시간 세션 이탈위험 휴리스틱(A). 모델 아님, 운영 규칙.

근거: 17-2 초단위 세션이탈 프로토콜. inter-event 간격을 공변량으로 한 *이산시간 생존분석/
hazard* 의 경량 닫힌형(closed-form). 학습(라벨 최적화) 없음 → 설명 가능.

핵심:
- 세션을 "수명"으로 보고, 다음 이벤트까지의 대기시간을 Weibull 로 모델링.
  S(gap)=exp(-(gap/τ)^k) = "간격 gap 이 흐른 지금 세션이 살아있을 확률".
  risk = 1 - S = 이탈(무구매 세션 포기) 위험. k>1 → idle 길수록 hazard 가속.
- τ·k 는 17-2 가 측정한 REES46 세션 내 간격 분포(중앙 18s, p75 61s, p90 168s, 경계 1800s)에
  캘리브레이션한 값(데이터 기반 파라미터 설정이지 학습이 아님).
- 인게이지먼트(전환 의도) 보정: 구매=거의 이탈 안 함, 카트보유=의도 있음(위험↓),
  뷰만 누적=구경만(위험↑), 담았다 다 뺌=이탈 징후(위험↑).

B(모델팀 세션모델) 부재 시 폴백으로 사용. session_bounce(개인 실험물)는 쓰지 않는다.
"""
import math

# Weibull 파라미터 — 17-2 세션 내 간격 분포(중앙 18s/p75 61s/p90 168s, 경계 1800s)에 캘리브레이션.
# p90=168s 부근을 "중위험(≈0.45)" 변곡점으로 두도록 분위수 맞춤 → TAU≈250, K=1.3.
# 결과 곡선: 18s→~3%, 61s→~14%, 168s→~45%, 600s→~95%, 1800s→~100%.
TAU = 250.0       # sec — 특성 idle 척도
K = 1.3           # shape(>1 → 가속 hazard)
GAP_SEC = 1800    # 세션 경계(30분, 17-2/업계 표준)
RISK_HIGH, RISK_LOW = 0.65, 0.35


def _weibull_risk(gap_sec: float) -> float:
    """간격(초) → 이탈 hazard 기반 위험(0~1)."""
    if gap_sec <= 0:
        return 0.0
    g = min(gap_sec, GAP_SEC)
    return 1.0 - math.exp(-((g / TAU) ** K))


def _level(p: float) -> str:
    return "high" if p >= RISK_HIGH else "medium" if p >= RISK_LOW else "low"


def session_risk(events: list, now_ts: float = None) -> dict:
    """events: [{'type','ts'(epoch sec|None),'price'}] (시간순) → 세션 이탈임박 확률 + 설명.

    now_ts: 현재 epoch(sec). 주면 '마지막 이벤트 이후 경과시간'도 hazard 간격에 반영(유휴 시 위험↑).
    반환: {'p':0~1, 'risk_level', 'source':'hazard', 'detail':{...}}.
    """
    if not events:
        return {"p": 0.0, "risk_level": "low", "source": "hazard",
                "detail": {"reason": "no_events"}}

    n = len(events)
    types = [e.get("type") for e in events]
    n_view = types.count("view")
    n_cart = types.count("cart")
    n_remove = types.count("remove")
    n_purch = types.count("purchase")

    # hazard 간격 = max(마지막 inter-event 간격, 마지막 이벤트 후 경과시간).
    # 전자=이벤트 구동 신호(17-2 권장), 후자=폴링 중 유휴 에스컬레이션.
    ts = [e.get("ts") for e in events if e.get("ts") is not None]
    last_gap = (ts[-1] - ts[-2]) if len(ts) >= 2 else 0.0
    idle = (now_ts - ts[-1]) if (now_ts is not None and ts) else 0.0
    gap = max(last_gap, idle)
    if gap <= 0:
        gap = TAU * 0.1            # ts 정보 없음 → 활발 가정(낮은 위험)
    base = _weibull_risk(gap)

    # 인게이지먼트 보정(전환 의도)
    has_cart = (n_cart - n_remove) > 0
    if n_purch > 0:
        mult = 0.15                      # 구매 = 거의 이탈 안 함
    elif has_cart:
        mult = 0.55                      # 카트 보유 = 의도 있음 → 위험↓
    elif n_view >= 3 and n_cart == 0:
        mult = 1.25                      # 뷰만 누적 = 구경만 → 위험↑
    else:
        mult = 1.0
    if n_cart > 0 and n_remove >= n_cart:
        mult *= 1.3                      # 담았다 다 뺌 = 이탈 징후

    p = max(0.0, min(1.0, base * mult))
    return {"p": round(p, 4), "risk_level": _level(p), "source": "hazard",
            "detail": {"hazard_gap_sec": round(gap, 1), "last_gap_sec": round(last_gap, 1),
                       "idle_sec": round(idle, 1), "weibull_base": round(base, 4),
                       "engagement_mult": round(mult, 3), "step": n,
                       "n_view": n_view, "n_cart": n_cart, "n_remove": n_remove,
                       "n_purchase": n_purch, "tau": TAU, "k": K}}
