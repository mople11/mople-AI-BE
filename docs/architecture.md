# 어디가남(Eodiganam) Django/DRF 아키텍처 설계

이 문서는 어디가남 백엔드를 FastAPI에서 Django REST Framework(DRF)로 전환하기 위한 설계 스펙이다.
이 문서를 기반으로 코드를 생성하는 에이전트(예: Codex)는 아래 원칙과 구조를 반드시 따른다.

## 0. 작업 원칙 (반드시 준수)

1. **기능 단위로 단계적으로 구현한다.** 한 커밋/한 세션에 전체 앱을 몰아서 만들지 않는다. 아래 "8. 단계별 구현 계획"의 스테이지 순서를 따른다.
2. **없는 스펙을 임의로 만들지 않는다.** `trips`, `reviews`, `likes`, `bookmarks` 등은 아직 Notion API 명세가 확정되지 않았다. 모델 필드나 엔드포인트를 추측해서 미리 만들지 말고, 해당 기능 스테이지에 도달했을 때 실제 명세를 먼저 확인한다. 지금 단계에서는 앱 스캐폴딩과 관계 설계 방향만 따른다.
3. **Django/DRF 기본 기능을 최대한 활용한다.** 커스텀 인증 백엔드, 커스텀 ORM 래퍼, 커스텀 시리얼라이저 베이스 등 불필요한 재구현을 피하고 `django.contrib.auth`, DRF `ModelSerializer`, `ModelViewSet`, `django.contrib.admin` 을 기본으로 사용한다.
4. **API 응답 계약(response contract)은 기존 FastAPI 버전과 동일하게 유지한다.** 프론트엔드가 이미 이 계약에 맞춰 개발되어 있을 수 있으므로, 아래 "5. API 공통 규약"을 그대로 재현한다.

## 1. 서비스 개요

- 이름: 어디가남 (Eodiganam)
- 설명: 전남(전라남도) 날씨 기반 여행 추천 서비스
- 명세 출처: Notion "기능명세서" 데이터베이스(그룹: `Auth`, `Home`, `검색·정보`, `추천`, `후기·만족도`, `게이미피케이션`, `마이페이지`, `공통`) + "API 설계" 페이지. 이 문서의 도메인 분리는 위 그룹 분류를 그대로 따른다.
- 핵심 도메인: 회원(가입/로그인/소셜로그인), 홈(날씨 기반 추천 허브), 검색·장소(통합검색/혼잡도/교통), 추천(AI 맞춤 코스/동선 최적화), 후기(별점/AI 만족도 분석), 게이미피케이션(시군 스탬프/숨겨진 여행지/완주카드), 마이페이지, 공통(설정/온보딩)
- 이전 스택: FastAPI + SQLite + PBKDF2 + 자체 JWT 구현 (전면 폐기, 참고용으로만 git 히스토리에 남음)

## 2. 기술 스택

| 영역 | 선택 | 비고 |
|---|---|---|
| 프레임워크 | Django + Django REST Framework | |
| 언어 | Python 3.12 | 현재 `.venv` 기준 |
| 패키지 관리 | uv | 기존 `pyproject.toml` / `uv.lock` 유지 |
| DB | MySQL 8 | 로컬은 Docker Compose로 컨테이너 실행 |
| DB 드라이버 | PyMySQL | `mysqlclient`는 시스템에 `libmysqlclient-dev`가 없어 빌드 불가. 배포 환경에서 필요 시 `mysqlclient`로 교체 가능 |
| 인증 토큰 | `djangorestframework-simplejwt` | access/refresh 토큰 발급, 기존 FastAPI 버전과 동일하게 JWT 유지 |
| 환경변수 | `django-environ` | `.env` 파일 로드 |
| 테스트 | `pytest` + `pytest-django` | 기존 pytest 사용 경험 유지 |

## 3. 저장소 구조

```text
Eodiganam/
├── manage.py
├── config/                      # Django 프로젝트 패키지 (도메인 로직 없음)
│   ├── __init__.py
│   ├── settings.py               # 단일 설정 파일 (dev/prod 분리는 배포 단계에서 도입)
│   ├── urls.py                   # 최상위 URL 라우팅, api/v1/* include
│   ├── wsgi.py
│   └── asgi.py
├── accounts/                      # Stage 1: 회원/인증 (Auth 그룹)
│   ├── models.py                  # User, SocialAccount, EmailVerificationCode
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   ├── permissions.py
│   └── admin.py
├── places/                        # Stage 2: 검색·정보 그룹 (Place, 통합검색, 혼잡도, 교통)
├── courses/                       # Stage 3: 추천 그룹 (Course, CoursePlace, AI 추천/동선 최적화)
├── reviews/                       # Stage 4: 후기·만족도 그룹 (Review, 도움돼요)
├── interactions/                  # Stage 4: Bookmark(찜) — Place/Course 공통 찜하기
├── gamification/                  # Stage 5: 게이미피케이션 (Stamp, HiddenPlaceUnlock, CompletionCard)
├── mypage/                        # Stage 6: 마이페이지 — 다른 앱 데이터를 모아 보여주는 조회 전용 앱
├── home/                          # Stage 6: Home 그룹 — 날씨 연동 추천 허브 (자체 모델 없이 다른 앱 조회)
├── common/                        # 공통 응답 포맷, 에러 코드, 커스텀 예외 핸들러, Settings
│   ├── response.py                # ApiResponse 포맷 래핑 유틸
│   ├── exceptions.py              # ErrorCode enum (기존 app/exceptions/codes.py 이식)
│   ├── exception_handler.py       # DRF custom exception handler
│   └── models.py                  # UserSettings (알림/언어 등, 공통 그룹)
├── docker-compose.yml             # MySQL 로컬 컨테이너
├── .env / .env.example
├── pyproject.toml
└── docs/
    └── architecture.md           # 이 문서
```

각 도메인 앱(`accounts`, `trips`, `reviews`, `interactions`)은 Django app 단위이며, `config/urls.py`에서 `path("api/v1/xxx/", include("xxx.urls"))` 형태로 연결한다.

## 4. 설정(config) 설계

### 4.1 `config/settings.py` 핵심 항목

- `INSTALLED_APPS`: `django.contrib.admin`, `auth`, `contenttypes`, `sessions`, `staticfiles` (기본) + `rest_framework`, `rest_framework_simplejwt`, `rest_framework_simplejwt.token_blacklist`(로그아웃 시 refresh token 무효화용, `feature/auth-login`에서 추가 — 6.4절 참고) + 도메인 앱들
- `AUTH_USER_MODEL = "accounts.User"` — 커스텀 User 모델 사용 선언 (반드시 최초 마이그레이션 전에 설정)
- `REST_FRAMEWORK`: 기본 인증 클래스를 `rest_framework_simplejwt.authentication.JWTAuthentication`으로, 기본 예외 핸들러를 `common.exception_handler.custom_exception_handler`로 지정
- `DATABASES["default"]`: `django.db.backends.mysql`, PyMySQL 사용을 위해 `config/__init__.py`에서 `pymysql.install_as_MySQLdb()` 호출
- `SECRET_KEY`, `DEBUG`, DB 접속 정보는 전부 `django-environ`으로 `.env`에서 로드

### 4.2 환경 변수 (`.env.example`)

```
DJANGO_SECRET_KEY=change-me-in-env
DJANGO_DEBUG=True
MYSQL_DATABASE=eodiganam
MYSQL_USER=eodiganam
MYSQL_PASSWORD=change-me-in-env
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
JWT_ACCESS_TOKEN_LIFETIME_MIN=60
JWT_REFRESH_TOKEN_LIFETIME_DAYS=14
EMAIL_VERIFICATION_CODE_LIFETIME_MIN=5
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

(`DEV_EMAIL_VERIFICATION_CODE`는 이슈 #5에서 실제 `EmailVerificationCode` 조회 방식으로 대체되며 제거된다.)

### 4.3 로컬 MySQL (`docker-compose.yml`)

MySQL 8 컨테이너 하나만 정의한다. Django 앱 자체는 아직 컨테이너화하지 않고 로컬 venv에서 `manage.py runserver`로 실행한다. 전체 앱 Docker화(+ Nginx)는 배포 단계에서 별도로 설계한다.

## 5. API 공통 규약 (기존 FastAPI 버전과 동일 유지)

### 5.1 응답 포맷

```json
{ "success": true, "data": { ... }, "error": null }
```

```json
{ "success": false, "data": null, "error": { "code": "DUPLICATE_ID", "message": "이미 사용 중인 아이디입니다." } }
```

DRF 필드 검증 오류는 기존 `code`/`message`를 유지하면서 어떤 필드가 실패했는지 알 수 있도록 `error.details`를 추가한다.

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "COMMON_422",
    "message": "요청 값이 올바르지 않습니다.",
    "details": { "email": ["유효한 이메일 주소를 입력하십시오."] }
  }
}
```

DRF는 기본적으로 이 포맷을 강제하지 않으므로, `common/exception_handler.py`에서 DRF의 `exception_handler`를 감싸 에러 발생 시 위 포맷으로 변환하고, 정상 응답은 `common/response.py`의 헬퍼(`ApiResponse(data=...)`)로 감싸 반환한다.

### 5.2 에러 코드

기존 `app/exceptions/codes.py`의 `ErrorCode` enum을 `common/exceptions.py`로 이식하고, 회원가입 단계에서는 `DUPLICATE_ID`, `DUPLICATE_EMAIL`, `CODE_MISMATCH`, `PASSWORD_MISMATCH`, `TERMS_NOT_AGREED`를 사용한다. 새 코드가 필요하면 이 enum에 추가하는 방식으로 확장한다.

이슈 #5(이메일 인증코드) 반영 시 `CODE_EXPIRED`를 추가한다. `CODE_MISMATCH`는 코드 값 자체가 틀린 경우, `CODE_EXPIRED`는 코드 값은 맞지만 `expires_at`이 지난 경우로 구분한다.

`feature/auth-login`(로그인/로그아웃) 반영 시 `INVALID_CREDENTIALS`(401)와 `INVALID_TOKEN`(400)을 추가한다. 자세한 발생 조건은 6.4절 표를 따른다.

### 5.3 URL 버전 규약

기존과 동일하게 `api/v1/` 프리픽스를 유지한다. 예: `api/v1/auth/signup`.

## 6. accounts 앱 설계 (Stage 1)

기존 FastAPI의 `SignupRequest`/`LoginRequest` 스키마(`app/schemas/domain/auth.py`)에 정의된 필드는 이미 확정된 Notion API 명세이므로 그대로 계승한다.

### 6.1 모델

**`User` (`AbstractUser` 상속)**
- `username` → 로그인 아이디로 사용 (기존 스펙의 `id` 필드에 대응). `USERNAME_FIELD`는 기본값(`username`) 유지.
- `email` — 고유(unique) 제약 추가 (`AbstractUser` 기본은 unique 아님)
- `nickname` — `CharField`, 신규 필드
- `agreed_terms_at` — `DateTimeField(null=True)`, 약관 동의 시각 기록 (TERMS_NOT_AGREED 검증용)
- 비밀번호는 Django 기본 `set_password`/`check_password` (PBKDF2, Django 기본 해셔) 사용 — 자체 해싱 구현 금지

**`SocialAccount`**
- `user` — FK to `User`
- `provider` — `CharField`, choices: `google`, `kakao` (기존 `SocialLoginRequest.provider` Literal과 동일)
- `provider_uid` — `CharField`
- `(provider, provider_uid)` unique_together

**`EmailVerificationCode`**
- `email` — `CharField`
- `code` — `CharField`
- `purpose` — choices: `signup`, `password_reset`
- `expires_at` — `DateTimeField`
- `is_used` — `BooleanField(default=False)`

### 6.2 엔드포인트 (기존 명세 매핑)

| 메서드/경로 | 기존 FastAPI 대응 | 설명 |
|---|---|---|
| `POST /api/v1/auth/signup` | `signup` | 회원가입 |
| `GET /api/v1/auth/signup/check-id` | `check_id_duplicate` | 아이디 중복 확인 |
| `POST /api/v1/auth/login` | `login` | 아이디/비밀번호 로그인 → JWT 발급 (6.4절) |
| `POST /api/v1/auth/login/social` | `social_login` | 소셜 로그인 (google/kakao) |
| `POST /api/v1/auth/logout` | `logout` | 로그아웃 — refresh token을 `token_blacklist`에 등록해 무효화 (6.4절) |
| `POST /api/v1/auth/email/verify-code` | `send_email_code` | 이메일 인증코드 발송 |
| `POST /api/v1/auth/email/verify-confirm` | `verify_email_code` | 이메일 인증코드 확인 |
| `POST /api/v1/auth/password/reset-request` | `send_password_reset_code` | 비밀번호 재설정 코드 발송 |
| `POST /api/v1/auth/password/reset-confirm` | `reset_password` | 비밀번호 재설정 |

뷰는 `APIView` 또는 `generics.GenericAPIView` 기반으로 액션별 클래스를 만든다 (CRUD 리소스가 아니라 액션 중심 엔드포인트이므로 `ModelViewSet`은 부적합).

회원가입과 아이디 중복 확인에는 다음 검증 규칙을 적용한다.

- `id`는 필수이며 공백일 수 없고, Django `username`과 동일하게 최대 150자 및 `UnicodeUsernameValidator` 규칙을 적용한다.
- `email`은 유효한 이메일 형식이어야 하며 중복될 수 없다.
- `pw`는 `AUTH_PASSWORD_VALIDATORS`를 모두 통과해야 한다.
- `nickname`은 필수이며 공백일 수 없고 최대 50자이다.
- 일반 필드 검증 실패는 `COMMON_422`와 필드별 `error.details`를 반환한다.

### 6.3 이메일 인증코드 발송/확인 (이슈 #5)

`SignupSerializer.validate_verifyCode`가 `settings.DEV_EMAIL_VERIFICATION_CODE`(고정값)와 단순 비교하던 임시 구현을 실제 `EmailVerificationCode` 조회 방식으로 교체한다.

- **유효시간**: `EMAIL_VERIFICATION_CODE_LIFETIME_MIN` 환경변수(기본값 5분)만큼 발급 시점부터 유효. `EmailVerificationCode.expires_at`은 발급 시각 + 이 값으로 저장한다. 코드에 값을 하드코딩하지 않는다.
- **에러 코드 구분**: 코드 값이 틀리면 `CODE_MISMATCH`, 코드 값은 맞지만 `expires_at`이 지났으면 `CODE_EXPIRED`를 반환한다.
- **이메일 발송 백엔드**: `EMAIL_BACKEND` 환경변수로 설정. 로컬 개발은 `django.core.mail.backends.console.EmailBackend`(콘솔 출력), 테스트는 Django 테스트 러너가 자동으로 적용하는 `locmem.EmailBackend`를 사용하므로 테스트 설정에서 별도 오버라이드가 필요 없다. 실제 SMTP 연동은 배포 단계에서 환경변수 값만 교체해 적용한다.
- `SignupSerializer.validate_verifyCode`는 `email`+`code`로 미사용(`is_used=False`)·미만료 레코드를 조회해 검증하고, 성공 시 해당 레코드를 `is_used=True`로 갱신한다.

### 6.4 로그인/로그아웃 설계 (`feature/auth-login`)

`feature/auth-signup`([[project_branch_scope_auth_signup]] 참고)에서 제외했던 로그인/로그아웃을 이 브랜치에서 구현한다. 대상은 `POST /api/v1/auth/login`, `POST /api/v1/auth/logout` 두 엔드포인트로 한정하고, 소셜 로그인·비밀번호 재설정은 포함하지 않는다.

#### 6.4.1 로그아웃 방식 결정: refresh token 블랙리스트

simplejwt는 기본적으로 stateless라 발급된 토큰을 서버가 강제로 무효화할 수단이 없다. 두 선택지를 검토했다.

- **(A) 아무것도 안 함** — "로그아웃"은 클라이언트가 로컬에 저장된 토큰을 지우는 동작뿐이고, 서버 입장에서 access/refresh token은 자연 만료 전까지 계속 유효하다.
- **(B) `rest_framework_simplejwt.token_blacklist` 앱을 설치**하고, 로그아웃 시 전달받은 refresh token을 블랙리스트에 등록한다. 이후 이 refresh token으로는 새 access token을 재발급받을 수 없다.

**(B)를 채택한다.** 근거:

1. 로그인 응답 계약(`AuthTokenResponse`)에 `refreshToken`이 포함돼 있다는 것 자체가 클라이언트가 이 토큰을 들고 있다는 전제다. 로그아웃이 이 토큰에 아무 영향도 못 주면 사용자에게는 "로그아웃했다"는 착각만 남긴다.
2. `token_blacklist`는 이미 의존성에 있는 `djangorestframework-simplejwt` 패키지에 포함된 앱을 `INSTALLED_APPS`에 추가하는 것으로 끝난다 — 커스텀 세션/토큰 관리 로직을 새로 만들 필요가 없다 (0절 원칙 3: Django/DRF 기본 기능 활용).
3. 비용은 `OutstandingToken`/`BlacklistedToken` 테이블 2개와 마이그레이션 1회뿐이다.

**한계**: access token 자체는 여전히 stateless이므로 로그아웃 직후에도 만료 전까지는 유효하다(`JWT_ACCESS_TOKEN_LIFETIME_MIN`만큼). 이 한계는 access token 수명을 짧게 유지하는 선에서 감수하고, access token 자체를 무효화하는 별도 장치(예: 매 요청마다 블랙리스트 조회)는 이번 스테이지에서 도입하지 않는다.

**설정 및 배포 변경**: `INSTALLED_APPS`에 `rest_framework_simplejwt.token_blacklist`를 추가하고, 애플리케이션 배포 전에 반드시 `python manage.py migrate --noinput`을 실행한다. 이 앱이 활성화되면 `RefreshToken.for_user()`가 `OutstandingToken` 테이블에 발급 토큰을 기록하므로, 마이그레이션을 누락하면 로그아웃뿐 아니라 해당 메서드를 사용하는 회원가입과 로그인도 500 오류로 실패한다. CI도 테스트 전에 마이그레이션을 명시적으로 실행한다. 추가 환경변수는 필요 없다.

**refreshToken을 응답 바디로 내려주는 방식에 대한 검토**: `refreshToken`을 JSON 응답 바디에 평문으로 담아 내려주면, 클라이언트가 이를 저장하는 방식(예: localStorage)에 따라 XSS 공격 시 탈취될 수 있다는 지적이 있었다. 대안으로 `HttpOnly`/`Secure`/`SameSite=Strict` 쿠키로 전달하는 방식을 검토했으나, 다음 이유로 **현재의 JSON 바디 방식을 유지**하기로 확정한다.

- `AuthTokenResponse` 계약은 이미 확정된 API 명세이고, signup 응답도 이미 `accessToken`을 바디로 내려주는 선례가 있어 일관성이 있다.
- 쿠키 방식은 CORS/CSRF 처리와 쿠키 도메인 설정이 추가로 필요하고 API 계약이 바뀌어 프론트 연동을 다시 맞춰야 한다 — 이번 `feature/auth-login` 범위를 넘어서는 변경이다.
- 탈취 위험은 로그아웃 시 refresh token을 즉시 블랙리스트에 등록(위 (B) 결정)하고 access token 수명을 짧게 유지하는 것으로 완화한다. 완전한 제거가 아니라 완화라는 점은 인지하고 있으며, 쿠키 전환은 추후 필요 시 별도 브랜치에서 재검토한다.

#### 6.4.2 에러 코드 추가

| 코드 | 상태코드 | 메시지 | 발생 조건 |
|---|---|---|---|
| `INVALID_CREDENTIALS` | 401 | 아이디 또는 비밀번호가 일치하지 않습니다. | 로그인 시 `authenticate()`가 `None`을 반환. 아이디가 존재하지 않는 경우/비밀번호가 틀린 경우/계정이 비활성인 경우를 구분하지 않고 동일 코드로 응답한다 (아이디 존재 여부가 유추되지 않도록 의도적으로 뭉뚱그림 — `CODE_MISMATCH`/`CODE_EXPIRED`를 분리했던 이슈 #5 방식과는 반대 방향의 선택이다) |
| `INVALID_TOKEN` | 400 | 유효하지 않은 토큰입니다. | 로그아웃 요청의 `refreshToken`이 형식 오류·서명 불일치·만료·이미 블랙리스트에 있거나, access token으로 인증한 사용자의 토큰이 아닌 경우 |

기존 `AUTH_401`("인증이 필요합니다")은 그대로 두고 재사용하지 않는다. `AUTH_401`은 "요청 자체에 유효한 인증이 없는 경우"(access token 누락/만료)에 쓰이고, `INVALID_CREDENTIALS`는 "로그인 시도 자체가 틀린 경우"에 쓰여 의미가 다르다.

#### 6.4.3 `POST /api/v1/auth/login`

**요청** (`LoginSerializer`)

| 필드 | 타입 | 비고 |
|---|---|---|
| `id` | str | 로그인 아이디 (`User.username`), 최대 150자 |
| `pw` | str | `write_only` |

**뷰 로직** (`LoginView`, `permission_classes = [AllowAny]`)

1. `LoginSerializer`로 필수 여부와 `id`의 최대 길이(150자)를 검증한다. 사용자 존재 여부나 비밀번호 일치는 여기서 검사하지 않는다.
2. `django.contrib.auth.authenticate(request, username=id, password=pw)`를 호출한다. 직접 `User.objects.get` + `check_password`를 호출하지 않는 이유: `authenticate()`는 등록된 인증 백엔드(`ModelBackend`)를 통해 비밀번호 검증과 `is_active` 체크를 함께 수행한다. 비활성 계정은 비밀번호가 맞아도 `None`을 반환하므로 별도 분기 없이 자연스럽게 로그인 거부로 이어진다.
3. `authenticate()`가 `None`이면 `ApiError(ErrorCode.INVALID_CREDENTIALS)`를 발생시킨다.
4. 성공하면 `RefreshToken.for_user(user)`로 refresh token을 발급하고, `str(refresh)`(refresh token 문자열)와 `str(refresh.access_token)`(access token 문자열)을 함께 응답한다.

**응답 데이터** (`AuthTokenResponse`)

```json
{
  "success": true,
  "data": {
    "accessToken": "eyJ...",
    "refreshToken": "eyJ...",
    "user": { "id": "traveler", "nickname": "여행자" }
  },
  "error": null
}
```

`user.id`는 signup 응답의 `userId`와 키 이름이 다르다 — 이미 확정된 API 계약이므로 그대로 따르고, 두 응답 간 통일성을 이유로 임의로 바꾸지 않는다. 값은 DB PK가 아니라 `LoginRequest.id`와 동일한 로그인 아이디(`user.username`)이며, 응답 시 정수 PK를 노출하지 않는다.

#### 6.4.4 `POST /api/v1/auth/logout`

**요청** (`LogoutSerializer`, `permission_classes = [IsAuthenticated]`)

| 필드 | 타입 | 비고 |
|---|---|---|
| `refreshToken` | str | 로그인 시 발급받은 refresh token |

`IsAuthenticated`는 로그아웃 요청에 유효한 access token(`Authorization: Bearer ...`)이 있는지만 확인하며, 요청 바디의 refresh token 소유권까지 보장하지는 않는다. 따라서 복원한 refresh token의 `user_id` 클레임이 `request.user.pk`와 일치하는지 별도로 확인한다. access token이 없거나 만료된 요청은 `common/exception_handler.py`가 이미 처리하는 경로(`NotAuthenticated`/`AuthenticationFailed` → `AUTH_401`)로 응답한다.

**뷰 로직** (`LogoutView`)

1. `LogoutSerializer`로 `refreshToken` 존재 여부만 검증한다 (누락 시 `COMMON_422`).
2. `RefreshToken(refreshToken_문자열)`로 토큰 객체를 복원한다 — 이 시점에 서명·만료·블랙리스트 여부가 함께 검증된다.
3. 복원한 토큰의 `user_id`와 `request.user.pk`가 다르면 토큰 소유 관계를 노출하지 않고 `ApiError(ErrorCode.INVALID_TOKEN)`을 반환한다.
4. 검증을 통과하면 `token.blacklist()`를 호출한다. simplejwt는 이 한 번의 호출로 `OutstandingToken` 등록과 `BlacklistedToken` 추가를 `get_or_create`로 함께 처리한다.
5. `TokenError`(서명 불일치·만료·이미 블랙리스트됨)가 발생하면 `ApiError(ErrorCode.INVALID_TOKEN)`으로 변환한다.
6. 성공 응답은 별도 데이터 없이 `data: null`로 반환한다.

**응답**

```json
{ "success": true, "data": null, "error": null }
```

#### 6.4.5 URL 등록 (`accounts/urls.py`)

```
POST /api/v1/auth/login   -> LoginView   (name="login")
POST /api/v1/auth/logout  -> LogoutView  (name="logout")
```

#### 6.4.6 테스트 관점 (`tests/test_auth_login.py`, 신규)

- 로그인 성공: 응답에 `accessToken`/`refreshToken`/`user.id`/`user.nickname`이 모두 존재하는지 확인.
- 로그인 실패 — 존재하지 않는 아이디: `INVALID_CREDENTIALS`, 401.
- 로그인 실패 — 비밀번호 불일치: `INVALID_CREDENTIALS`, 401 (아이디 존재 여부와 무관하게 응답이 동일한지 확인).
- 로그아웃 성공: 로그인으로 받은 `refreshToken`으로 로그아웃 요청 → 같은 문자열로 `RefreshToken(token)`을 다시 생성하면 블랙리스트로 인해 `TokenError`가 발생하는지, 또는 `BlacklistedToken` 레코드가 생성됐는지로 확인.
- 로그아웃 실패 — access token 없이 요청: `AUTH_401`.
- 로그아웃 실패 — 다른 사용자의 access token과 refresh token 조합: `INVALID_TOKEN`, 400이며 refresh token은 블랙리스트에 등록되지 않음.
- 로그아웃 실패 — 형식이 잘못됐거나 만료/이미 블랙리스트된 `refreshToken`: `INVALID_TOKEN`, 400.

#### 6.4.7 미해결 사항 (이번 브랜치 범위 밖)

현재 6.2절 엔드포인트 목록에는 refresh token으로 access token을 재발급받는 `POST /api/v1/auth/token/refresh` 같은 엔드포인트가 없다. 즉 로그인 응답으로 `refreshToken`을 내려주지만, 클라이언트가 이를 실제로 소비할 방법이 아직 명세에 없다. Notion 명세에 해당 엔드포인트가 있는지 확인이 필요하며, 없다면 access token 만료 시 재로그인을 강제하는 것으로 정할지 별도 결정이 필요하다 — 이번 `feature/auth-login` 범위에서는 임의로 추가하지 않는다 (0절 원칙 2).

### 6.5 비밀번호 재설정 설계 (`feature/auth-password-reset`)

대상은 `POST /api/v1/auth/password/reset-request`, `POST /api/v1/auth/password/reset-confirm` 두 엔드포인트다. `EmailVerificationCode`(이슈 #5)를 `purpose="password_reset"`으로 재사용하며 새 모델은 만들지 않는다.

#### 6.5.1 이메일 존재 여부 비노출 정책

`reset-request`는 요청한 이메일이 실제 가입된 계정인지와 무관하게 항상 동일한 성공 응답(`{"message": "인증번호가 발송되었습니다."}`)을 반환한다. 실제로 인증코드를 생성하고 메일을 발송하는 것은 서버 내부에서 `User.objects.filter(email=...).exists()`가 참일 때만 수행한다.

**근거**: 존재하지 않는 이메일에 대해 응답을 다르게 하면(예: 404) 공격자가 이메일 목록을 순회해 어떤 이메일이 가입되어 있는지 알아낼 수 있다(User enumeration). 응답을 동일하게 유지하면서 실제 발송만 내부적으로 건너뛰면, 가입되지 않은 이메일로 "비밀번호 재설정" 메일이 나가는 것도 막을 수 있다.

이 정책의 부수 효과로 `reset-confirm`에도 별도의 "이메일 존재 확인" 로직이 필요 없다 — 애초에 존재하지 않는 이메일에는 `EmailVerificationCode` 레코드가 생성되지 않으므로, 어떤 코드를 넣어도 `verify_email_verification_code`가 자연스럽게 `CODE_MISMATCH`로 처리한다.

**한계**: 실제 발송 시 `send_mail` 호출(SMTP 왕복)이 추가되므로, 계정 존재 여부에 따라 응답 시간에 미세한 차이가 날 수 있다(timing side channel). 이번 스테이지에서는 별도의 더미 지연을 넣는 등의 완화 장치는 도입하지 않는다 — 응답 바디/상태 코드가 완전히 동일한 것만으로도 실무 기준을 충족한다고 보고, 타이밍 채널까지 막는 것은 과설계로 판단한다.

#### 6.5.2 `POST /api/v1/auth/password/reset-request`

**요청** (`PasswordResetRequestSerializer`)

| 필드 | 타입 | 비고 |
|---|---|---|
| `email` | str | 재설정 코드를 받을 이메일 주소 |

`purpose`는 클라이언트가 지정하지 않는다 — 이 엔드포인트 자체가 `password_reset` 목적 전용이므로 서비스 계층에서 고정한다. (기존 범용 `POST /api/v1/auth/email/verify-code`는 `purpose`를 파라미터로 받지만, 이 엔드포인트는 그와 별개의 전용 엔드포인트로 6.2절 표에 이미 명시되어 있다.)

**서비스 로직** (`send_password_reset_code`, `accounts/services.py`)

```python
def send_password_reset_code(*, email: str) -> None:
    if User.objects.filter(email=email).exists():
        send_email_verification_code(
            email=email,
            purpose=EmailVerificationCode.Purpose.PASSWORD_RESET,
        )
```

기존 `send_email_verification_code`(이슈 #5)를 그대로 재사용하고, 앞단에 존재 여부 체크만 추가한다.

**뷰 로직** (`PasswordResetRequestView`, `permission_classes = [AllowAny]`)

1. `PasswordResetRequestSerializer`로 `email` 형식만 검증한다.
2. `send_password_reset_code(email=...)`를 호출한다 — 반환값과 무관하게 항상 성공 응답.

**응답**

```json
{ "success": true, "data": { "message": "인증번호가 발송되었습니다." }, "error": null }
```

#### 6.5.3 `POST /api/v1/auth/password/reset-confirm`

**요청** (`PasswordResetConfirmSerializer`)

| 필드 | 타입 | 비고 |
|---|---|---|
| `email` | str | 인증번호를 발급받은 이메일 |
| `code` | str | 6자리 인증번호. `VerifyEmailVerificationCodeSerializer`와 동일한 형식 검증(6자리 숫자) 적용 |
| `newPw` | str | `write_only`. `AUTH_PASSWORD_VALIDATORS`를 모두 통과해야 함 |

**정정(2026-07-19)**: 최초 초안은 "`SignupSerializer`와 동일한 `validate()`/`save()` 이중 검증 패턴"이라고 썼으나 부정확했다. `save()`/`create()`를 오버라이드해 소비 로직을 두는 것은 **새 리소스를 생성하는** `SignupSerializer`뿐이고, 액션성 엔드포인트(`LoginView`/`LogoutView`/`SendEmailVerificationCodeView`/`VerifyEmailVerificationCodeView`)는 전부 시리얼라이저에 `save()`를 두지 않고 **뷰가 서비스 함수를 직접 호출**하는 패턴이다. 비밀번호 재설정 확인은 리소스 생성이 아니라 기존 `User`를 변경하는 액션이므로 후자를 따른다.

- 시리얼라이저(`PasswordResetConfirmSerializer`)는 `validate()`에서 락 없는 1차 검증(코드 일치 여부, 비밀번호 정책)만 수행하고 `save()`는 두지 않는다 — `VerifyEmailVerificationCodeSerializer`와 동일한 성격.
- 실제 소비(트랜잭션 + `select_for_update` + `set_password` + `is_used` 갱신)는 `accounts/services.py`에 `reset_password(*, email, code, new_password)` 함수로 새로 추가하고, 뷰가 이를 호출한다 — `send_email_verification_code`/`verify_email_verification_code`와 같은 자리에 둔다.
- 시리얼라이저 필드명은 `newPw`(API 계약)이지만 서비스 함수 인자명은 `new_password`(파이썬 관례)로 다르므로, 뷰에서 `**serializer.validated_data`로 그대로 넘기지 말고 명시적으로 매핑한다.

```python
# accounts/serializers.py
def validate(self, attrs):
    verify_email_verification_code(
        email=attrs["email"],
        code=attrs["code"],
        purpose=EmailVerificationCode.Purpose.PASSWORD_RESET,
    )

    try:
        user = User.objects.get(email=attrs["email"])
    except User.DoesNotExist:
        # 이론상 도달하지 않음: 6.5.1 정책상 존재하지 않는 이메일에는
        # 애초에 EmailVerificationCode가 생성되지 않으므로 이 지점에
        # 도달했다는 것 자체가 code가 일치했다는 뜻이다. 코드 발급과
        # 확인 사이에 계정이 삭제된 극히 드문 레이스만 여기 해당하며,
        # 새 에러 코드를 추가하는 대신 기존 CODE_MISMATCH로 뭉뚱그린다.
        raise ApiError(ErrorCode.CODE_MISMATCH)

    try:
        validate_password(attrs["newPw"], user=user)
    except DjangoValidationError as exc:
        raise serializers.ValidationError({"newPw": exc.messages}) from exc

    return attrs
```

```python
# accounts/services.py
def reset_password(*, email: str, code: str, new_password: str) -> User:
    with transaction.atomic():
        verification = verify_email_verification_code(
            email=email,
            code=code,
            purpose=EmailVerificationCode.Purpose.PASSWORD_RESET,
            for_update=True,
        )
        try:
            user = User.objects.select_for_update().get(email=email)
        except User.DoesNotExist:
            # validate()와 동일한 극히 드문 레이스(코드 발급 후 계정 삭제)
            # 대응 — 여기서도 독립적으로 재확인한다.
            raise ApiError(ErrorCode.CODE_MISMATCH)
        user.set_password(new_password)
        user.save(update_fields=["password"])
        verification.is_used = True
        verification.save(update_fields=["is_used"])
    return user
```

`validate_password`에 새로 조회한 `User` 인스턴스를 넘겨 `UserAttributeSimilarityValidator`(아이디/이메일과 비슷한 비밀번호 거부) 등이 signup과 동일하게 작동하도록 한다.

**뷰 로직** (`PasswordResetConfirmView`, `permission_classes = [AllowAny]`)

1. `PasswordResetConfirmSerializer`로 1차 검증한다 (`serializer.is_valid(raise_exception=True)`).
2. 필드명을 명시적으로 매핑해 `reset_password()`를 호출한다:
   ```python
   reset_password(
       email=serializer.validated_data["email"],
       code=serializer.validated_data["code"],
       new_password=serializer.validated_data["newPw"],
   )
   ```
3. 별도 데이터 가공 없이 응답한다.

**응답**

```json
{ "success": true, "data": { "success": true }, "error": null }
```

**에러 코드**: 새 에러 코드를 추가하지 않는다. `CODE_MISMATCH`/`CODE_EXPIRED`/`CODE_ALREADY_USED`(이슈 #5)를 그대로 재사용하고, `newPw`가 비밀번호 정책을 통과하지 못하면 signup의 `pw` 필드와 동일하게 `serializers.ValidationError` → `COMMON_422` + `error.details`로 처리된다.

#### 6.5.4 URL 등록 (`accounts/urls.py`)

```
POST /api/v1/auth/password/reset-request  -> PasswordResetRequestView  (name="password-reset-request")
POST /api/v1/auth/password/reset-confirm  -> PasswordResetConfirmView  (name="password-reset-confirm")
```

#### 6.5.5 테스트 관점 (`tests/test_auth_password_reset.py`, 신규)

- 재설정 요청 성공 — 가입된 이메일: 응답이 성공 형태이고, 이메일 백엔드에 발송 기록이 남는지 확인.
- 재설정 요청 — 가입되지 않은 이메일: 가입된 이메일과 동일한 성공 응답이 오는지, 그리고 이메일이 실제로는 발송되지 않았는지(`mail.outbox` 비어있음) 함께 확인.
- 재설정 확인 성공: 발급받은 코드와 새 비밀번호로 요청 → 응답 성공, 이후 새 비밀번호로 로그인 가능한지 확인.
- 재설정 확인 실패 — 코드 불일치: `CODE_MISMATCH`, 400.
- 재설정 확인 실패 — 코드 만료: `CODE_EXPIRED`, 400.
- 재설정 확인 실패 — 이미 사용된 코드로 재시도: `CODE_ALREADY_USED`, 400.
- 재설정 확인 실패 — 새 비밀번호가 정책 미달(예: 너무 짧음, 아이디와 유사): `COMMON_422` + `error.details.newPw`.
- 재설정 확인 성공 후 같은 코드로 재요청: 이미 `is_used=True`이므로 `CODE_ALREADY_USED`.

#### 6.5.6 미해결 사항 (이번 브랜치 범위 밖)

비밀번호 재설정 성공 시 해당 사용자의 기존 refresh token들을 전부 블랙리스트에 등록해 다른 기기의 로그인 세션을 강제로 끊을지 여부는 이번 브랜치에서 다루지 않는다.

**이번 브랜치 범위 밖으로 남기는 이유**:
1. 이슈 완료조건 4가지(재설정 코드 발송/확인 플로우, 비밀번호 정책 통과, 이메일 존재 여부 비노출 정책, pytest 통과) 어디에도 세션 무효화가 포함되어 있지 않다 — 0절 원칙 2("없는 스펙을 임의로 만들지 않는다")에 따라 이번 범위에 임의로 추가하지 않는다.
2. `token_blacklist` 앱은 이미 설치돼 있으므로(6.4.1) 기술적으로는 `OutstandingToken.objects.filter(user=user)`를 순회하며 `blacklist()` 처리하는 것으로 추가 의존성 없이 구현 가능하다 — 즉 "못 해서" 미루는 게 아니라 "이번 이슈 범위가 아니라서" 미루는 것이며, 필요해지면 별도 이슈/브랜치에서 바로 착수할 수 있다.
3. 6.4.7과 동일하게, 로그인 관련 세션 정책은 한 번에 몰아 결정하기보다 실제 필요가 생겼을 때(예: 보안 요구사항이 명시적으로 들어올 때) 별도로 검토하는 편이 범위를 깔끔하게 유지한다.

## 7. 향후 앱 설계 (Notion 기능명세서 반영)

아래는 Notion "기능명세서" DB의 각 그룹을 실제로 읽고 정리한 내용이다. CRUD 성격이 뚜렷한 모델은 필드까지 제시하고, 외부 API(날씨/카카오 로컬/한국도로공사) 연동이나 AI 큐레이션처럼 "모델보다 로직이 핵심"인 기능은 연동 지점만 표시했다. **실제 구현 시에도 이 문서와 Notion 원본이 어긋나면 Notion을 기준으로 삼는다** (섹션 끝 "Notion 원문 참조" 링크로 재확인).

### 7.1 `places` — 검색·정보 그룹

Notion 페이지: 통합 검색, 관광지 혼잡도, 장소 상세, 실시간 교통 혼잡 안내

- **`Place`**: `name`, `category`(맛집/관광지/숙박/축제 중 선택), `address`, `description`, `business_hours`, `is_cultural_heritage`(문화재 여부), `latitude`/`longitude`, 대표 이미지(별도 `PlaceImage` 모델로 갤러리 지원)
- **혼잡도/교통 안내**: DB에 정적으로 저장하는 데이터가 아니라 실시간 조회 성격 (혼잡도는 자체 집계 로직 또는 외부 데이터, 교통은 한국도로공사 API 연동). 이 단계에서는 `Place`에 연동 키(예: 외부 시스템 ID)만 두고, 실제 혼잡도/교통 계산 로직은 별도 서비스 계층에서 API 연동 확정 후 설계.
- 통합 검색은 `Place`에 대한 필터링(카테고리/지역/정렬) API로 구현, 별도 모델 불필요.

### 7.2 `courses` — 추천 그룹

Notion 페이지: AI 맞춤 추천 입력, 코스 동선 최적화, 추천 코스 결과

- **`Course`**: `name`, `owner`(추천/저장한 User, null 허용 — AI 자동 생성 코스는 소유자 없을 수 있음), `duration_minutes`, `distance_km`, `recommend_reason`(AI 추천 이유 텍스트), `mood`/`companion_type`/`transport_type`(추천 입력값 기록용)
- **`CoursePlace`** (through 모델): `course` FK, `place` FK, `order`(방문 순서), `travel_time_from_prev`(구간 이동 시간 — 카카오 로컬 API 결과 캐시)
- **AI 코스 추천/동선 최적화 자체는 모델이 아니라 서비스 로직** (외부 AI/카카오 로컬 API 연동). 이 스테이지에서는 요청·응답 스키마와 `Course`/`CoursePlace` 저장 구조만 확정하고, 추천 알고리즘 연동은 별도로 설계.
- "코스 시작/완주" 상태는 `Course`에 두지 않고 사용자별 진행 기록이 필요하므로 `CourseProgress`(user FK, course FK, started_at, completed_at) 모델로 분리.

### 7.3 `reviews` — 후기·만족도 그룹

Notion 페이지: 후기 작성, 후기 목록

- **`Review`**: `user` FK, `place` FK(null 허용) 또는 `course` FK(null 허용) 중 하나만 채워지는 구조(어떤 대상 후기인지), `rating`(1~5), `content`, `visited_at`, `visited_weather`, 사진은 `ReviewImage`로 분리
- **`ReviewHelpful`**: `user` FK, `review` FK, `(user, review)` unique — "도움돼요" 버튼
- 신고("신고" 버튼)는 `ReviewReport`(user, review, reason, created_at)로 별도 모델
- "AI 예상 만족도"/키워드 요약은 저장 데이터가 아니라 리뷰 누적 데이터를 배치/집계해서 계산하는 값 — Review 모델 자체에는 필드 불필요, 별도 집계 서비스에서 처리

### 7.4 `interactions` — 찜하기(Bookmark)

Notion 페이지: 장소 상세("찜하기"), 추천 코스 결과("코스 저장"), 마이페이지("찜 목록")

- **`Bookmark`**: `user` FK, `place` FK(null 허용), `course` FK(null 허용), `(user, place)` / `(user, course)` 각각 unique. 제네릭 FK 대신 nullable FK 두 개로 구현 — Django Admin/쿼리 가독성이 더 좋고, 대상이 Place/Course 두 종류로 고정되어 있어 GenericForeignKey의 유연성이 필요 없음.
- 기존에 "Like" 모델로 임시 설계했던 것은 폐기 — Notion 명세엔 범용 좋아요가 아니라 찜하기(Bookmark)와 후기 도움돼요(ReviewHelpful) 두 가지뿐이다.

### 7.5 `gamification` — 게이미피케이션 그룹

Notion 페이지: 지역 스탬프(스탬프북), 숨겨진 여행지(Weather Unlock), 완주 카드

- **`RegionStamp`**: 전남 22개 시군 마스터 데이터 (`name`), 관리자 페이지에서 등록
- **`UserStamp`**: `user` FK, `region_stamp` FK, `acquired_at`, `(user, region_stamp)` unique — 체크인 시 생성
- **`HiddenCourse`**: `course` FK(OneToOne 또는 FK), `rarity`(LEGENDARY/RARE/UNCOMMON/COMMON), `unlock_condition`(날씨/계절/시간대 조건 — 조건 매칭 로직은 서비스 계층)
- **`UserHiddenCourseUnlock`**: `user` FK, `hidden_course` FK, `unlocked_at`
- **`CompletionCard`**: `user` FK, `course` FK, `photo`(선택), `created_at` — 완주 인증 카드, SNS 공유 링크는 저장하지 않고 요청 시 생성

### 7.6 `mypage` — 마이페이지 그룹

Notion 페이지: 마이페이지

- 자체 모델 없음. `accounts.User`, `courses.Course`/`CourseProgress`, `reviews.Review`, `interactions.Bookmark`, `gamification`을 조합해 조회 전용 API(`GET /api/v1/mypage`, `/wishlist`, `/courses`, `/reviews`)로 노출. 프로필 수정(`PATCH /api/v1/mypage/profile`)만 `accounts.User`를 갱신.

### 7.7 `home` — Home 그룹

Notion 페이지: 메인(홈)

- 자체 모델 없음. 위치·날씨(기상청 API 연동, 연동 방식은 별도 설계 필요) 기준으로 `places`/`courses` 앱의 데이터를 조회해 추천 카드를 구성하는 조회 전용 API. 날씨 API 연동 지점만 이 단계에서 인터페이스로 확정하고 실제 공급자는 이후 스테이지에서 결정.

### 7.8 `common` — 공통 그룹 (Settings)

Notion 페이지: 설정, 온보딩

- **`UserSettings`**: `user` OneToOne FK, `push_notification_enabled`, `golden_hour_notification_enabled`, `language`(한/영/일/중)
- 온보딩은 서버 상태가 없는 클라이언트 전용 화면 — 백엔드 모델/엔드포인트 불필요 (위치 권한 요청은 클라이언트 OS 레벨 처리)

### 7.9 관리자 기능

별도 앱을 만들지 않고 각 앱의 `admin.py`에서 `ModelAdmin`으로 노출하는 것을 기본으로 한다 (Django Admin 재사용).

### 7.10 Notion 원문 참조

- 기능명세서 DB: `6a504d37-4d27-821d-a919-0133884f7706`
- API 설계 페이지: `39504d37-4d27-806c-b05e-de375e0b1e6c`
- 구현 중 세부 필드가 애매하면 위 ID를 Notion MCP `fetch`/`query_data_sources`로 다시 읽어 확인한다.

## 8. 단계별 구현 계획

- **Stage 0** — Django 프로젝트 뼈대: `config/` 생성, MySQL 연결, 빈 상태로 `manage.py migrate`/`runserver` 동작 확인. 도메인 앱 없음.
- **Stage 1** — `accounts` 앱: 6절 모델/엔드포인트 구현. `common` 앱의 응답 포맷/에러 핸들러도 이 단계에서 함께 구현 (auth가 이를 바로 사용하므로).
- **Stage 2** — `places` 앱: `Place`/`PlaceImage` 모델과 통합 검색/장소 상세 API. 혼잡도·교통 연동은 외부 API 확정 전까지 인터페이스만.
- **Stage 3** — `courses` 앱: `Course`/`CoursePlace`/`CourseProgress`. AI 추천·동선 최적화 연동은 별도 스테이지로 다시 분리 검토.
- **Stage 4** — `reviews` + `interactions` 앱: `Review`/`ReviewHelpful`/`ReviewReport`, `Bookmark`.
- **Stage 5** — `gamification` 앱: `RegionStamp`/`UserStamp`/`HiddenCourse`/`UserHiddenCourseUnlock`/`CompletionCard`.
- **Stage 6** — `mypage` + `home` (조회 전용, 자체 모델 없음) + `common.UserSettings`.
- **Stage 7** — 배포 준비: settings dev/prod 분리, Dockerfile, Nginx, CI(`.github/workflows/ci.yml`) 갱신.

각 스테이지는 별도 커밋/PR 단위로 진행하고, 다음 스테이지로 넘어가기 전에 리뷰를 거친다.

## 9. 폐기 대상 (Stage 0에서 제거)

- `app/` 전체 (FastAPI 코드)
- `tests/test_api_skeleton.py`, `tests/test_auth_signup.py`, `tests/conftest.py`, `tests/test_error_response.py`, `tests/test_health.py` (Django 버전 테스트로 재작성)
- `data/eodiganam.sqlite3`
- `pyproject.toml`의 `fastapi`, `uvicorn`, `pydantic-settings`, `httpx` 의존성

`.github/workflows/ci.yml`은 Stage 1에서 pytest-django 기준으로 갱신한다 (Stage 0에서는 임시로 실패 상태를 허용하거나 스킵).
