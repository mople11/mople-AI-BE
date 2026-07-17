# 어디가남

전남 날씨 기반 여행 추천 서비스의 Django REST Framework 백엔드입니다.

## 현재 구현 범위

`docs/architecture.md`의 Stage 0(Django 프로젝트 뼈대)만 구현되어 있습니다.

- Django/DRF 프로젝트 설정
- `django-environ` 기반 환경변수
- PyMySQL을 사용한 MySQL 8 연결
- MySQL Docker Compose
- Simple JWT 기본 설정
- Django Admin 최상위 URL

도메인 앱과 API는 아직 생성하지 않았습니다. 회원/인증과 커스텀 `User`는 Stage 1에서 최초 도메인 마이그레이션 전에 추가합니다.

## 로컬 실행

```bash
cp .env.example .env
uv sync
docker compose up -d mysql
uv run python manage.py migrate
uv run python manage.py runserver
```

개발 서버는 `http://127.0.0.1:8000`, Django Admin은 `http://127.0.0.1:8000/admin/`에서 접근할 수 있습니다.

> Stage 1에서 `AUTH_USER_MODEL = "accounts.User"`를 처음 적용해야 하므로, Stage 0의 기본 auth 마이그레이션은 구조 확인용 로컬 DB에서만 실행하고 영구 데이터를 저장하지 마세요.

## 검증

```bash
uv run python manage.py check
uv run pytest
```
