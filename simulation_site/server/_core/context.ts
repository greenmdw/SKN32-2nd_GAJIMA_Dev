import type { CreateExpressContextOptions } from "@trpc/server/adapters/express";

/** 로컬 사용자 타입(마누스 OAuth 제거). 본 시뮬은 로그인 없이 동작하므로 user는 항상 null. */
export type AppUser = {
  id: number;
  name?: string | null;
  email?: string | null;
  role: "user" | "admin";
};

export type TrpcContext = {
  req: CreateExpressContextOptions["req"];
  res: CreateExpressContextOptions["res"];
  user: AppUser | null;
};

export async function createContext(
  opts: CreateExpressContextOptions
): Promise<TrpcContext> {
  // 인증 없음 — 이커머스 시뮬은 익명 세션으로 동작(이벤트는 sessionId/userId로 추적).
  return {
    req: opts.req,
    res: opts.res,
    user: null,
  };
}
