import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { SessionManager, EventLogger } from '@/lib/eventLogger';
import { getChurnPrediction, BackendDisconnectedError } from '@/lib/fastApiClient';
import { AlertCircle, TrendingDown, ChevronRight, ChevronLeft } from 'lucide-react';

export default function FloatingChurnWidget() {
  const [churnRate, setChurnRate] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const session = SessionManager.getOrCreateSession();

  useEffect(() => {
    let active = true;
    // 세션 이벤트를 백엔드(/api/churn/predict)로 보내 실제 모델 이탈확률을 받는다(랜덤 아님).
    const fetchChurnRate = async () => {
      setIsLoading(true);
      try {
        const raw = await EventLogger.getSessionEvents(session.sessionId);
        const events = (raw as Record<string, unknown>[]).map(e => ({
          event_type: String(e.eventType ?? e.event_type ?? 'view'),
          product_id: String(e.productId ?? e.product_id ?? ''),
          category_id: String(e.categoryId ?? e.category_id ?? ''),
          brand: String(e.brand ?? ''),
          price: Number(e.price ?? 0),
          quantity: Number(e.quantity ?? 1),
          // 백엔드 hazard 가 inter-event 간격/유휴를 쓰므로 반드시 ISO 로 보낸다.
          timestamp: e.eventTime instanceof Date
            ? e.eventTime.toISOString()
            : String(e.eventTime ?? e.event_time ?? new Date().toISOString()),
        }));
        // 무상태 채점: 호출마다 ephemeral session_id → 백엔드가 버퍼 전체를 1회만 채점(이중 누적 방지).
        const churnSid = `${session.sessionId}:t${Date.now()}`;
        const resp = await getChurnPrediction(churnSid, session.userId, events);
        if (!active) return;
        // 백엔드가 0~1 또는 0~100 어느 쪽으로 주든 %로 정규화
        const p = resp.churn_probability;
        const pct = p <= 1 ? p * 100 : p;
        const rounded = Math.round(pct * 10) / 10;
        // 새 값이 0(세션 이벤트 없음 등)이면 직전 퍼센트를 유지 → 0%로 깜빡이지 않게
        setChurnRate(prev => (rounded <= 0 && prev !== null ? prev : rounded));
        setError(null);
      } catch (err) {
        if (!active) return;
        setChurnRate(null);
        setError(err instanceof BackendDisconnectedError
          ? '백엔드 미연결 — 실확률 불가'
          : '이탈확률 조회 실패');
      } finally {
        if (active) setIsLoading(false);
      }
    };

    // 즉시 1회 + 이후 4초마다 백엔드 재조회
    fetchChurnRate();
    const interval = setInterval(fetchChurnRate, 4000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [session.sessionId, session.userId]);

  const getChurnColor = (rate: number | null) => {
    if (rate === null) return 'text-slate-400';
    if (rate < 30) return 'text-green-400';
    if (rate < 60) return 'text-yellow-400';
    return 'text-red-400';
  };

  const getChurnBgColor = (rate: number | null) => {
    if (rate === null) return 'bg-slate-700/20';
    if (rate < 30) return 'bg-green-500/10';
    if (rate < 60) return 'bg-yellow-500/10';
    return 'bg-red-500/10';
  };

  return (
    <div className="fixed left-6 bottom-6 z-40 w-80">
      <Card className={`bg-slate-800 border-slate-700 transition-all duration-300 ${
        isCollapsed ? 'p-3' : 'p-4'
      }`}>
        {/* Header with Toggle */}
        <div className="flex items-center justify-between">
          {!isCollapsed && (
            <div className="flex items-center gap-2 flex-1">
              <TrendingDown className="w-5 h-5 text-slate-400" />
              <h3 className="font-semibold text-slate-100">Churn Rate</h3>
            </div>
          )}
          
          {/* Churn Rate Display (Always Visible) */}
          <div className={`flex items-center gap-2 ${isCollapsed ? 'flex-1 justify-center' : ''}`}>
            {isLoading && (
              <div className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse"></div>
            )}
            {churnRate !== null && !error && (
              <div className={`font-bold text-lg ${getChurnColor(churnRate)}`}>
                {churnRate.toFixed(1)}%
              </div>
            )}
          </div>

          {/* Toggle Button */}
          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="text-slate-400 hover:text-slate-100 transition-colors ml-2"
          >
            {isCollapsed ? (
              <ChevronRight className="w-4 h-4" />
            ) : (
              <ChevronLeft className="w-4 h-4" />
            )}
          </button>
        </div>

        {/* Expanded Content */}
        {!isCollapsed && (
          <>
            <div className={`rounded-lg p-4 mt-3 ${getChurnBgColor(churnRate)}`}>
              {error ? (
                <div className="flex items-center gap-2 text-red-400 text-sm">
                  <AlertCircle className="w-4 h-4" />
                  <span>{error}</span>
                </div>
              ) : churnRate === null ? (
                <div className="text-slate-400 text-sm">Loading...</div>
              ) : (
                <div>
                  <p className="text-xs text-slate-400">
                    Estimated churn probability for this session
                  </p>
                </div>
              )}
            </div>

            {/* Progress Bar */}
            {churnRate !== null && !error && (
              <div className="mt-4">
                <div className="w-full h-2 bg-slate-700 rounded-full overflow-hidden">
                  <div
                    className={`h-full transition-all duration-500 ${
                      churnRate < 30
                        ? 'bg-gradient-to-r from-green-500 to-green-400'
                        : churnRate < 60
                        ? 'bg-gradient-to-r from-yellow-500 to-yellow-400'
                        : 'bg-gradient-to-r from-red-500 to-red-400'
                    }`}
                    style={{ width: `${churnRate}%` }}
                  />
                </div>
                <div className="flex justify-between text-xs text-slate-500 mt-1">
                  <span>Low Risk</span>
                  <span>High Risk</span>
                </div>
              </div>
            )}

            {/* Info */}
            <p className="text-xs text-slate-500 mt-4">
              이탈예측 백엔드 실추론 · 세션 활동 기반 4초마다 갱신
            </p>
          </>
        )}
      </Card>
    </div>
  );
}
