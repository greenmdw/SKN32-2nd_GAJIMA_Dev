# E-Commerce Churn Simulator - Project TODO

## Phase 1: 프로젝트 구조 설계 및 기술 스택 확정
- [x] 프로젝트 초기화 (web-db-user scaffold)
- [x] 기술 스택 문서화 (MySQL, FastAPI, React, tRPC)
- [x] 환경변수 설정 계획 (FASTAPI_URL 등)

## Phase 2: Neon DB 스키마 설계 및 이벤트 로깅 API 구현
- [x] Neon PostgreSQL 스키마 설계
  - [x] events 테이블 (event_id, user_id, session_id, event_type, event_time, product_id, category_id, brand, price, quantity, page_url, referrer, device_type, payload_json)
  - [x] products 테이블 (product_id, sku, name, category_id, brand, price)
  - [x] sessions 테이블 (session_id, user_id, device_type, start_time, end_time, event_count)
- [x] Drizzle ORM 스키마 정의
- [x] DB 쿼리 헬퍼 함수 구현 (logEvent, getEventsBySessionId, createOrUpdateSession)
- [x] 이벤트 로깅 API 엔드포인트 구현 (events.logEvent)
- [x] 이벤트 조회 API 엔드포인트 구현 (events.getEventsBySession)

## Phase 3: React 프론트엔드 기본 구조 및 상품 목록/상세 페이지 구현
- [x] 프로젝트 레이아웃 및 라우팅 구조 설계
- [x] 상품 목록 페이지 (ProductList.tsx)
  - [x] 카테고리 필터
  - [x] 브랜드 필터
  - [x] 상품 카드 컴포넌트 (상품명, 가격, 브랜드, 카테고리)
  - [x] view 이벤트 로깅
- [x] 상품 상세 페이지 (ProductDetail.tsx)
  - [x] 상품 상세 정보 표시
  - [x] 장바구니 담기 버튼
  - [x] cart 이벤트 로깅
  - [x] 연관 상품 추천 섹션 (FastAPI 연동 준비)

## Phase 4: 장바구니 기능 및 유저 행동 이벤트 로깅 시스템 구현
- [x] 장바구니 상태 관리 (Context API)
- [x] 장바구니 페이지 (Cart.tsx)
  - [x] 담긴 상품 목록 표시
  - [x] 수량 조절 기능
  - [x] 상품 제거 기능 (remove_from_cart 이벤트)
  - [x] 구매 완료 버튼 (purchase 이벤트)
- [x] 이벤트 로깅 유틸리티 함수 구현
  - [x] logEvent() 함수 (event_id, user_id, session_id, event_type, event_time, product_id, category_id, brand, price, quantity, page_url, referrer, device_type, payload_json)
  - [x] tRPC 서버로 이벤트 전송
- [x] 세션 관리 (user_id, session_id, device_type)

## Phase 5: 실시간 이탈률 대시보드 및 이벤트 로그 뷰어 구현
- [x] 실시간 이탈률 위젯 (ChurnRateWidget.tsx)
  - [x] 모뒠 이탈 확률 계산 (실시간 업데이트)
  - [x] 상단 위젯에 표시
  - [x] 3초 간격 실시간 업데이트
- [x] 이벤트 로그 뷰어 (EventLogViewer.tsx)
  - [x] 현재 세션의 이벤트 목록 시간순 표시
  - [x] 이벤트 상세 정보 표시 (JSON 단초)
  - [x] 단축 단추 기능
- [x] 시뮬레이션 컨트롤 패널 (SimulationControl.tsx)
  - [x] 가상 user_id 설정
  - [x] 가상 session_id 설정
  - [x] 디바이스 타입 선택 (desktop, mobile, tablet)
  - [x] 세션 초기화 기능
- [x] 홈 페이지 (Home.tsx) - 다크 테마 네온 스타일 적용

## Phase 6: FastAPI 외부 서버 연동 및 추천 상품 시스템 구현
- [x] 환경변수 설정 (VITE_FASTAPI_URL)
- [x] FastAPI 클라이언트 유틸리티 (fastApiClient.ts)
  - [x] 이벤트 전송 함수
  - [x] 이탈률 조회 함수
  - [x] 추천 상품 조회 함수
  - [x] 서버 상태 확인 및 세션 분석 함수
- [x] 추천 상품 시스템
  - [x] RecommendedProducts 컴포넌트 구옄
  - [x] FastAPI 기반 추천 데이터 수신
  - [x] 추천 상품 로드 및 에러 처리
  - [x] 추천 상품 클릭 시 내비게이션
- [x] 이탈률 폴링 시스템
  - [x] ChurnRateWidget에서 3초 간격 업데이트 구현
  - [x] 모뒠 데이터 배닝 및 에러 처리

## Phase 7: 다크 테마 네온 사이버펑크 스타일 UI 적용 및 통합 테스트
- [x] 다크 테마 색상 팔레트 정의 (Tailwind 기본)
  - [x] 네온 컬러 (cyan, purple, pink 그래디언트)
  - [x] 배경색 (slate-900, slate-800)
  - [x] 텍스트색 (slate-100, slate-400)
- [x] 네온 사이버펑크 스타일 컴포넌트 적용
  - [x] 글로우 효과 (shadow)
  - [x] 네온 테두리 (border-purple-500, border-cyan-500)
  - [x] 애니메이션 효과 (hover, transition)
- [x] 전체 UI 통합 및 반응형 디자인 검증
- [x] 브라우저 호환성 테스트 (Chrome, Safari, Firefox 드래프트)

## Phase 8: 결과물 전달 및 사용 가이드 제공
- [x] 최종 체크포인트 생성
- [x] README 문서 작성 (설정, 사용법, API 문서)
- [x] 환경변수 설정 가이드 작성 (ENV_SETUP.md)
- [x] FastAPI 서버 연동 가이드 작성 (예시, 스키마)
- [x] 사용자 가이드 제공 (README + ENV_SETUP)

## 추가 구현 항목
- [x] 상품 데이터 샘플 준비 (REES46 화장품 데이터셋 일부 - 20개 상품)
- [x] 에러 처리 및 로깅 (기본 구현)
- [x] 성능 최적화 (이벤트 배치 전송, 캐싱) - 기본 구조 완성
- [x] 보안 (CORS 설정, 입력 검증) - 기본 구조 완성
