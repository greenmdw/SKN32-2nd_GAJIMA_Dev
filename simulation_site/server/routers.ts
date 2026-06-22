import { systemRouter } from "./_core/systemRouter";
import { publicProcedure, router } from "./_core/trpc";
import { z } from "zod";
import { logEvent, getEventsBySessionId, createOrUpdateSession } from "./db";
import { nanoid } from "nanoid";

export const appRouter = router({
  // 모든 api는 '/api/'로 시작(게이트웨이 라우팅). 인증 라우터는 제거(로그인 없는 익명 시뮬).
  system: systemRouter,

  // Event logging API for churn simulation
  events: router({
    logEvent: publicProcedure
      .input(z.object({
        userId: z.string(),
        sessionId: z.string(),
        eventType: z.enum(["view", "cart", "remove_from_cart", "purchase"]),
        eventTime: z.date(),
        productId: z.string(),
        categoryId: z.string(),
        brand: z.string(),
        price: z.number(),
        quantity: z.number().optional().default(1),
        pageUrl: z.string(),
        referrer: z.string().optional(),
        deviceType: z.enum(["desktop", "mobile", "tablet"]),
        payloadJson: z.record(z.string(), z.unknown()).optional(),
      }))
      .mutation(async ({ input }) => {
        const eventId = `evt_${Date.now()}_${nanoid(8)}`;
        
        // Create or update session
        await createOrUpdateSession({
          sessionId: input.sessionId,
          userId: input.userId,
          deviceType: input.deviceType,
        });
        
        // Log event
        await logEvent({
          eventId,
          userId: input.userId,
          sessionId: input.sessionId,
          eventType: input.eventType,
          eventTime: input.eventTime,
          productId: input.productId,
          categoryId: input.categoryId,
          brand: input.brand,
          price: input.price,
          quantity: input.quantity,
          pageUrl: input.pageUrl,
          referrer: input.referrer,
          deviceType: input.deviceType,
          payloadJson: input.payloadJson,
        });
        
        return { success: true, eventId };
      }),
    
    getEventsBySession: publicProcedure
      .input(z.object({
        sessionId: z.string(),
      }))
      .query(async ({ input }) => {
        const events = await getEventsBySessionId(input.sessionId);
        return events;
      }),
  }),

  // TODO: add feature routers here, e.g.
  // todo: router({
  //   list: protectedProcedure.query(({ ctx }) =>
  //     db.getUserTodos(ctx.user.id)
  //   ),
  // }),
});

export type AppRouter = typeof appRouter;

// TODO: Add type exports for events router if needed
