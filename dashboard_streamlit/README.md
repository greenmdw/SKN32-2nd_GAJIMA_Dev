# dashboard_streamlit (Anchor 통합 대시보드)

19-4 규격. **표시 계층 전용** — 데이터는 `services/api_client` → FastAPI 백엔드(REST). MySQL/Neon/모델 artifact 직접 접속 금지(진단 차트의 eval 파일 읽기만 개발용 허용).

## 실행
```bash
cd dashboard_streamlit
cp .env.example .env            # DASHBOARD_API_BASE_URL / USE_MOCK
streamlit run app.py
```
- 백엔드 없이 화면만 볼 때: `.env`에서 `DASHBOARD_USE_MOCK=true` → `mocks/` JSON 사용.
- 운영: `DASHBOARD_USE_MOCK=false` → 백엔드 REST.

## 구조
- `app.py` 진입(랜딩) · `pages/01_face_login.py` · `pages/02_dashboard.py`(단일 통합: 개요/고객조회/실시간바운스/추천 + 관리자 진단·로그)
- `services/` api_client·auth·dashboard·prediction·recommendation·chart·face_auth
- `components/` layout·kpi_cards·charts·risk_table·error_state
- `mocks/` 백엔드 미완성 시 개발용 JSON(실 eval 데이터 기반)

얼굴 로그인: insightface 임베딩은 **클라이언트에서 추출**해 백엔드 `/auth/face/*`로 전송 → 백엔드가 `face_user`/`face_login_log` 저장·매칭.
