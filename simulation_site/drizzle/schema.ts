import { int, mysqlTable, text, timestamp, varchar, json, decimal } from "drizzle-orm/mysql-core";

// 인증/사용자 테이블은 제거(로그인 없는 익명 시뮬). 시뮬 로그용 products/events/sessions만 유지.
// (05-6-4 §9: 시뮬 이벤트 로그 DB)

/**
 * Products table for storing cosmetics product information
 */
export const products = mysqlTable("products", {
  id: int("id").autoincrement().primaryKey(),
  productId: varchar("product_id", { length: 64 }).notNull().unique(),
  sku: varchar("sku", { length: 64 }).notNull(),
  name: text("name").notNull(),
  categoryId: varchar("category_id", { length: 64 }).notNull(),
  brand: varchar("brand", { length: 128 }).notNull(),
  price: decimal("price", { precision: 10, scale: 2 }).notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});

export type Product = typeof products.$inferSelect;
export type InsertProduct = typeof products.$inferInsert;

/**
 * Events table for storing user behavior events from simulation site
 */
export const events = mysqlTable("events", {
  id: int("id").autoincrement().primaryKey(),
  eventId: varchar("event_id", { length: 64 }).notNull().unique(),
  userId: varchar("user_id", { length: 64 }).notNull(),
  sessionId: varchar("session_id", { length: 64 }).notNull(),
  eventType: varchar("event_type", { length: 32 }).notNull(), // view, cart, remove_from_cart, purchase
  eventTime: timestamp("event_time").notNull(),
  productId: varchar("product_id", { length: 64 }).notNull(),
  categoryId: varchar("category_id", { length: 64 }).notNull(),
  brand: varchar("brand", { length: 128 }).notNull(),
  price: decimal("price", { precision: 10, scale: 2 }).notNull(),
  quantity: int("quantity").default(1).notNull(),
  pageUrl: text("page_url").notNull(),
  referrer: text("referrer"),
  deviceType: varchar("device_type", { length: 32 }).notNull(), // desktop, mobile, tablet
  payloadJson: json("payload_json"),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
});

export type Event = typeof events.$inferSelect;
export type InsertEvent = typeof events.$inferInsert;

/**
 * Sessions table for tracking user sessions
 */
export const sessions = mysqlTable("sessions", {
  id: int("id").autoincrement().primaryKey(),
  sessionId: varchar("session_id", { length: 64 }).notNull().unique(),
  userId: varchar("user_id", { length: 64 }).notNull(),
  deviceType: varchar("device_type", { length: 32 }).notNull(),
  startTime: timestamp("start_time").defaultNow().notNull(),
  endTime: timestamp("end_time"),
  eventCount: int("event_count").default(0).notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});

export type Session = typeof sessions.$inferSelect;
export type InsertSession = typeof sessions.$inferInsert;