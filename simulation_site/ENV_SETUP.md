# 환경변수 설정 가이드

이 문서는 E-Commerce Churn Simulator 프로젝트의 환경변수 설정 방법을 설명합니다.

## 필수 환경변수

### 1. FastAPI 서버 URL (선택사항)

**변수명**: `VITE_FASTAPI_URL`

**설명**: 외부 FastAPI 백엔드 서버의 URL입니다. 이탈률 예측 및 추천 상품 조회에 사용됩니다.

**기본값**: `http://localhost:8000`

**예시**:
```
VITE_FASTAPI_URL=http://your-fastapi-server.com:8000
VITE_FASTAPI_URL=https://api.churn-prediction.example.com
```

**설정 방법**:

#### 개발 환경 (.env.local)
```bash
# 프로젝트 루트에 .env.local 파일 생성
echo "VITE_FASTAPI_URL=http://localhost:8000" > .env.local
```

#### 프로덕션 환경 (Manus 관리 UI)
1. Management UI → Settings → Secrets
2. `VITE_FASTAPI_URL` 추가
3. FastAPI 서버 URL 입력
4. 저장

## FastAPI 서버 연동

### 지원하는 엔드포인트

#### 1. 이탈률 예측
```
POST /api/churn/predict
Content-Type: application/json

{
  "session_id": "sess_abc123",
  "user_id": "user_1024",
  "events": [
    {
      "event_type": "view",
      "product_id": "sku_10031",
      "category_id": "cat_18",
      "brand": "adidas",
      "price": 59000,
      "quantity": 1,
      "timestamp": "2026-06-21T13:42:10+09:00"
    }
  ]
}

응답:
{
  "session_id": "sess_abc123",
  "churn_probability": 35.5,
  "risk_level": "medium",
  "timestamp": "2026-06-21T13:42:15+09:00"
}
```

#### 2. 추천 상품 조회
```
POST /api/recommendations
Content-Type: application/json

{
  "session_id": "sess_abc123",
  "user_id": "user_1024",
  "current_product_id": "sku_10031",
  "category_id": "cat_18",
  "brand": "adidas"
}

응답:
{
  "session_id": "sess_abc123",
  "user_id": "user_1024",
  "current_product_id": "sku_10031",
  "recommendations": [
    {
      "product_id": "sku_10032",
      "name": "Adidas Serum",
      "category_id": "cat_18",
      "brand": "adidas",
      "price": 52000,
      "score": 0.92,
      "reason": "Same brand, similar category"
    }
  ],
  "timestamp": "2026-06-21T13:42:15+09:00"
}
```

#### 3. 이벤트 로그 저장
```
POST /api/events
Content-Type: application/json

{
  "event_id": "evt_20260621_000001",
  "user_id": "user_1024",
  "session_id": "sess_a91f",
  "event_type": "view",
  "event_time": "2026-06-21T13:42:10+09:00",
  "product_id": "sku_10031",
  "category_id": "cat_18",
  "brand": "adidas",
  "price": 59000,
  "quantity": 1,
  "page_url": "/products/sku_10031",
  "referrer": "/category/cat_18",
  "device_type": "desktop",
  "payload_json": {
    "source": "simulation_site"
  }
}
```

#### 4. 서버 상태 확인
```
GET /health

응답:
{
  "status": "ok"
}
```

## 이벤트 타입

- **view**: 상품 조회
- **cart**: 장바구니 추가
- **remove_from_cart**: 장바구니 제거
- **purchase**: 구매 완료

## 디바이스 타입

- **desktop**: 데스크톱
- **mobile**: 모바일
- **tablet**: 태블릿

## 카테고리 및 브랜드

### 지원하는 카테고리
- Face Care (cat_01)
- Makeup (cat_02)
- Body Care (cat_03)
- Hair Care (cat_04)
- Skincare (cat_05)

### 지원하는 브랜드
- adidas
- loreal
- maybelline
- neutrogena
- clinique

## 테스트

### 로컬 FastAPI 서버 실행
```bash
# FastAPI 서버 설치
pip install fastapi uvicorn

# 서버 실행
uvicorn main:app --reload --port 8000
```

### 환경변수 확인
```bash
# 개발 서버 콘솔에서 확인
echo $VITE_FASTAPI_URL
```

## 문제 해결

### FastAPI 서버에 연결할 수 없음
1. FastAPI 서버가 실행 중인지 확인
2. `VITE_FASTAPI_URL`이 올바른지 확인
3. CORS 설정 확인 (FastAPI 서버에서 localhost 허용 필요)

### 이탈률이 표시되지 않음
1. 브라우저 콘솔에서 에러 메시지 확인
2. FastAPI 서버 로그 확인
3. 네트워크 탭에서 요청/응답 확인

### 추천 상품이 표시되지 않음
1. FastAPI 서버의 `/api/recommendations` 엔드포인트 확인
2. 요청 데이터 형식 확인
3. FastAPI 서버 로그에서 에러 확인

## 보안 주의사항

- 프로덕션 환경에서는 HTTPS 사용
- API 키 또는 인증 토큰 필요 시 별도 설정
- CORS 설정에서 신뢰할 수 있는 도메인만 허용
- 민감한 정보는 환경변수로 관리

## 참고

- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [Vite 환경변수 문서](https://vitejs.dev/guide/env-and-mode.html)
- [프로젝트 README](./README.md)
