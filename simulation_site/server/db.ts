import { eq } from "drizzle-orm";
import { drizzle } from "drizzle-orm/mysql2";
import { events, sessions } from "../drizzle/schema";

let _db: ReturnType<typeof drizzle> | null = null;

// DATABASE_URL 미설정(로컬) 시 인메모리 폴백. logEvent/getEventsBySessionId 가 같은 프로세스에서
// 이벤트를 공유 → DB 없이도 churn 위젯이 세션 이벤트를 받아 실추론이 가능.
const _memEvents = new Map<string, Record<string, unknown>[]>();

// Lazily create the drizzle instance so local tooling can run without a DB.
export async function getDb() {
  if (!_db && process.env.DATABASE_URL) {
    try {
      _db = drizzle(process.env.DATABASE_URL);
    } catch (error) {
      console.warn("[Database] Failed to connect:", error);
      _db = null;
    }
  }
  return _db;
}

export async function logEvent(eventData: {
  eventId: string;
  userId: string;
  sessionId: string;
  eventType: string;
  eventTime: Date;
  productId: string;
  categoryId: string;
  brand: string;
  price: number;
  quantity: number;
  pageUrl: string;
  referrer?: string;
  deviceType: string;
  payloadJson?: Record<string, unknown>;
}): Promise<void> {
  const db = await getDb();
  if (!db) {
    // DB 미설정 → 인메모리에 보관(세션별, 최근 300건). 같은 프로세스의 getEventsBySessionId 가 읽음.
    const arr = _memEvents.get(eventData.sessionId) ?? [];
    arr.push({ ...eventData });
    if (arr.length > 300) arr.splice(0, arr.length - 300);
    _memEvents.set(eventData.sessionId, arr);
    return;
  }

  try {
    await db.insert(events).values({
      eventId: eventData.eventId,
      userId: eventData.userId,
      sessionId: eventData.sessionId,
      eventType: eventData.eventType,
      eventTime: eventData.eventTime,
      productId: eventData.productId,
      categoryId: eventData.categoryId,
      brand: eventData.brand,
      price: eventData.price.toString(),
      quantity: eventData.quantity,
      pageUrl: eventData.pageUrl,
      referrer: eventData.referrer || null,
      deviceType: eventData.deviceType,
      payloadJson: eventData.payloadJson || null,
    });
  } catch (error) {
    console.error("[Database] Failed to log event:", error);
    throw error;
  }
}

export async function getEventsBySessionId(sessionId: string) {
  const db = await getDb();
  if (!db) {
    // DB 미설정 → 인메모리 폴백에서 세션 이벤트 반환.
    return _memEvents.get(sessionId) ?? [];
  }

  try {
    const result = await db.select().from(events).where(eq(events.sessionId, sessionId));
    return result;
  } catch (error) {
    console.error("[Database] Failed to get events:", error);
    throw error;
  }
}

export async function createOrUpdateSession(sessionData: {
  sessionId: string;
  userId: string;
  deviceType: string;
}): Promise<void> {
  const db = await getDb();
  if (!db) {
    console.warn("[Database] Cannot create session: database not available");
    return;
  }

  try {
    const existing = await db.select().from(sessions).where(eq(sessions.sessionId, sessionData.sessionId)).limit(1);
    
    if (existing.length > 0) {
      // Session already exists, update event count
      await db.update(sessions)
        .set({ eventCount: existing[0].eventCount + 1 })
        .where(eq(sessions.sessionId, sessionData.sessionId));
    } else {
      // Create new session
      await db.insert(sessions).values({
        sessionId: sessionData.sessionId,
        userId: sessionData.userId,
        deviceType: sessionData.deviceType,
        eventCount: 0,
      });
    }
  } catch (error) {
    console.error("[Database] Failed to create/update session:", error);
    throw error;
  }
}

// TODO: add feature queries here as your schema grows.
