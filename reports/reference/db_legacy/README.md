# db_legacy (레거시 DB 참고 — 운영 사용 금지)

05-6-4 §6: 과거 SQLite/Streamlit-직결 DB 유틸 보관. 운영 DB는 `backend/`(FastAPI)+MySQL.
- db_client.py: 과거 Streamlit이 MySQL에 직접 붙던 유틸(현재는 백엔드 /auth/* 경유로 대체).
