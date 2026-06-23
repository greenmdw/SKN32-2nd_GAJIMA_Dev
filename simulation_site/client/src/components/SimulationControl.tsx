import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { SessionManager } from '@/lib/eventLogger';
import { RotateCcw, Settings } from 'lucide-react';
import { toast } from 'sonner';

export default function SimulationControl() {
  const session = SessionManager.getOrCreateSession();
  const [customUserId, setCustomUserId] = useState(session.userId);
  const [customSessionId, setCustomSessionId] = useState(session.sessionId);
  const [deviceType, setDeviceType] = useState<'desktop' | 'mobile' | 'tablet'>(session.deviceType);
  const [isOpen, setIsOpen] = useState(false);

  const handleSetUserId = () => {
    if (customUserId.trim()) {
      SessionManager.setCustomUserId(customUserId);
      toast.success('User ID updated');
    }
  };

  const handleSetSessionId = () => {
    if (customSessionId.trim()) {
      SessionManager.setCustomSessionId(customSessionId);
      toast.success('Session ID updated');
    }
  };

  const handleSetDeviceType = (type: 'desktop' | 'mobile' | 'tablet') => {
    SessionManager.setDeviceType(type);
    setDeviceType(type);
    toast.success(`Device type changed to ${type}`);
  };

  const handleResetSession = () => {
    if (confirm('Are you sure you want to reset the session? This will create a new session ID and user ID.')) {
      SessionManager.resetSession();
      const newSession = SessionManager.getOrCreateSession();
      setCustomUserId(newSession.userId);
      setCustomSessionId(newSession.sessionId);
      setDeviceType(newSession.deviceType);
      toast.success('Session reset successfully');
    }
  };

  return (
    <>
      {/* Toggle Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-6 right-6 z-50 w-12 h-12 bg-gradient-to-r from-cyan-500 to-purple-500 hover:from-cyan-600 hover:to-purple-600 rounded-full flex items-center justify-center text-white shadow-lg hover:shadow-xl transition-all"
        title="Simulation Control"
      >
        <Settings className="w-6 h-6" />
      </button>

      {/* Control Panel */}
      {isOpen && (
        <Card className="fixed bottom-20 right-6 z-50 w-80 bg-slate-800 border-slate-700 p-6 shadow-2xl">
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-bold text-slate-100 mb-4 flex items-center gap-2">
                <Settings className="w-5 h-5 text-purple-400" />
                Simulation Control
              </h3>
            </div>

            {/* User ID */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                User ID
              </label>
              <div className="flex gap-2">
                <Input
                  value={customUserId}
                  onChange={(e) => setCustomUserId(e.target.value)}
                  className="bg-slate-700 border-slate-600 text-slate-100 text-sm"
                  placeholder="Enter user ID"
                />
                <Button
                  size="sm"
                  className="bg-cyan-500 hover:bg-cyan-600 text-white"
                  onClick={handleSetUserId}
                >
                  Set
                </Button>
              </div>
              <p className="text-xs text-slate-500 mt-1">Current: {session.userId}</p>
            </div>

            {/* Session ID */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Session ID
              </label>
              <div className="flex gap-2">
                <Input
                  value={customSessionId}
                  onChange={(e) => setCustomSessionId(e.target.value)}
                  className="bg-slate-700 border-slate-600 text-slate-100 text-sm"
                  placeholder="Enter session ID"
                />
                <Button
                  size="sm"
                  className="bg-purple-500 hover:bg-purple-600 text-white"
                  onClick={handleSetSessionId}
                >
                  Set
                </Button>
              </div>
              <p className="text-xs text-slate-500 mt-1">Current: {session.sessionId}</p>
            </div>

            {/* Device Type */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Device Type
              </label>
              <Select value={deviceType} onValueChange={(val) => handleSetDeviceType(val as any)}>
                <SelectTrigger className="bg-slate-700 border-slate-600 text-slate-100 text-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-slate-700 border-slate-600">
                  <SelectItem value="desktop">Desktop</SelectItem>
                  <SelectItem value="mobile">Mobile</SelectItem>
                  <SelectItem value="tablet">Tablet</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Reset Button */}
            <Button
              className="w-full bg-red-900/50 hover:bg-red-900 text-red-400 border border-red-700"
              variant="outline"
              onClick={handleResetSession}
            >
              <RotateCcw className="w-4 h-4 mr-2" />
              Reset Session
            </Button>

            {/* Info */}
            <div className="bg-slate-700/50 rounded p-3 text-xs text-slate-400">
              <p className="font-semibold mb-1">Session Info:</p>
              <p>All user interactions are logged with these settings.</p>
            </div>
          </div>
        </Card>
      )}

      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setIsOpen(false)}
        />
      )}
    </>
  );
}
