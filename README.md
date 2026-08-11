# 어디가남

전남 기반 여행 추천 서비스의 Django REST Framework 백엔드입니다.

## 현재 구현 범위

`docs/architecture.md`의 Stage 0~7(MVP 핵심 기능 + 배포 준비)과 백로그까지 전부 구현되어
있습니다(`docs/roadmap.md` 3절 상태표 기준). Notion 기능명세서의 8개 그룹 API가 모두
포함됩니다.

- **Auth (`accounts`)**: 회원가입/아이디 중복 확인, 이메일 인증코드, 로그인/로그아웃,
  비밀번호 재설정, 소셜 로그인(Google/Kakao)
- **검색·정보 (`places`)**: 통합 검색, 장소 상세, 관광지 예상 방문 집중도, 실시간 교통 혼잡
- **추천 (`courses`)**: 코스 저장/시작/완주인증/공유(`Course`/`CoursePlace`/`CourseProgress`),
  AI 맞춤 코스 추천, 동선 최적화
- **후기·만족도 (`reviews`)**: 후기 작성/목록/도움돼요/신고, AI 만족도·키워드 요약
- **찜하기 (`interactions`)**: 장소 찜하기(Bookmark)
- **게이미피케이션 (`gamification`)**: 위치 체크인/스탬프북, 숨겨진 여행지/완주 카드
- **마이페이지 (`mypage`)**: 프로필 조회/수정, 저장한 코스/내 후기/찜한 장소 목록
- **Home (`home`)**: 날씨 기반 추천 허브(현재 날씨 조회, 메인 홈 데이터)
- **공통 (`common`)**: 사용자 설정(UserSettings)/온보딩, 목록 API 공통 페이지네이션
  (`page`/`pageSize`), 공통 응답/예외 포맷
- **배포**: settings dev/prod 분리, Dockerfile, Docker Compose(MySQL + Gunicorn app +
  Nginx), CI(GitHub Actions)

## 개발 환경 실행

```bash
cp .env.example .env
uv sync
docker compose up -d mysql
uv run python manage.py migrate
uv run python manage.py runserver
```

개발 서버는 `http://127.0.0.1:8000`, Django Admin은 `http://127.0.0.1:8000/admin/`에서 접근할 수 있습니다.

## Docker Compose 배포 환경 실행

먼저 `.env.example`을 복사한 뒤 `DJANGO_SECRET_KEY`를 안전한 값으로 바꾸고, Nginx로 접근할 호스트들을 `DJANGO_ALLOWED_HOSTS`에 콤마로 구분해 입력합니다. 운영 설정에서만 사용하는 `DJANGO_ALLOWED_HOSTS`와 `DJANGO_SECRET_KEY`는 모두 필수입니다.

```bash
cp .env.example .env
# .env: DJANGO_DEBUG=False, DJANGO_SECRET_KEY와 DJANGO_ALLOWED_HOSTS 설정
docker compose up --build
```

최초 빌드 이후에는 `docker compose up`으로 MySQL, Gunicorn app, Nginx를 함께 실행할 수 있습니다. app 컨테이너가 migration과 `collectstatic`을 수행하고, Nginx는 기본적으로 `http://localhost/`에서 API를 reverse proxy하며 공유 volume의 `/static/` 파일을 직접 제공합니다. 호스트의 80번 포트를 사용할 수 없다면 `NGINX_PORT=8080 docker compose up`처럼 변경할 수 있습니다.

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
