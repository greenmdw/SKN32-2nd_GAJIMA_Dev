import { nanoid } from 'nanoid';
import {
  sendEventToFastAPI,
  resolveSimMode,
  currentSimMode,
} from './fastApiClient';

/**
 * Event logger utility for tracking user behavior in the simulation
 */

export interface EventPayload {
  userId: string;
  sessionId: string;
  eventType: 'view' | 'cart' | 'remove_from_cart' | 'purchase';
  eventTime: Date;
  productId: string;
  categoryId: string;
  brand: string;
  price: number;
  quantity?: number;
  pageUrl: string;
  referrer?: string;
  deviceType: 'desktop' | 'mobile' | 'tablet';
  payloadJson?: Record<string, unknown>;
}

/**
 * Session management utility
 */
export class SessionManager {
  private static readonly SESSION_STORAGE_KEY = 'churn_simulator_session';
  private static readonly USER_STORAGE_KEY = 'churn_simulator_user';

  static getOrCreateSession(): {
    sessionId: string;
    userId: string;
    deviceType: 'desktop' | 'mobile' | 'tablet';
    createdAt: string;
  } {
    const stored = localStorage.getItem(this.SESSION_STORAGE_KEY);
    
    if (stored) {
      try {
        return JSON.parse(stored);
      } catch {
        // Invalid stored session, create new one
      }
    }

    // Create new session
    const session = {
      sessionId: `sess_${Date.now()}_${nanoid(8)}`,
      userId: this.getOrCreateUserId(),
      deviceType: this.detectDeviceType(),
      createdAt: new Date().toISOString(),
    };

    localStorage.setItem(this.SESSION_STORAGE_KEY, JSON.stringify(session));
    return session;
  }

  static getOrCreateUserId(): string {
    const stored = localStorage.getItem(this.USER_STORAGE_KEY);
    
    if (stored) {
      return stored;
    }

    const userId = `user_${Date.now()}_${nanoid(8)}`;
    localStorage.setItem(this.USER_STORAGE_KEY, userId);
    return userId;
  }

  static resetSession(): void {
    localStorage.removeItem(this.SESSION_STORAGE_KEY);
  }

  static setCustomUserId(userId: string): void {
    localStorage.setItem(this.USER_STORAGE_KEY, userId);
  }

  static setCustomSessionId(sessionId: string): void {
    const current = this.getOrCreateSession();
    const updated = {
      ...current,
      sessionId,
    };
    localStorage.setItem(this.SESSION_STORAGE_KEY, JSON.stringify(updated));
  }

  static setDeviceType(deviceType: 'desktop' | 'mobile' | 'tablet'): void {
    const current = this.getOrCreateSession();
    const updated = {
      ...current,
      deviceType,
    };
    localStorage.setItem(this.SESSION_STORAGE_KEY, JSON.stringify(updated));
  }

  private static detectDeviceType(): 'desktop' | 'mobile' | 'tablet' {
    if (typeof window === 'undefined') return 'desktop';

    const ua = navigator.userAgent.toLowerCase();
    
    if (/ipad|android(?!.*mobi)|tablet/.test(ua)) {
      return 'tablet';
    }
    
    if (/mobile|android|iphone|ipod|blackberry|iemobile|opera mini/.test(ua)) {
      return 'mobile';
    }
    
    return 'desktop';
  }
}

/**
 * 이벤트 적재 — 클라이언트 측 세션 버퍼(단일 진실원천은 백엔드).
 *
 * 설계 정합(19-2/19-3/05-6-4): 시뮬 사이트는 자체 권위 저장소를 두지 않는다.
 * - direct(A-최소, Neon 미연결): 이벤트를 클라 버퍼에만 쌓고, churn 조회 시 버퍼 전체를
 *   무상태로 백엔드 /api/churn/predict 에 보낸다(이중 누적·tRPC eventTime 버그 없음).
 * - neon(B, Neon 연결): 위 버퍼에 더해 각 이벤트를 백엔드 /api/events 로 보내
 *   Neon sim_event_log 에 영속(백엔드 pull 의 입력).
 *
 * 과거 tRPC(/api/trpc/events.logEvent + superjson z.date()) 경로는 제거.
 * eventTime(Date)을 JSON.stringify 하면 문자열이 되어 서버 z.date() 가 400 → 적재 실패하던 버그 해소.
 */
const _eventBuffer: Record<string, EventPayload[]> = {};
const _bufKey = (sessionId: string) => `churn_sim_events_${sessionId}`;

// 모드 1회 사전 해석(fire-and-forget). 미해석 동안은 direct 로 동작(네트워크 0).
void resolveSimMode();

export class EventLogger {
  private static _hydrate(sessionId: string): EventPayload[] {
    if (_eventBuffer[sessionId]) return _eventBuffer[sessionId];
    let arr: EventPayload[] = [];
    try {
      const raw = localStorage.getItem(_bufKey(sessionId));
      if (raw) arr = JSON.parse(raw) as EventPayload[];
    } catch { /* 무시 */ }
    _eventBuffer[sessionId] = arr;
    return arr;
  }

  private static _persist(sessionId: string): void {
    try {
      localStorage.setItem(_bufKey(sessionId), JSON.stringify(_eventBuffer[sessionId].slice(-300)));
    } catch { /* 용량 초과 등 무시 */ }
  }

  static async logEvent(payload: EventPayload): Promise<{ success: boolean; eventId?: string }> {
    const eventId = `evt_${Date.now()}_${nanoid(8)}`;
    const buf = this._hydrate(payload.sessionId);
    buf.push(payload);
    if (buf.length > 300) buf.splice(0, buf.length - 300);   // 세션당 상한
    this._persist(payload.sessionId);

    // B 모드일 때만 백엔드로 영속(Neon sim_event_log). direct 는 네트워크 없음.
    if (currentSimMode() === 'neon') {
      void sendEventToFastAPI({
        event_id: eventId,
        user_id: payload.userId,
        session_id: payload.sessionId,
        event_type: payload.eventType,
        event_time: (payload.eventTime instanceof Date
          ? payload.eventTime.toISOString()
          : String(payload.eventTime)),
        product_id: payload.productId,
        category_id: payload.categoryId,
        brand: payload.brand,
        price: payload.price,
        quantity: payload.quantity ?? 1,
        page_url: payload.pageUrl,
        referrer: payload.referrer,
        device_type: payload.deviceType,
        payload_json: payload.payloadJson,
      });
    }
    return { success: true, eventId };
  }

  static async getSessionEvents(sessionId: string): Promise<unknown[]> {
    return this._hydrate(sessionId);
  }

  static clearSession(sessionId: string): void {
    delete _eventBuffer[sessionId];
    try { localStorage.removeItem(_bufKey(sessionId)); } catch { /* 무시 */ }
  }
}

/**
 * Helper function to log a view event
 */
export async function logViewEvent(
  productId: string,
  categoryId: string,
  brand: string,
  price: number,
  pageUrl: string,
  referrer?: string
): Promise<void> {
  const session = SessionManager.getOrCreateSession();
  
  await EventLogger.logEvent({
    userId: session.userId,
    sessionId: session.sessionId,
    eventType: 'view',
    eventTime: new Date(),
    productId,
    categoryId,
    brand,
    price,
    quantity: 1,
    pageUrl,
    referrer,
    deviceType: session.deviceType,
    payloadJson: { source: 'simulation_site' },
  });
}

/**
 * Helper function to log a cart event
 */
export async function logCartEvent(
  productId: string,
  categoryId: string,
  brand: string,
  price: number,
  quantity: number,
  pageUrl: string,
  referrer?: string
): Promise<void> {
  const session = SessionManager.getOrCreateSession();
  
  await EventLogger.logEvent({
    userId: session.userId,
    sessionId: session.sessionId,
    eventType: 'cart',
    eventTime: new Date(),
    productId,
    categoryId,
    brand,
    price,
    quantity,
    pageUrl,
    referrer,
    deviceType: session.deviceType,
    payloadJson: { source: 'simulation_site' },
  });
}

/**
 * Helper function to log a remove from cart event
 */
export async function logRemoveFromCartEvent(
  productId: string,
  categoryId: string,
  brand: string,
  price: number,
  quantity: number,
  pageUrl: string,
  referrer?: string
): Promise<void> {
  const session = SessionManager.getOrCreateSession();
  
  await EventLogger.logEvent({
    userId: session.userId,
    sessionId: session.sessionId,
    eventType: 'remove_from_cart',
    eventTime: new Date(),
    productId,
    categoryId,
    brand,
    price,
    quantity,
    pageUrl,
    referrer,
    deviceType: session.deviceType,
    payloadJson: { source: 'simulation_site' },
  });
}

/**
 * Helper function to log a purchase event
 */
export async function logPurchaseEvent(
  items: Array<{
    productId: string;
    categoryId: string;
    brand: string;
    price: number;
    quantity: number;
  }>,
  pageUrl: string,
  referrer?: string
): Promise<void> {
  const session = SessionManager.getOrCreateSession();
  
  // Log purchase event for each item
  for (const item of items) {
    await EventLogger.logEvent({
      userId: session.userId,
      sessionId: session.sessionId,
      eventType: 'purchase',
      eventTime: new Date(),
      productId: item.productId,
      categoryId: item.categoryId,
      brand: item.brand,
      price: item.price,
      quantity: item.quantity,
      pageUrl,
      referrer,
      deviceType: session.deviceType,
      payloadJson: { source: 'simulation_site' },
    });
  }
}
