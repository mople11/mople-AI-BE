# 어디가남

전남 날씨 기반 여행 추천 서비스의 FastAPI 백엔드입니다.

## 기술 스택

- Python 3.11+
- FastAPI
- uv
- pytest
- Pydantic Settings

## 이번 이슈의 범위

이번 `feature/api-skeleton` 브랜치에서는 모든 API를 한 번에 만들지 않습니다. Notion API 명세를 대충 추론해 전체 endpoint를 미리 열어두면, 이후 프론트엔드와 백엔드가 서로 다른 API 계약을 보게 될 수 있기 때문입니다.

따라서 이번 이슈는 다음 기반 작업에 집중합니다.

- FastAPI 프로젝트 구조 생성
- API v1 라우터 구조 생성
- 공통 성공 응답 형식 정의
- 공통 에러 응답 형식 정의
- 전역 예외 처리 구조 정의
- CORS 및 환경 설정 구조 정의
- Health check API 생성
- Auth 일부 endpoint를 Notion 명세 기준으로 생성
- pytest 기반 검증 추가
- GitHub Actions CI 추가

Course, Search, Place, Review, Mypage, Gamification 등은 각 기능 이슈에서 Notion 개별 API 페이지를 확인한 뒤 하나씩 정확히 구현합니다.

## 프로젝트 구조

```text
app
├── main.py
├── api
│   └── v1
│       ├── router.py
│       ├── health.py
│       └── auth.py
├── core
│   ├── config.py
│   └── security.py
├── exceptions
│   ├── base.py
│   ├── codes.py
│   └── handlers.py
└── schemas
    ├── response.py
    ├── error.py
    └── domain
        ├── health.py
        └── auth.py

tests
├── test_api_skeleton.py
├── test_error_response.py
└── test_health.py
```

## 공통 성공 응답

```json
{
  "success": true,
  "data": {},
  "error": null
}
```

## 공통 에러 응답

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "AUTH_401",
    "message": "인증이 필요합니다."
  }
}
```

## 현재 생성된 엔드포인트

### Health

- `GET /api/v1/health`

### Auth

Notion API 명세의 Auth endpoint를 기준으로 skeleton만 생성했습니다. 실제 회원가입, 로그인, 이메일 발송, 토큰 발급 로직은 이후 Auth 기능 이슈에서 구현합니다.

- `POST /api/v1/auth/signup`
- `GET /api/v1/auth/signup/check-id?id={id}`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/login/social`
- `POST /api/v1/auth/logout`
- `POST /api/v1/auth/email/verify-code`
- `POST /api/v1/auth/email/verify-confirm`
- `POST /api/v1/auth/password/reset-request`
- `POST /api/v1/auth/password/reset-confirm`

## 실행 방법

```bash
uv sync
uv run uvicorn app.main:app --reload
```

서버 실행 후 health check:

```bash
curl http://127.0.0.1:8000/api/v1/health
```

Swagger 문서:

```text
http://127.0.0.1:8000/docs
```

## 테스트

```bash
uv run pytest
```

테스트는 health check, Auth skeleton endpoint의 공통 응답 형식, 인증 헤더 검증, 공통 에러 응답을 확인합니다.

## 포트폴리오 정리

Python FastAPI 기반으로 `어디가남` 백엔드의 API 기반 구조를 설계했습니다. 처음에는 전체 API skeleton을 한 번에 생성하는 방식도 고려했지만, Notion 명세와 endpoint 계약이 어긋날 위험이 있어 범위를 줄였습니다.

이번 작업에서는 모든 기능 API를 미리 만들기보다, 공통 응답/에러 형식, 전역 예외 처리, CORS/환경 설정, pytest, CI, health check를 먼저 구성했습니다. Auth는 Notion 명세에서 endpoint가 확인된 범위만 skeleton으로 생성했습니다.

이후 기능 개발은 각 브랜치에서 Notion 개별 API 페이지를 확인한 뒤 하나씩 정확히 구현하는 방식으로 진행합니다. 이를 통해 API 계약의 정확성을 유지하고, 프론트엔드와 백엔드가 같은 명세를 기준으로 협업할 수 있도록 했습니다.
