# E-Commerce Churn Simulator

실시간 쇼핑몰 유저 활동 시뮬레이션 및 이탈 예측 시스템

## 프로젝트 개요

REES46 화장품 데이터셋을 기반으로 구축된 실시간 이탈 예측 시뮬레이션 플랫폼입니다. 사용자가 상품을 탐색하고 장바구니에 담으며 구매하는 과정에서 발생하는 모든 행동을 실시간으로 로깅하고, 머신러닝 모델을 통해 이탈 확률을 예측합니다.

## 기술 스택

### 프론트엔드
- **React 19** - UI 라이브러리
- **Tailwind CSS 4** - 스타일링
- **TypeScript** - 타입 안전성
- **Wouter** - 라우팅
- **Sonner** - 토스트 알림
- **Shadcn/ui** - UI 컴포넌트

### 백엔드
- **Express 4** - 웹 서버
- **tRPC 11** - RPC 프레임워크
- **Drizzle ORM** - 데이터베이스 ORM
- **MySQL** - 데이터베이스

### 외부 서비스
- **FastAPI** - 이탈 예측 및 추천 시스템 (선택사항)
- **Neon** - PostgreSQL 호스팅 (선택사항)

## 주요 기능

### 1. 상품 탐색
- 카테고리 및 브랜드별 필터링
- 검색 기능
- 상품 상세 정보 조회

### 2. 장바구니 관리
- 상품 추가/제거
- 수량 조절
- 주문 요약

### 3. 실시간 이탈률 표시
- 세션별 이탈 확률 실시간 계산
- 진행 바 및 위험도 표시
- 3초 간격 자동 업데이트

### 4. 이벤트 로깅
- 모든 사용자 행동 기록
- 이벤트 타입: view, cart, remove_from_cart, purchase
- 세션별 이벤트 로그 조회

### 5. 시뮬레이션 컨트롤
- 가상 사용자 ID 설정
- 가상 세션 ID 설정
- 디바이스 타입 선택 (Desktop/Mobile/Tablet)
- 세션 초기화

### 6. 추천 시스템
- 현재 상품 기반 추천
- 카테고리 및 브랜드 기반 추천
- FastAPI 연동 (선택사항)

## 설치 및 실행

### 전제 조건
- Node.js 22.13.0 이상
- pnpm 10.4.1 이상

### 설치
```bash
# 프로젝트 클론
git clone <repository-url>
cd ecom-churn-simulation

# 의존성 설치
pnpm install
```

### 개발 서버 실행
```bash
# 개발 서버 시작
pnpm dev

# 브라우저에서 http://localhost:3000 접속
```

### 빌드
```bash
# 프로덕션 빌드
pnpm build

# 빌드 결과 확인
pnpm start
```

## 환경변수 설정

### 필수 환경변수
- `DATABASE_URL`: MySQL 연결 문자열
- `JWT_SECRET`: 세션 쿠키 서명 비밀키

### 선택 환경변수
- `VITE_FASTAPI_URL`: FastAPI 서버 URL (기본값: http://localhost:8000)

자세한 설정 방법은 [ENV_SETUP.md](./ENV_SETUP.md)를 참고하세요.

## 프로젝트 구조

```
ecom-churn-simulation/
├── client/                 # React 프론트엔드
│   ├── src/
│   │   ├── pages/         # 페이지 컴포넌트
│   │   ├── components/    # 재사용 가능한 컴포넌트
│   │   ├── lib/           # 유틸리티 함수
│   │   ├── contexts/      # React Context
│   │   └── App.tsx        # 메인 앱
│   └── index.html
├── server/                 # Express 백엔드
│   ├── routers.ts         # tRPC 라우터
│   ├── db.ts              # 데이터베이스 쿼리
│   └── _core/             # 핵심 설정
├── drizzle/               # 데이터베이스 스키마
│   └── schema.ts
├── shared/                # 공유 타입 및 상수
└── package.json
```

## 데이터베이스 스키마

### events 테이블
사용자 행동 이벤트 저장

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INT | 기본 키 |
| event_id | VARCHAR | 이벤트 고유 ID |
| user_id | VARCHAR | 사용자 ID |
| session_id | VARCHAR | 세션 ID |
| event_type | VARCHAR | 이벤트 타입 (view, cart, remove_from_cart, purchase) |
| event_time | TIMESTAMP | 이벤트 발생 시간 |
| product_id | VARCHAR | 상품 ID |
| category_id | VARCHAR | 카테고리 ID |
| brand | VARCHAR | 브랜드명 |
| price | INT | 상품 가격 |
| quantity | INT | 수량 |
| page_url | VARCHAR | 페이지 URL |
| referrer | VARCHAR | 이전 페이지 URL |
| device_type | VARCHAR | 디바이스 타입 |
| payload_json | JSON | 추가 데이터 |
| created_at | TIMESTAMP | 생성 시간 |

### sessions 테이블
세션 정보 저장

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INT | 기본 키 |
| session_id | VARCHAR | 세션 ID |
| user_id | VARCHAR | 사용자 ID |
| device_type | VARCHAR | 디바이스 타입 |
| start_time | TIMESTAMP | 세션 시작 시간 |
| end_time | TIMESTAMP | 세션 종료 시간 |
| event_count | INT | 이벤트 개수 |
| created_at | TIMESTAMP | 생성 시간 |

## API 엔드포인트

### tRPC 엔드포인트

#### events.logEvent
사용자 이벤트 로깅

```typescript
trpc.events.logEvent.useMutation({
  eventType: 'view',
  productId: 'sku_10031',
  categoryId: 'cat_18',
  brand: 'adidas',
  price: 59000,
  quantity: 1,
  pageUrl: '/products/sku_10031',
  referrer: '/category/cat_18',
})
```

#### events.getEventsBySession
세션별 이벤트 조회

```typescript
trpc.events.getEventsBySession.useQuery({
  sessionId: 'sess_abc123',
})
```

## 사용 예시

### 1. 상품 탐색
1. 홈페이지에서 "Start Simulation" 클릭
2. 상품 목록 페이지에서 상품 탐색
3. 카테고리/브랜드 필터 적용
4. 검색 기능 사용

### 2. 장바구니 추가
1. 상품 상세 페이지에서 수량 선택
2. "Add to Cart" 버튼 클릭
3. 장바구니 페이지에서 확인

### 3. 이탈률 모니터링
1. 상품 목록 페이지 상단의 "Churn Rate" 위젯 확인
2. 실시간 이탈 확률 표시
3. 진행 바로 위험도 시각화

### 4. 이벤트 로그 확인
1. 상품 목록 페이지의 "Events" 버튼 클릭
2. 우측 패널에서 이벤트 로그 확인
3. 이벤트 상세 정보 조회

### 5. 시뮬레이션 컨트롤
1. 우측 하단 설정 아이콘 클릭
2. User ID/Session ID 커스텀 설정
3. 디바이스 타입 변경
4. 세션 초기화

## FastAPI 연동

FastAPI 백엔드 서버를 연동하면 다음 기능이 활성화됩니다:

- **실시간 이탈 예측**: 머신러닝 모델 기반 정확한 이탈률 계산
- **추천 상품**: 사용자 행동 기반 개인화된 상품 추천
- **분석 대시보드**: 세션별 상세 분석 데이터

### FastAPI 서버 설정

```bash
# FastAPI 서버 실행
python -m uvicorn main:app --reload --port 8000

# 환경변수 설정
export VITE_FASTAPI_URL=http://localhost:8000
```

자세한 설정은 [ENV_SETUP.md](./ENV_SETUP.md)를 참고하세요.

## 스타일 및 테마

### 다크 테마 네온 사이버펑크 스타일
- **배경색**: Slate 900/800
- **네온 컬러**: Cyan, Purple, Pink 그래디언트
- **글로우 효과**: Box-shadow 활용
- **호버 효과**: 부드러운 전환 및 색상 변화

### 반응형 디자인
- 모바일 (< 768px)
- 태블릿 (768px - 1024px)
- 데스크톱 (> 1024px)

## 성능 최적화

- **이벤트 배치 전송**: 여러 이벤트를 한 번에 전송
- **캐싱**: 상품 데이터 클라이언트 캐싱
- **지연 로딩**: 이미지 및 컴포넌트 지연 로딩
- **코드 스플리팅**: 페이지별 번들 분할

## 보안

- **CORS 설정**: 신뢰할 수 있는 도메인만 허용
- **입력 검증**: 모든 사용자 입력 검증
- **세션 관리**: 안전한 세션 쿠키 관리
- **환경변수**: 민감한 정보는 환경변수로 관리

## 문제 해결

### 개발 서버가 시작되지 않음
```bash
# 포트 충돌 확인
lsof -i :3000

# 캐시 삭제
rm -rf node_modules/.vite

# 재설치
pnpm install
pnpm dev
```

### 데이터베이스 연결 오류
```bash
# DATABASE_URL 확인
echo $DATABASE_URL

# 데이터베이스 마이그레이션 실행
pnpm drizzle-kit generate
pnpm drizzle-kit migrate
```

### FastAPI 연동 실패
1. FastAPI 서버 실행 확인
2. `VITE_FASTAPI_URL` 환경변수 확인
3. CORS 설정 확인
4. 브라우저 콘솔 에러 메시지 확인

## 기여

이 프로젝트에 기여하고 싶으신 분은 다음 절차를 따라주세요:

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](./LICENSE) 파일을 참고하세요.

## 지원

문제가 발생하거나 질문이 있으신 경우:

1. [GitHub Issues](https://github.com/your-repo/issues)에서 이슈 생성
2. [ENV_SETUP.md](./ENV_SETUP.md) 문제 해결 섹션 참고
3. 프로젝트 문서 검토

## 참고 자료

- [React 공식 문서](https://react.dev)
- [Tailwind CSS 문서](https://tailwindcss.com)
- [tRPC 문서](https://trpc.io)
- [Drizzle ORM 문서](https://orm.drizzle.team)
- [FastAPI 문서](https://fastapi.tiangolo.com)

## 변경 이력

### v1.0.0 (2026-06-21)
- 초기 릴리스
- 상품 탐색 및 장바구니 기능
- 실시간 이탈률 표시
- 이벤트 로깅 시스템
- 시뮬레이션 컨트롤 패널
- FastAPI 연동 준비

---

**마지막 업데이트**: 2026-06-21
