# 가지마 운영 백엔드 (FastAPI / Python)

19-2 설계 반영. **운영 정본 백엔드**. 학습(추론) 코드 없음 — 모델 레지스트리·평가 ingest·대시보드 차트 API·예측 로그를 담당한다. 점수(`churn_probability`)는 모델파트/사이드카가 제출한다.

> Node.js 백엔드(19-1)는 `team_project_churn/sample_project/backend_node/`에 보관(백업·테스트용). 가지마 운영 백엔드는 본 FastAPI다.

## 구조 (클린아키텍처, 19-2 §4·§5)
```
backend/
├── app/
│   ├── main.py                      # FastAPI 부트스트랩 + 라우터 등록
│   ├── config.py                    # .env 로딩, MySQL/임계값
│   ├── interfaces/http/             # 라우터(얇게) + API키 의존성
│   ├── schemas/                     # Pydantic 요청 모델
│   ├── application/                 # usecase(도메인+repo 조립)
│   ├── domain/                      # 위험등급·리텐션·앙상블(순수)
│   ├── infrastructure/mysql/        # repository(+memory 폴백)
│   ├── infrastructure/files/        # eval 산출물 reader(차트 원천)
│   └── validators/                  # 제출 payload 검증
├── db/schema_mysql.sql · migrate.py # 15테이블
└── scripts/submit_models.py         # 7모델 일괄 제출(26-9 P1)
```

## 실행
```bash
# 가지마 .venv 사용(streamlit과 공유)
.venv/Scripts/python -m pip install -r backend/requirements.txt
cp backend/.env.example backend/.env     # MYSQL_* 채우기(미설정 시 memory 데모 모드)
.venv/Scripts/python backend/db/migrate.py
.venv/Scripts/python -m uvicorn app.main:app --port 8090   # (cwd=backend)
# 7모델 적재(서버 기동 후)
.venv/Scripts/python backend/scripts/submit_models.py
```
Swagger 문서: `http://127.0.0.1:8090/docs`

## API (19-2 §8)
| Endpoint | Method | 책임 |
| --- | --- | --- |
| `/health` | GET | 상태(인증 불필요) |
| `/models/submit` | POST | 모델/평가 등록 |
| `/models` · `/models/active` | GET | 모델 목록 |
| `/models/{id}/evaluation` | GET | 평가 요약 |
| `/models/{model}/charts/{name}` | GET | roc/pr/threshold/calibration/shap(→feature_importance 폴백) |
| `/dashboard/summary` | GET | 7모델 비교 요약 |
| `/predict` | POST | 점수→위험등급·리텐션·로그 |
| `/predictions/latest` | GET | 유저 최신 예측 |
| `/predictions/top-risk` | GET | 고위험 유저(향후 7일 이탈확률 desc) |
| `/ensemble/run` | POST | 다모델 조합 |

인증: `/health` 외 전 엔드포인트 `x-api-key` 헤더 필요(.env `API_KEY`).
