import { useEffect, useState } from 'react';
import { pingBackend } from '@/lib/fastApiClient';

/**
 * 백엔드(이탈예측 서버) 연결 상태 배너.
 * "양쪽(프론트+백엔드) 다 연결돼야 진행" 원칙 — 미연결이면 상단에 경고를 띄워
 * 이탈예측/추천이 동작하지 않음을 명확히 한다. 가짜(mock) 데이터로 위장하지 않는다.
 */
export default function BackendStatusBanner() {
  // null=확인중, true=연결, false=미연결
  const [connected, setConnected] = useState<boolean | null>(null);

  useEffect(() => {
    let active = true;
    const check = async () => {
      const ok = await pingBackend();
      if (active) setConnected(ok);
    };
    check();
    const id = setInterval(check, 10000); // 10초마다 라이브 재확인
    return () => {
      active = false;
      clearInterval(id);
    };
  }, []);

  if (connected !== false) return null; // 연결됨/확인중에는 표시하지 않음

  return (
    <div
      role="alert"
      className="fixed top-0 left-0 right-0 z-[9999] bg-amber-600 text-white px-4 py-2 text-center text-sm font-medium shadow-md"
    >
      ⚠ 이탈예측 백엔드 미연결 — 이탈예측·추천 기능이 동작하지 않습니다. 백엔드를 실행/배포한 뒤 새로고침하세요.
    </div>
  );
}
