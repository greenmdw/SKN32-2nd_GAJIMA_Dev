# simulation_site (미구축 — 골격)

05-6-4 §6 · 19-2 §1: Vercel/정적 이커머스 시뮬레이션. 유저 행동 → `/events` → Neon `sim_event_log` 적재.
백엔드가 Neon에서 pull → 실시간 점수 → 리텐션/추천을 다시 시뮬 사이트로 push(루프).

- `app/` 또는 `pages/`: 고객 행동 시뮬 UI
- `api/`: events/recommendation push thin API
- `neon/schema_neon.sql`: sim_event_log DDL
