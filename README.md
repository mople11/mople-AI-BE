# 어디가남

전남 기반 여행 추천 서비스의 Django REST Framework 백엔드입니다.

## 현재 구현 범위

`docs/architecture.md`의 Stage 1 중 회원가입과 아이디 중복 확인까지 구현되어 있습니다.

- Django/DRF 프로젝트 설정
- `django-environ` 기반 환경변수
- PyMySQL을 사용한 MySQL 8 연결
- MySQL Docker Compose
- Simple JWT 기본 설정
- Django Admin 최상위 URL
- 커스텀 `accounts.User` 모델
- 회원가입 및 아이디 중복 확인 API
- 공통 API 응답 및 예외 포맷

로그인, 소셜 로그인, 이메일 발송 및 비밀번호 재설정은 아직 구현하지 않았습니다.

## 로컬 실행

```bash
cp .env.example .env
uv sync
docker compose up -d mysql
uv run python manage.py migrate
uv run python manage.py runserver
```

개발 서버는 `http://127.0.0.1:8000`, Django Admin은 `http://127.0.0.1:8000/admin/`에서 접근할 수 있습니다.

## API 문서

개발 서버를 실행한 뒤 다음 주소에서 현재 API 계약을 확인할 수 있습니다.

- Swagger UI: `http://127.0.0.1:8000/docs/`
- OpenAPI 스키마: `http://127.0.0.1:8000/api/schema/`

OpenAPI 파일을 생성하고 명세 오류를 검증하려면 다음 명령을 실행합니다.

```bash
uv run python manage.py spectacular --file schema.yml --validate
```

> Stage 0에서 기본 auth 마이그레이션을 이미 실행한 로컬 DB라면 `docker compose down -v`로 개발용 볼륨을 초기화한 뒤 다시 마이그레이션해야 합니다.

## 검증

```bash
uv run python manage.py check
uv run pytest
```

새 MySQL 볼륨을 초기화할 때 애플리케이션 계정에 `test_<MYSQL_DATABASE>` 전용 권한이 자동 부여됩니다. 기존 볼륨에는 초기화 스크립트가 다시 실행되지 않으므로, 테스트 DB 권한이 없는 기존 개발 볼륨은 데이터를 확인한 뒤 `docker compose down -v`로 재생성해야 합니다. GitHub Actions에서는 테스트 전용 root 계정을 사용합니다.
