import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { SessionManager } from '@/lib/eventLogger';
import { AlertCircle, TrendingDown } from 'lucide-react';

interface ChurnRateWidgetProps {
  className?: string;
}

export default function ChurnRateWidget({ className = '' }: ChurnRateWidgetProps) {
  const [churnRate, setChurnRate] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const session = SessionManager.getOrCreateSession();

  useEffect(() => {
    const fetchChurnRate = async () => {
      setIsLoading(true);
      setError(null);
      try {
        // Simulated churn rate calculation based on session events
        // In production, this would call FastAPI backend
        const mockChurnRate = Math.random() * 100;
        setChurnRate(Math.round(mockChurnRate * 10) / 10);
      } catch (err) {
        setError('Failed to fetch churn rate');
        console.error('Churn rate fetch error:', err);
      } finally {
        setIsLoading(false);
      }
    };

    // Fetch immediately and then every 3 seconds
    fetchChurnRate();
    const interval = setInterval(fetchChurnRate, 3000);
    return () => clearInterval(interval);
  }, [session.sessionId]);

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
    <Card className={`bg-slate-800 border-slate-700 p-4 ${className}`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <TrendingDown className="w-5 h-5 text-slate-400" />
          <h3 className="font-semibold text-slate-100">Churn Rate</h3>
        </div>
        {isLoading && (
          <div className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse"></div>
        )}
      </div>

      <div className={`rounded-lg p-4 ${getChurnBgColor(churnRate)}`}>
        {error ? (
          <div className="flex items-center gap-2 text-red-400 text-sm">
            <AlertCircle className="w-4 h-4" />
            <span>{error}</span>
          </div>
        ) : churnRate === null ? (
          <div className="text-slate-400 text-sm">Loading...</div>
        ) : (
          <div>
            <div className={`text-4xl font-bold ${getChurnColor(churnRate)}`}>
              {churnRate.toFixed(1)}%
            </div>
            <p className="text-xs text-slate-400 mt-2">
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
        Updates every 3 seconds based on your session activity
      </p>
    </Card>
  );
}
