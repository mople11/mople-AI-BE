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
│   ├── models.py                  # User(provider/provider_id 포함), EmailVerificationCode
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
- `provider` — `CharField(choices=Provider.choices, null=True, blank=True)`, choices: `google`, `kakao` (`SocialLoginSerializer.provider`와 동일). 일반(아이디/비밀번호) 가입 유저는 `null`.
- `provider_id` — `CharField(max_length=255, null=True, blank=True)`. 소셜 제공자가 내려주는 사용자 식별자(Google `sub`, Kakao `id`). 일반 가입 유저는 `null`.
- `(provider, provider_id)` — `UniqueConstraint`. 별도 `SocialAccount` 모델은 두지 않는다(6.6절 참고) — 한 유저는 최대 하나의 소셜 계정만 연결한다는 현재 스펙(가입 화면에 소셜/일반 계정 다중 연결 UI가 없음)에서는 `User`에 직접 필드를 두는 편이 조인 없이 로그인 조회가 가능해 더 단순하다. 한 유저가 여러 소셜 제공자를 연결하는 요구사항이 생기면 그때 별도 모델로 분리한다.
- 비밀번호는 Django 기본 `set_password`/`check_password` (PBKDF2, Django 기본 해셔) 사용 — 자체 해싱 구현 금지. 소셜 가입 유저는 비밀번호 로그인 경로가 없으므로 `set_unusable_password()`로 생성한다.

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
| `POST /api/v1/auth/login/social` | `social_login` | 소셜 로그인 (google/kakao, 6.6절) |
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

### 6.6 소셜 로그인 설계 (`feature/auth-social-login`)

대상은 `POST /api/v1/auth/login/social` 한 엔드포인트다. Notion "소셜 로그인" API 명세(`32804d37-4d27-837b-9dba-81d8e278df9e`) 기준으로 `provider`는 `google`/`kakao` 두 값만 허용한다 — 회원가입 화면 UI 명세에 남아있는 "깃허브로 가입" 문구는 스테일로 판단하고 이번 구현 범위에서 제외한다(0절 원칙 2).

#### 6.6.1 인증 흐름

```
클라이언트가 Google/Kakao SDK로 발급받은 토큰(oauthToken)
    ↓
POST /api/v1/auth/login/social { provider, oauthToken }
    ↓
provider별 토큰 검증 (accounts/google.py 또는 accounts/kakao.py)
    ↓
(provider, provider_id)로 회원 조회 → 있으면 그 유저로 로그인
    ↓ (없으면)
동일 email의 기존 계정 존재 여부 확인
    → 있으면 SOCIAL_EMAIL_CONFLICT(409)
    → 없으면 신규 User 생성(자동 회원가입)
    ↓
RefreshToken.for_user(user)로 JWT 발급
```

Google/Kakao 연동 로직을 각각 `accounts/google.py`/`accounts/kakao.py`로 분리해 뷰가 검증 방식의 세부사항(서명 검증 라이브러리, 외부 API 호출)을 알 필요가 없게 한다 — 참고한 사내 설계 문서("Google OAuth와 자체 JWT 인증 연동 설계")의 책임 분리 방향을 그대로 따른다. 회원 조회/생성은 `accounts/services.py`의 `find_or_create_social_user`가 담당하고, JWT 발급은 기존 로그인(6.4절)과 동일하게 `RefreshToken.for_user()`를 재사용한다.

#### 6.6.2 `accounts/google.py` — Google ID Token 검증

`google-auth` 패키지의 `google.oauth2.id_token.verify_oauth2_token()`을 사용한다. 이 함수가 다음을 한 번에 수행하므로 서명 검증을 직접 구현하지 않는다(0절 원칙 3):

- Google의 공개키(JWKS)로 토큰 서명을 검증
- `aud` 클레임이 `settings.GOOGLE_CLIENT_ID`와 일치하는지 확인
- `iss`, `exp` 등 표준 클레임 검증

검증 실패(서명 불일치, `aud` 불일치, 만료 등)는 모두 `ValueError`/`GoogleAuthError`로 올라오므로 `ApiError(ErrorCode.OAUTH_FAILED)`로 변환한다. 검증에 성공하면 클레임에서 `sub`(→ `provider_id`), `email`, `name`(→ `nickname`, 없으면 이메일 로컬파트로 대체)을 추출해 반환한다. `sub` 또는 `email`이 없거나 `email_verified`가 `true`가 아니면 Google이 신뢰할 수 있는 계정 식별 정보로 간주하지 않고 `OAUTH_FAILED`로 처리한다.

#### 6.6.3 `accounts/kakao.py` — Kakao 사용자 조회

Kakao는 ID Token이 아니라 클라이언트가 카카오 SDK로 발급받은 액세스 토큰을 그대로 넘겨받는다. 이 토큰으로 `GET https://kapi.kakao.com/v2/user/me`를 `Authorization: Bearer {oauthToken}` 헤더로 호출해 사용자 정보를 조회하는 것 자체가 토큰 검증이다(호출이 401이면 유효하지 않은 토큰).

**이메일이 없는 경우(placeholder 이메일)**: 원래는 `kakao_account.email`이 없으면 `OAUTH_FAILED`로 처리할 계획이었으나, 실제 앱으로 검증하는 과정(6.6.9절)에서 카카오의 `account_email` 동의항목이 **사업자 등록이 없는 계정은 신청 자격 자체가 없다**는 것이 확인되어 방침을 변경했다. 이메일이 없으면 실패시키는 대신 `kakao_{provider_id}@users.eodiganam.local` 형태의 placeholder 이메일을 생성해 정상적으로 가입을 진행한다. `provider_id`가 카카오 계정별로 유니크하므로 이 placeholder도 자동으로 유니크하다 — 다른 유저의 이메일과 충돌할 일이 없고(`SOCIAL_EMAIL_CONFLICT` 오탐 없음), 실제 사용자 이메일 주소가 아니므로 이 계정에는 이메일 발송 기반 기능(비밀번호 재설정 등)이 동작하지 않는다는 한계는 있다. `nickname`도 마찬가지로 `kakao_account.profile.nickname`이 없으면(닉네임 동의항목도 별도로 켜야 함) `카카오사용자{provider_id 뒤 6자리}` 형태로 대체한다.

`KAKAO_REST_API_KEY`는 이번 호출(`/v2/user/me`)에는 사용하지 않는다 — 이 엔드포인트는 사용자 액세스 토큰만으로 인증되고, REST API 키는 인가 코드 교환 등 별도 흐름에서 필요하다. 다만 이후 카카오 로컬 API(7.2절 코스 동선 최적화) 연동 등에서 재사용할 것을 감안해 `.env`에 자리만 미리 마련해 둔다.

#### 6.6.4 에러 코드 추가

| 코드 | 상태코드 | 메시지 | 발생 조건 |
|---|---|---|---|
| `OAUTH_FAILED` | 401 | 소셜 인증에 실패했습니다. | Google ID Token 서명/`aud` 검증 실패(이메일 클레임 없음 포함), 또는 Kakao `/v2/user/me` 호출 실패(401 등, 유효하지 않은 액세스 토큰) |
| `SOCIAL_EMAIL_CONFLICT` | 409 | 이미 가입된 이메일과 연결된 계정입니다. | 신규 소셜 로그인 시도 시 동일 `email`의 `User`가 이미 존재(다른 provider 또는 일반 가입)하는 경우 |

**이메일 충돌을 자동 연결하지 않고 에러로 처리하는 이유**: Kakao는 이메일 소유권을 검증하지 않고 카카오 계정에 등록된 이메일을 그대로 내려줄 수 있어, 이미 가입된 이메일에 소셜 로그인을 자동으로 연결하면 계정 탈취(account takeover) 경로가 생긴다. 프론트에는 `SOCIAL_EMAIL_CONFLICT`를 받으면 기존 계정으로 로그인하도록 안내하는 것을 권장하되, 그 UX 처리는 이번 백엔드 구현 범위 밖이다.

#### 6.6.5 `find_or_create_social_user` (`accounts/services.py`)

```python
def find_or_create_social_user(*, provider, provider_id, email, nickname) -> User:
    try:
        return User.objects.get(provider=provider, provider_id=provider_id)
    except User.DoesNotExist:
        pass

    if User.objects.filter(email=email).exists():
        raise ApiError(ErrorCode.SOCIAL_EMAIL_CONFLICT)

    username = f"{provider}_{provider_id}"
    if len(username) > 150:
        username = f"{provider}_{sha256(provider_id.encode()).hexdigest()}"

    user = User(
        username=username,
        email=email,
        nickname=nickname[:50],
        provider=provider,
        provider_id=provider_id,
    )
    user.set_unusable_password()
    user.save()
    return user
```

- 신규 가입 시 `username`은 `signup`처럼 클라이언트가 지정하지 않으므로 `{provider}_{provider_id}` 형식으로 자동 생성한다. 150자를 넘는 비정상적으로 긴 provider ID는 조용히 잘라 충돌시키지 않고 SHA-256 해시 기반 username으로 대체한다.
- 외부 제공자가 내려준 닉네임은 `User.nickname`의 최대 길이인 50자로 제한해 DB 저장 단계에서 길이 초과 오류가 발생하지 않게 한다.
- `(provider, provider_id)` 조회와 `email` 중복 체크 사이의 레이스(동시에 같은 계정으로 두 번 로그인)로 `IntegrityError`가 나면 `(provider, provider_id)`로 재조회해 이미 생성된 유저를 반환한다. 그 외에는 username과 email 충돌을 각각 재확인해 `DUPLICATE_ID` 또는 `SOCIAL_EMAIL_CONFLICT`로 구분하고, 알려진 충돌이 아니면 원본 예외를 다시 발생시킨다.

#### 6.6.6 응답

`POST /auth/login/social` 응답은 로그인(6.4.3절) `AuthTokenResponse`와 동일한 형태를 그대로 재사용한다(별도 스키마 없음).

```json
{
  "success": true,
  "data": {
    "accessToken": "eyJ...",
    "refreshToken": "eyJ...",
    "user": { "id": "google_1029384756", "nickname": "여행자" }
  },
  "error": null
}
```

#### 6.6.7 환경 변수

```
GOOGLE_CLIENT_ID=change-me-in-env
KAKAO_REST_API_KEY=change-me-in-env
```

이번 이슈 시점에는 실제 Google/Kakao 클라이언트 ID가 아직 발급되지 않아 `.env.example`에 placeholder만 추가한다. `GOOGLE_CLIENT_ID`가 비어 있으면 `verify_oauth2_token`의 `aud` 검증이 항상 실패해 모든 Google 로그인 요청이 `OAUTH_FAILED`가 되므로, 실제 값 발급 전에는 Google 소셜 로그인이 정상 동작하지 않는다(테스트는 검증 함수 자체를 mock 처리하므로 영향받지 않는다). 실제 값 발급 후 통합 스모크 테스트는 별도 후속 작업으로 남긴다.

#### 6.6.8 테스트 관점 (`tests/test_auth_social_login.py`, 신규)

API 흐름 테스트에서는 `accounts.views.verify_google_id_token`/`accounts.views.verify_kakao_token`을 mock 처리한다. 검증 함수 자체의 테스트에서는 Google의 `id_token.verify_oauth2_token`과 Kakao의 `requests.get`처럼 실제 외부 통신 지점만 mock 처리해 클레임 및 응답 파싱 로직을 직접 실행한다.

- Google 로그인 성공 — 신규 `provider_id`: 응답에 `accessToken`/`refreshToken`/`user`가 있고, `User.objects.get(provider="google", provider_id=...)`가 생성되어 있으며 `has_usable_password()`가 `False`인지 확인.
- Google 로그인 성공 — 이미 연결된 `provider_id`: 새 유저를 만들지 않고 기존 유저로 로그인되는지 확인(생성 건수 비교).
- Google 로그인 실패 — 토큰 검증 실패: `OAUTH_FAILED`, 401.
- Google 로그인 실패 — `sub`/`email` 누락 또는 `email_verified=false`: `OAUTH_FAILED`, 401.
- Google 로그인 실패 — 동일 이메일의 기존(일반 가입) 계정 존재: `SOCIAL_EMAIL_CONFLICT`, 409.
- Kakao 로그인 성공 — 신규 `provider_id`.
- Kakao 로그인 성공 — `kakao_account.email` 없음(이메일 동의항목 미승인 상태): 실패하지 않고 `kakao_{provider_id}@users.eodiganam.local` placeholder 이메일로 가입되는지 확인.
- Kakao 로그인 — 같은 `provider_id`로 이메일 없이 재로그인: placeholder 이메일 계정이 중복 생성되지 않고 재사용되는지 확인.
- Kakao 로그인 실패 — `/v2/user/me` 호출이 200이 아님: `OAUTH_FAILED`, 401.
- Kakao 로그인 실패 — 네트워크 오류, JSON 파싱 실패 또는 `id` 누락: `OAUTH_FAILED`, 401.
- `provider`에 `google`/`kakao` 이외 값(예: `github`) 요청 시 `COMMON_422`.

#### 6.6.9 실제 Kakao 앱으로 검증한 결과 (2026-07-30)

Kakao REST API 키(`eodiganam` 앱)를 발급받아 실제 카카오 서버로 수동 스모크 테스트를 진행했다.

- 인가 코드 요청(`kauth.kakao.com/oauth/authorize`) → 코드 → 액세스 토큰 교환(`kauth.kakao.com/oauth/token`)까지는 정상 동작 확인.
- **`/v2/user/me` 응답에 `kakao_account`가 아예 오지 않음** — 이 앱의 "동의항목"에서 `account_email`(카카오계정 이메일) 상태가 "미연동"이고 [설정] 버튼조차 없기 때문. 닉네임/프로필사진/친구목록과 달리 이메일·전화번호·생일·성별 등은 Kakao 문서(`docs/ko/kakaologin/prerequisite#additional-features`) 기준 **비즈 앱 전환 + 사업자 정보 심사를 마쳐야 "추가 기능 신청" 자체가 가능**하고, 신청 후에도 영업일 3~5일 심사가 필요하다. **사업자 등록이 불가능한 학교 프로젝트 계정이라 이메일 동의항목 신청 자격 자체가 없다** — "언젠가 승인받으면"이 아니라 이 프로젝트 범위에서는 구조적으로 막혀 있다.
- 처음엔(방침 변경 전) 이 실제 토큰으로 `POST /api/v1/auth/login/social`(`provider=kakao`)을 호출해 `OAUTH_FAILED`(401)가 반환되는 것까지 확인했었다. 하지만 이메일 동의가 원천적으로 불가능하다는 게 확정된 이상, 원래 완료조건("Kakao 이메일 누락 시 OAUTH_FAILED")대로 두면 **이 서비스에서 카카오 로그인은 어떤 실사용자도 쓸 수 없는 기능**이 된다. 그래서 6.6.3절과 같이 이메일 누락 시 실패 대신 placeholder 이메일로 가입을 진행하도록 방침을 바꿨다 — Notion 명세에는 없는 결정이지만, 사업자 인증 불가라는 확인된 제약 위에서 기능을 실제로 동작시키기 위한 의도적 변경이다(0절 원칙 2의 "없는 스펙을 임의로 만들지 않는다"와는 별개로, 이미 있는 스펙이 실행 불가능함을 확인하고 대체 경로를 마련한 경우).
- 방침 변경 후 실제 토큰으로 재검증하려 했으나, 그 사이 사용자가 카카오톡 앱에서 `eodiganam` 연결을 끊어 토큰이 만료(`this access token does not exist`)되어 재시도하지 못했다. 대신 유닛 테스트(`test_kakao_login_missing_email_still_signs_up_with_placeholder_email` 등, 6.6.8절)가 실제로 관찰된 응답 형태(`kakao_account` 키 자체가 없음)를 그대로 mock해 동일 동작을 검증한다.

#### 6.6.10 미해결 사항 (이번 브랜치 범위 밖)

- placeholder 이메일 계정은 이메일 발송 기반 기능(비밀번호 재설정 등)을 쓸 수 없다 — 필요해지면 소셜 전용 계정에 대한 별도 안내/UX를 정의해야 한다.
- 닉네임 동의항목(`profile_nickname`)은 심사 없이 켤 수 있으므로, 실제 배포 전에 콘솔에서 활성화해두면 `카카오사용자{id}` 대신 실제 닉네임이 표시된다 — 코드 변경은 필요 없고 콘솔 설정만 남은 작업.
- 실제 Google 클라이언트 ID 발급 후 통합 스모크 테스트(6.6.7절).
- 한 유저가 여러 소셜 제공자를 동시에 연결하는 시나리오(현재는 `User`당 `(provider, provider_id)` 하나) — 필요해지면 6.1절에서 언급한 대로 별도 `SocialAccount` 모델로 분리 검토.
- `SOCIAL_EMAIL_CONFLICT` 발생 시 기존 계정에 소셜 로그인을 연결(link)하는 플로우(예: 비밀번호 재확인 후 연결) — Notion 명세에 없으므로 임의로 추가하지 않는다.

## 7. 향후 앱 설계 (Notion 기능명세서 반영)

아래는 Notion "기능명세서" DB의 각 그룹을 실제로 읽고 정리한 내용이다. CRUD 성격이 뚜렷한 모델은 필드까지 제시하고, 외부 API(날씨/카카오 로컬/한국도로공사) 연동이나 AI 큐레이션처럼 "모델보다 로직이 핵심"인 기능은 연동 지점만 표시했다. **실제 구현 시에도 이 문서와 Notion 원본이 어긋나면 Notion을 기준으로 삼는다** (섹션 끝 "Notion 원문 참조" 링크로 재확인).

### 7.1 `places` — 검색·정보 그룹

Notion 페이지: 통합 검색, 관광지 혼잡도, 장소 상세, 실시간 교통 혼잡 안내

- **`Place`**: `name`, `category`(맛집/관광지/숙박/축제 중 선택), `address`, `description`, `business_hours`, `is_cultural_heritage`(문화재 여부), `latitude`/`longitude`, 대표 이미지(별도 `PlaceImage` 모델로 갤러리 지원)
- **혼잡도/교통 안내**: DB에 정적으로 저장하는 데이터가 아니라 실시간 조회 성격 (혼잡도는 자체 집계 로직 또는 외부 데이터, 교통은 한국도로공사 API 연동). 이 단계에서는 `Place`에 연동 키(예: 외부 시스템 ID)만 두고, 실제 혼잡도/교통 계산 로직은 별도 서비스 계층에서 API 연동 확정 후 설계.
- 통합 검색은 `Place`에 대한 필터링(카테고리/지역/정렬) API로 구현, 별도 모델 불필요.

### 7.2 `courses` — 추천 그룹

Notion 페이지: AI 맞춤 추천 입력, 코스 동선 최적화, 추천 코스 결과

- **`Course`**: `name`, `owner`(추천/저장한 User, null 허용 — AI 자동 생성 코스는 소유자 없을 수 있음), `duration_minutes`, `distance_km`, `recommend_reason`(AI 추천 이유 텍스트), `mood`/`companion_type`/`transport_type`(추천 입력값 기록용), `status`(`TEMP`/`SAVED`, 실제 구현에 반영됨)
- **`CoursePlace`** (through 모델): `course` FK, `place` FK, `order`(방문 순서), `travel_time_from_prev`(구간 이동 시간 — 카카오 로컬 API 결과 캐시)
- **AI 코스 추천/동선 최적화 자체는 모델이 아니라 서비스 로직** (외부 AI/카카오 로컬 API 연동). 이 스테이지에서는 요청·응답 스키마와 `Course`/`CoursePlace` 저장 구조만 확정하고, 추천 알고리즘 연동은 별도로 설계.
- "코스 시작/완주" 상태는 `Course`에 두지 않고 사용자별 진행 기록이 필요하므로 `CourseProgress`(user FK, course FK, started_at, completed_at) 모델로 분리.

**실행 상세 설계**는 이슈 단위로 아래에 따로 정리한다:
- 저장/시작/완주인증/공유(`feature/courses-base`) — **완료**, 7.12절.
- AI 맞춤 추천(`feature/courses-recommend`) — **완료**, 7.13절.
- 코스 동선 최적화(`feature/courses-optimize`) — 7.14절.

### 7.3 `reviews` — 후기·만족도 그룹

Notion 페이지: 후기 작성, 후기 목록

- **`Review`**: `user` FK, `place` FK(null 허용) 또는 `course` FK(null 허용) 중 하나만 채워지는 구조(어떤 대상 후기인지), `rating`(1~5), `content`, `visited_at`, `visited_weather`, 사진은 `ReviewImage`로 분리
- **`ReviewHelpful`**: `user` FK, `review` FK, `(user, review)` unique — "도움돼요" 버튼
- 신고("신고" 버튼)는 `ReviewReport`(user, review, reason, created_at)로 별도 모델
- "AI 예상 만족도"/키워드 요약은 저장 데이터가 아니라 리뷰 누적 데이터를 배치/집계해서 계산하는 값 — Review 모델 자체에는 필드 불필요, 별도 집계 서비스에서 처리

**실행 상세 설계는 착수 시 7.15절에 작성한다**(`feature/reviews`) — API spec/ERD를 다시 확인한 결과 `targetId` 단일 필드로 대상 종류가 모호한 지점 등 착수 전 재확인이 필요한 사항이 있다(`docs/roadmap.md` 5절).

### 7.4 `interactions` — 찜하기(Bookmark)

Notion 페이지: 장소 상세("찜하기"), 추천 코스 결과("코스 저장"), 마이페이지("찜 목록")

- **`Bookmark`**: `user` FK, `place` FK, `(user, place)` unique. API spec 재확인 결과 찜 엔드포인트는 `POST /places/{placeId}/like` 하나뿐이고 코스 찜은 없어(ERD `wishlists`도 장소만 가짐) **장소 전용**으로 확정했다(`docs/roadmap.md` 5절). 코스 저장은 Stage 3의 `CourseProgress.status=SAVED`가 이미 담당한다.
- 기존에 "Like" 모델로 임시 설계했던 것은 폐기.

**실행 상세 설계는 착수 시 7.16절에 작성한다**(`feature/interactions-bookmark`).

### 7.5 `gamification` — 게이미피케이션 그룹

Notion 페이지: 지역 스탬프(스탬프북), 숨겨진 여행지(Weather Unlock), 완주 카드

- **`RegionStamp`**: 전남 22개 시군 마스터 데이터 (`name`), 관리자 페이지에서 등록 — *착수 시 재검토: ERD/API spec 재확인 결과 마스터 테이블 없이 `Stamp.city_code`를 choices로 직접 쓰는 쪽이 계약과 더 맞는다(`docs/roadmap.md` 5절).*
- **`UserStamp`**: `user` FK, `region_stamp` FK, `acquired_at`, `(user, region_stamp)` unique — 체크인 시 생성
- **`HiddenCourse`**: `course` FK(OneToOne 또는 FK), `rarity`(LEGENDARY/RARE/UNCOMMON/COMMON), `unlock_condition`(날씨/계절/시간대 조건 — 조건 매칭 로직은 서비스 계층). **API 재확인 결과 이 방향(코스 단위)이 맞다고 확정됨** — `GET /courses/unlocked`가 `courseId`/`rarity`로 응답한다(`docs/roadmap.md` 5절).
- **`UserHiddenCourseUnlock`**: `user` FK, `hidden_course` FK, `unlocked_at`
- **`CompletionCard`**: `user` FK, `course` FK, `photo`(선택), `created_at` — 완주 인증 카드, SNS 공유 링크는 저장하지 않고 요청 시 생성. **API 재확인 결과 course 단위가 맞다고 확정됨**(`POST /cards/completion`이 `courseId` 필수, `GET /cards` 응답에 `courseName`).

**실행 상세 설계는 착수 시 7.17절에 작성한다**(`feature/gamification`).

### 7.6 `mypage` — 마이페이지 그룹

Notion 페이지: 마이페이지

- 자체 모델 없음. `accounts.User`, `courses.Course`/`CourseProgress`, `reviews.Review`, `interactions.Bookmark`, `gamification`을 조합해 조회 전용 API(`GET /users/me`, `/users/me/courses`, `/users/me/reviews`, `/users/me/likes`)로 노출. 프로필 수정(`PATCH /users/me`)만 `accounts.User`를 갱신.
- **착수 전 중요 확인 사항**: `PATCH /users/me`가 요구하는 `profileImg`/`NICKNAME_DUPLICATE` 검증을 위해, 이미 머지된 `accounts.User`(Stage 1)에 `profile_img` 필드 추가 + `nickname` `unique=True` 마이그레이션이 필요하다. 기존 DB에 중복 닉네임이 있으면 마이그레이션이 실패하므로 착수 전 확인 필요(`docs/roadmap.md` 4절 Stage 6).

**실행 상세 설계는 착수 시 7.18절에 작성한다**(`feature/mypage`).

### 7.7 `home` — Home 그룹

Notion 페이지: 메인(홈)

- 자체 모델 없음. 위치·날씨(기상청 API 연동, 연동 방식은 별도 설계 필요) 기준으로 `places`/`courses` 앱의 데이터를 조회해 추천 카드를 구성하는 조회 전용 API(`GET /weather/current`, `GET /home`). 둘 다 `authorization: none`. `home`은 `courses`(Stage 3)·`gamification`(Stage 5)에 의존하므로 그 두 Stage 완료 후 완전한 형태로 구현 가능하다.

**실행 상세 설계는 착수 시 7.19절에 작성한다**(`feature/home`).

### 7.8 `common` — 공통 그룹 (Settings)

Notion 페이지: 설정, 온보딩

- **`UserSettings`**: `user` OneToOne FK, `push_notification_enabled`, `golden_hour_notification_enabled`, `language`(한/영/일/중), `location_permission_granted`(API 재확인 결과 응답에 `permissions.location`이 있어 추가 확인됨). 응답은 `notifications`/`permissions`로 중첩된 구조다(`docs/roadmap.md` 5절).
- 온보딩은 서버 상태가 없는 클라이언트 전용 화면 — 백엔드 모델/엔드포인트 불필요 (위치 권한 요청은 클라이언트 OS 레벨 처리)

**실행 상세 설계는 착수 시 7.20절에 작성한다**(`feature/common-settings`).

### 7.9 관리자 기능

별도 앱을 만들지 않고 각 앱의 `admin.py`에서 `ModelAdmin`으로 노출하는 것을 기본으로 한다 (Django Admin 재사용).

### 7.10 Notion 원문 참조

- 기능명세서 DB: `6a504d37-4d27-821d-a919-0133884f7706`
- API 설계 페이지: `39504d37-4d27-806c-b05e-de375e0b1e6c`
- 구현 중 세부 필드가 애매하면 위 ID를 Notion MCP `fetch`/`query_data_sources`로 다시 읽어 확인한다.

### 7.11 `places` 앱 상세 설계 (Stage 2 실행용, GitHub 이슈 #12 기준 재설계)

> **개정 이력**: 이전 버전은 통합 검색·장소 상세 2개 엔드포인트만 다루고 혼잡도·교통은 제외했었다. GitHub 이슈 #12(`mople11/mople-AI-BE#12`, "[Feature] 검색·장소 정보 API 구현")가 Notion "검색·정보" 그룹 4개 페이지 전체를 요구 범위로 지정했고, 사용자가 "이슈 #12대로 다시 설계"를 명시적으로 지시해 이번 개정으로 대체한다. 아래는 처음부터 다시 쓴 버전이며, 이전 버전의 결정(TourAPI write-through 캐시 등) 중 유효한 것은 유지하고 나머지는 갱신했다.

이번 스테이지 범위는 Notion "검색·정보" 그룹 **4개 페이지 전부**다: **통합 검색**(`/search`), **장소 상세**(`/places/{placeId}`), **관광지 혼잡도**(`/places/{placeId}/congestion`), **실시간 교통 혼잡 안내**(`/traffic/congestion`). 아래 요청/응답 필드는 Notion API spec 페이지(각 페이지 ID는 7.10 참고 대신 아래 표로 대체 — 통합 검색 `a3204d37-4d27-83b0-b1b8-8131101c7f05`, 장소 상세 `c3204d37-4d27-821e-af59-81263fd33f1b`, 관광지 혼잡도 `9a104d37-4d27-83ab-8542-01f809bdf151`, 실시간 교통 혼잡 안내 `19604d37-4d27-8269-8969-81efe22666e2`)를 그대로 옮긴 것이다.

#### 7.11.1 외부 API 매핑 및 데이터 소스 결정

세 개의 서로 다른 외부 API를 쓴다. 매핑은 이슈 #12 기준으로 확정한다.

| 기능 | 외부 API | 비고 |
|---|---|---|
| 통합 검색 / 장소 상세 | 한국관광공사 TourAPI | 실시간 호출 + 로컬 write-through 캐시(아래 근거 참고) |
| 관광지 예상 방문 집중도 | 한국관광공사 관광지 집중률 방문자 추이 예측 API | KT 이동통신 데이터 기반 향후 30일 집중률을 사용한다. 실시간·시간대별 데이터가 아니므로 API와 화면에서 "예상 방문 집중도"로 명시한다. |
| 실시간 교통 혼잡 안내 | 카카오모빌리티 길찾기 API | 경로별 예상 시간, 도로별 교통 상태와 대안 경로를 사용한다. Notion 원문의 "한국도로공사" 연동 지점은 카카오모빌리티로 정정한다. |

**TourAPI는 write-through 캐시를 유지한다** (이전 버전 §7.11.1의 결정을 그대로 승계):

1. Stage 3 이후(`Course`/`Review`/`Bookmark`/게이미피케이션)가 이미 로컬 장소 FK를 전제로 설계돼 있어, 안정적인 로컬 PK(`placeId`)가 필요하다.
2. "실시간 연동"은 사전 대량 시딩을 하지 않고 조회 시점에 최신 데이터를 반영한다는 뜻으로 해석하며, 로컬 저장 자체를 금지하지 않는다.
3. 검색/상세 모두 매 요청마다 TourAPI를 호출해 항상 최신 데이터를 보여주고, 로컬 테이블은 "이미 조회된 장소의 안정적 앵커" 역할만 한다.

**관광지 집중률 / 카카오모빌리티는 로컬 캐시를 두지 않는다.** 집중률 예측과 교통 데이터는 외부 API의 최신 응답을 사용한다. 외부 데이터가 없거나 호출에 실패하면 기존 계약대로 HTTP 200과 빈 `data`를 반환한다.

#### 7.11.2 모델

**`TouristSpot`** (이전 버전의 `Place`를 대체하는 이름 — 이슈 #12 지시 그대로)

| 필드 | 타입 | 비고 |
|---|---|---|
| `content_id` | `CharField`, unique | TourAPI `contentid`. 로컬 캐시 upsert의 조회 키 |
| `name` | `CharField` | |
| `category` | `CharField`, choices | `ATTRACTION`(관광지)/`RESTAURANT`(맛집)/`LODGING`(숙박)/`FESTIVAL`(축제). TourAPI `contenttypeid` → 매핑은 어댑터에서 변환(7.11.3). API 응답 시에는 한글 라벨(`get_category_display()`)로 직렬화해 통합 검색 요청의 `category` 파라미터 값("맛집|관광지|숙박|축제")과 어휘를 맞춘다 |
| `address` | `CharField` | |
| `description` | `TextField` | TourAPI 공통정보의 개요(overview) |
| `hours` | `CharField`, blank 허용 | TourAPI 소개정보. 콘텐츠 타입별로 원본 필드명이 다르므로 어댑터에서 정규화. Notion 응답 필드명이 `hours`이므로 그대로 맞춘다 |
| `latitude` / `longitude` | `DecimalField` | TourAPI `mapy`/`mapx` |
| `sigungu` | `CharField`, blank 허용 | 통합 검색의 `region` 필터링용 내부 필드. 전남 시군 이름, 응답 필드로 노출하지 않는다 |
| `parking_available` | `BooleanField(null=True, blank=True)` | TourAPI 소개정보(`detailIntro2`)에서 파싱. 정보가 없으면 `None`(→ 응답에서 `null`). 관광지 혼잡도 응답의 `parkingAvailable`에만 쓰인다 — 장소 상세 응답에는 노출하지 않는다(Notion 장소 상세 계약에 이 필드가 없음) |
| `synced_at` | `DateTimeField` | 마지막 TourAPI upsert 시각 |

이전 버전에 있던 `is_cultural_heritage` 필드는 제거했다 — Notion 응답 계약 어디에도 없는, 근거 없이 추가했던 필드였다(0절 원칙 2 위반이라 이번에 정리).

**`TouristSpotImage`** (이전 버전 `PlaceImage`와 동일한 구조, FK만 이름 변경)

| 필드 | 타입 | 비고 |
|---|---|---|
| `spot` | FK to `TouristSpot` | |
| `image_url` | `URLField` | TourAPI가 내려주는 이미지 URL을 그대로 저장(파일 업로드 아님) |
| `is_primary` | `BooleanField(default=False)` | |
| `order` | `PositiveSmallIntegerField(default=0)` | TourAPI `detailImage` 응답 순서를 그대로 따른다 |

혼잡도·교통 데이터는 별도 모델을 만들지 않는다 — 매 요청 실시간(mock) 호출 결과를 그대로 응답할 뿐, DB에 저장할 근거가 없다.

#### 7.11.3 외부 API 어댑터 3종

- **`places/tourapi.py` — `TourApiClient`**
  - `requests`를 새 의존성으로 추가(`pyproject.toml`).
  - 환경변수(`.env.example`): `TOUR_API_BASE_URL`, `TOUR_API_SERVICE_KEY`, `TOUR_API_TIMEOUT_SEC`(기본 5).
  - 메서드: `search_spots(*, keyword=None, category=None, sigungu=None) -> list[RawSpot]`, `get_spot_detail(*, content_id: str) -> RawSpot | None`(공통정보+소개정보(`detailIntro2`, 주차장 필드 파싱 포함)+이미지정보 조합).
  - KorService2의 `detailCommon2`/`detailImage2`는 KorService1용 선택 파라미터(`defaultYN`, `firstImageYN`, `areacodeYN`, `catcodeYN`, `addrinfoYN`, `mapinfoYN`, `overviewYN`, `subImageYN`)를 보내면 `INVALID_REQUEST_PARAMETER_ERROR`를 반환한다. 따라서 해당 파라미터는 보내지 않으며, `overview`를 포함한 공통 필드는 기본 응답으로 받는다.
  - 정확한 엔드포인트·파라미터·응답 필드명은 이 문서에서 확정하지 않는다 — 공식 문서로 최종 확인 후 이 어댑터 안에만 캡슐화한다. 조회 범위는 전남(area code) 한정.
  - 호출 실패(타임아웃·5xx·파싱 오류)는 `TourApiError`를 던지고, 서비스 계층에서 `ApiError(ErrorCode.EXTERNAL_API_ERROR)`로 변환(7.11.4).
- **`places/tourist_congestion.py` — `TouristCongestionClient`**
  - 한국관광공사 `TatsCnctrRateService/tatsCnctrRatedList`를 호출한다.
  - 관광지명과 전남 시군구 법정동 코드를 전달하고, 첫 날짜의 집중률과 향후 30일 중 집중률이 가장 낮은 추천일을 반환한다.
  - 집중률은 34 미만 `여유`, 67 미만 `보통`, 그 이상 `혼잡`으로 변환한다.
- **`places/kakao_mobility.py` — `KakaoMobilityClient`**
  - 메서드: `get_traffic(*, origin: tuple[float, float], destination: tuple[float, float]) -> TrafficData | None`.
  - 카카오모빌리티 Directions API를 호출해 기본 경로의 도로별 교통 상태와 ETA, 대안 경로 ETA를 반환한다.

#### 7.11.4 에러 코드

| 코드 | 상태코드 | 메시지 | 발생 조건 |
|---|---|---|---|
| `EXTERNAL_API_ERROR` | 502 | 외부 정보를 불러오지 못했습니다. | TourAPI 호출 타임아웃/5xx/응답 파싱 실패(검색·상세에만 해당) |
| `PLACE_NOT_FOUND` | 404 | 장소 정보를 찾을 수 없습니다. | 장소 상세·관광지 혼잡도 조회 시 로컬 `placeId`가 없거나, 상세의 경우 TourAPI에 해당 `content_id`가 더 이상 존재하지 않음 |

**`CONGESTION_DATA_UNAVAILABLE`, `TRAFFIC_DATA_UNAVAILABLE`은 `ApiError`로 만들지 않는다.** 둘 다 HTTP 200 + 빈 `data`로 응답해야 하는 정상 케이스이므로, 클라이언트가 `None`을 반환하면 뷰에서 `ApiResponse(data={})`로 처리한다.

#### 7.11.5 서비스 계층 (`places/services.py`)

- `search_spots(*, keyword, category, region) -> list[TouristSpot]`
  1. `TourApiClient.search_spots(...)` 호출(카테고리 한글 라벨 → `contenttypeid` 변환은 어댑터 책임).
  2. 각 결과를 `TouristSpot.objects.update_or_create(content_id=raw.content_id, defaults={...})`로 upsert, 대표 이미지 1장만 `TouristSpotImage`(`is_primary=True`)로 upsert.
  3. `sort`는 TourAPI 기본 정렬을 패스스루(7.11.8). 페이지네이션 파라미터는 Notion 계약에 없으므로 이번 스테이지는 노출하지 않는다(7.11.8).
- `get_spot_detail(*, place_id: int, user_lat=None, user_lng=None) -> tuple[TouristSpot, float | None]`
  1. 로컬 `TouristSpot`을 `place_id`로 조회(없으면 `PLACE_NOT_FOUND`) → `content_id` 확보.
  2. 항상 `TourApiClient.get_spot_detail(content_id=...)`를 실시간 호출. `None`이면(TourAPI에서 사라진 콘텐츠) `PLACE_NOT_FOUND`.
  3. 받은 상세로 `TouristSpot`/`TouristSpotImage`(전체 갤러리) upsert.
  4. `user_lat`/`user_lng`가 모두 주어지면 `calculate_distance_km`로 계산, 아니면 `None`.
- `get_congestion(*, place_id: int) -> tuple[TouristSpot, CongestionData | None]`
  1. 로컬 `TouristSpot`을 `place_id`로 조회(없으면 `PLACE_NOT_FOUND` — 장소 자체가 없는 것과 "혼잡도 데이터가 없는 것"은 다른 케이스로 구분).
  2. `TouristCongestionClient.get_forecast(spot_name=..., sigungu=...)` 호출. 결과와 `TouristSpot.parking_available`을 뷰에서 조합한다. `parkingAvailable`은 집중률 API가 아니라 로컬 TourAPI 캐시값에서 채운다.
- `get_traffic_congestion(*, origin, destination) -> TrafficData | None`
  - 좌표 자체를 다루므로 로컬 장소 조회가 필요 없다. `KakaoMobilityClient.get_traffic(...)`을 그대로 호출.
- `calculate_distance_km(lat1, lng1, lat2, lng2) -> float` — haversine 공식.

#### 7.11.6 엔드포인트

4개 엔드포인트가 하나의 URL prefix 아래 있지 않다(`/search`, `/places/{id}`, `/places/{id}/congestion`, `/traffic/congestion`). `config/urls.py`에는 이미 `path("", include("places.urls"))`로 루트 마운트가 되어 있으므로, `places/urls.py` 안에서 각 경로를 `api/v1/...` 형태로 전부 직접 명시한다. 뷰는 `accounts`와 동일하게 `APIView` 기반, `permission_classes = [AllowAny]`(Notion `authorization: none`).

**`GET /api/v1/search`** — query: `keyword`, `category`(맛집/관광지/숙박/축제), `region`, `sort` — 전부 선택

```json
{
  "success": true,
  "data": {
    "results": [
      { "id": 1, "name": "...", "category": "관광지", "location": "...", "rating": 0, "thumbnail": "https://..." }
    ]
  },
  "error": null
}
```

`id`는 로컬 `TouristSpot` PK — 이후 `/places/{placeId}` 등에서 쓰는 값과 동일하다(Notion 명세엔 그냥 "id"라고만 돼 있지만, 다른 3개 엔드포인트의 `placeId`와 같은 값이어야 검색→상세 흐름이 이어진다). `location`은 `address`, `thumbnail`은 대표 이미지 URL. `rating`은 후기 집계가 없는 이번 스테이지엔 항상 `0` 고정값(리뷰 앱 완료 후 실제 값으로 교체, 7.11.8). 결과 없으면 `results: []`.

**`GET /api/v1/places/{placeId}`** — query: 없음(Notion 명세엔 lat/lng가 query에 없지만, 이슈 #12가 "선택적 lat/lng 쿼리파라미터"를 명시적으로 요구하므로 `latitude`, `longitude`를 선택 쿼리 파라미터로 추가한다 — 계약 확장이지 축소가 아니라서 안전하다고 판단)

```json
{
  "success": true,
  "data": {
    "placeId": 1,
    "name": "...",
    "category": "관광지",
    "description": "...",
    "address": "...",
    "hours": "...",
    "images": ["https://...", "https://..."],
    "map": { "lat": 34.8, "lng": 126.4 },
    "distanceFromUser": "12.3km",
    "reviewSummary": { "avgRating": 0, "aiSatisfaction": null }
  },
  "error": null
}
```

`distanceFromUser`는 Notion 명세 타입(`"string"`)에 맞춰 `"{km}km"` 형식의 문자열로 반환한다(예: `"12.3km"`). lat/lng 쿼리가 없으면 `null`. `reviewSummary`는 `reviews` 앱(Stage 4) 전까지 `avgRating: 0`, `aiSatisfaction: null` 고정값.

**`GET /api/v1/places/{placeId}/congestion`**

```json
{
  "success": true,
  "data": {
    "level": "보통",
    "concentrationRate": 57.2,
    "forecastDate": "2026-08-05",
    "parkingAvailable": true,
    "recommendedDate": "2026-08-10"
  },
  "error": null
}
```

`TouristCongestionClient`가 일치하는 관광지 예측 데이터를 찾지 못하거나 호출에 실패하면 `{"success": true, "data": {}, "error": null}`로 응답한다.

**`GET /api/v1/traffic/congestion`** — query: `origin.lat`, `origin.lng`, `destination.lat`, `destination.lng`

```json
{
  "success": true,
  "data": {
    "segments": [{ "section": "...", "level": "원활" }],
    "etaMin": 15,
    "altRoute": { "available": true, "etaMin": 12 }
  },
  "error": null
}
```

`KakaoMobilityClient`가 `None`을 반환하면(이번 스테이지는 항상 그렇다) `TRAFFIC_DATA_UNAVAILABLE`로 `{"success": true, "data": {}, "error": null}` 응답.

#### 7.11.7 테스트 관점 (`tests/test_places_search.py`, `tests/test_places_detail.py`, `tests/test_places_congestion.py`, `tests/test_traffic_congestion.py`)

`TourApiClient`/`TouristCongestionClient`/`KakaoMobilityClient`는 테스트에서 `unittest.mock.patch`로 HTTP 호출을 모킹한다.

- 검색 성공: mock 2건 반환 → `id`/`name`/`category`/`location`/`thumbnail` 존재, `rating: 0`, `TouristSpot` upsert 확인.
- 검색 결과 없음: `results: []`.
- 검색 — TourAPI 실패(mock이 `TourApiError`): `EXTERNAL_API_ERROR`, 502.
- 상세 조회 성공: `latitude`/`longitude` 쿼리 있을 때 `distanceFromUser` 계산됨, 없을 때 `null`. `reviewSummary`는 항상 고정값.
- 상세 조회 — 존재하지 않는 `placeId`: `PLACE_NOT_FOUND`, 404.
- 상세 조회 — 로컬엔 있지만 TourAPI가 더 이상 `content_id`를 반환 안 함(mock `None`): `PLACE_NOT_FOUND`, 404.
- 혼잡도 — 존재하지 않는 `placeId`: `PLACE_NOT_FOUND`, 404.
- 집중률 — 예측 데이터가 없을 때 200 + `data: {}`.
- 집중률 — 현재 집중률, 기준일, 추천 방문일을 파싱하고 `parkingAvailable`을 로컬 `TouristSpot.parking_available`에서 채우는지 확인.
- 교통 — `KakaoMobilityClient`가 `None`(기본 동작): 200 + `data: {}`.

#### 7.11.8 미해결 사항 / 후속 작업

1. 관광지 집중률은 실시간 현장 인원이나 시간대별 대기시간이 아니라 향후 30일의 일별 예측값이다. 화면과 API에서 이를 실시간 혼잡도로 표현하지 않는다.
2. 집중률 API 관광지명과 TourAPI 장소명이 일치하지 않는 장소는 빈 데이터로 처리하며, 운영 데이터 확인 후 별도 매핑 테이블 도입을 검토한다.
3. `rating`(통합 검색), `reviewSummary.avgRating`/`aiSatisfaction`(장소 상세)은 `reviews`/`interactions` 앱(Stage 4) 완료 전까지 고정값(`0`/`null`)으로 응답한다. Stage 4 완료 후 실제 집계값으로 교체한다.
4. `sort` 쿼리 파라미터는 Notion 명세에 구체적 옵션이 없다 — 현재는 값을 받기만 하고 실제 정렬에는 반영하지 않는다(TourAPI 기본 정렬 그대로 반환). 통합 검색 페이지네이션도 노출하지 않는다. 프론트 요구사항 확인 후 별도 확정.
5. 캐시 TTL 만료·오래된 `TouristSpot`/`TouristSpotImage` 정리 배치는 도입하지 않는다. 트래픽이 늘어 TourAPI 호출량이 문제가 되면 재검토.

### 7.12 `courses` 앱 상세 설계 (Stage 3-① 실행용, `feature/courses-base`)

> GitHub 이슈 초안("[Feature] 추천 코스 저장 구조 + 상태 API 구현")과 Notion API spec DB "추천" 그룹의 코스 저장(`e6804d374d2783f3a7c0014db7badaf9`)·코스 시작(`1e304d374d2782c3957a81d1d32968cf`)·완주 인증(`56e04d374d2783ea9e3c81d0a400f879`)·코스 공유(`72104d374d27821e93198183646acb2f`) 4개 페이지, "데이터 모델링 (ERD)" 페이지의 `courses`/`course_places`/`user_courses` 테이블을 근거로 7.2절을 실행 가능한 수준까지 구체화한다. 이 브랜치에는 `Course`/`CoursePlace`를 만드는 공개 API가 없다 — AI 추천(Stage 3-②, `feature/courses-recommend`)과 동선 최적화(Stage 3-③, `feature/courses-optimize`)가 그 역할을 맡으므로, 이번 스테이지는 두 모델이 **이미 존재한다고 가정**하고 그 위에서 저장/시작/완주 인증/공유 4개 상태 전이 API만 구현한다. 테스트도 `Course`/`CoursePlace`를 ORM으로 직접 생성해 검증한다.

#### 7.12.1 모델

**`Course`** (7.2절 필드 + ERD `courses.status` 반영)

| 필드 | 타입 | 비고 |
|---|---|---|
| `owner` | FK to `accounts.User`, null 허용, `on_delete=SET_NULL` | AI 자동 생성 코스는 소유자 없음. **이 필드는 "코스를 최초로 만든 사람"만 가리키고, 코스 저장(`save`) API가 이 값을 갱신하지 않는다** — 공유 링크로 들어온 다른 사용자가 저장/시작해도 `owner`는 그대로다. 여러 사용자의 개별 진행은 `CourseProgress`가 담당(7.12.3의 "다중 사용자" 메모). |
| `name` | `CharField` | |
| `duration_minutes` | `PositiveIntegerField`, null 허용 | AI 추천 결과로 채워짐(Stage 3-②), 이번 스테이지는 fixture 값 그대로 |
| `distance_km` | `DecimalField`, null 허용 | 〃 |
| `recommend_reason` | `TextField`, blank 허용 | 〃 |
| `mood` / `companion_type` / `transport_type` | `CharField`, blank 허용 | AI 추천 입력값 기록용(Stage 3-②) |
| `status` | `CharField`, choices `TEMP`/`SAVED`, default `TEMP` | ERD 기준 신규 추가. **`TEMP → SAVED` 단방향 승격만 한다** — 코스 저장 API가 호출되면 `SAVED`로 바뀌고 이후 절대 되돌아가지 않는다(다운그레이드 로직 없음). |

**`CoursePlace`** (7.2절 그대로, 이번 스테이지에서 필드 추가 없음 — 동선 최적화 착수 시 ERD의 `estimated_arrival_time` 등 나머지 필드 도입 여부를 그때 재검토)

| 필드 | 타입 | 비고 |
|---|---|---|
| `course` | FK to `Course`, `on_delete=CASCADE`, `related_name="places"` | |
| `place` | FK to `places.TouristSpot`, `on_delete=CASCADE` | |
| `order` | `PositiveSmallIntegerField` | 방문 순서 |
| `travel_time_from_prev` | `PositiveIntegerField`, null 허용 | 분 단위, 카카오 로컬 API 결과 캐시. Stage 3-③ 전까지 항상 `None` |

`Meta.constraints = [UniqueConstraint(fields=["course", "order"])]` — ERD `visit_order UNIQUE with course_id` 반영.

**`CourseProgress`**

| 필드 | 타입 | 비고 |
|---|---|---|
| `user` | FK to `accounts.User`, `on_delete=CASCADE`, `related_name="course_progresses"` | |
| `course` | FK to `Course`, `on_delete=CASCADE`, `related_name="progresses"` | |
| `status` | `CharField`, choices `SAVED`/`IN_PROGRESS`/`COMPLETED` | ERD `user_courses.status` |
| `started_at` | `DateTimeField`, null 허용 | `start` 호출 시각 |
| `completed_at` | `DateTimeField`, null 허용 | `complete` 성공 시각 |
| `created_at` / `updated_at` | `DateTimeField`(`auto_now_add`/`auto_now`) | |

`Meta.constraints = [UniqueConstraint(fields=["user", "course"])]` — ERD `user_courses` UNIQUE(user_id, course_id). 사용자 1명당 코스 1개에 진행 기록은 1건뿐이며, "다시 시작"도 같은 행을 갱신한다(7.12.3).

#### 7.12.2 에러 코드 (`common/exceptions.py` 추가)

| 코드 | 상태코드 | 메시지 | 발생 조건 |
|---|---|---|---|
| `COURSE_NOT_FOUND` | 404 | 존재하지 않는 코스입니다. | 4개 엔드포인트 전부 — path의 `courseId`로 `Course`를 찾을 수 없음 |
| `LOCATION_MISMATCH` | 400 | 코스 경로와 위치가 일치하지 않습니다. | 완주 인증 시 `checkInLocations` 개수 불일치 또는 반경 이탈 |

#### 7.12.3 서비스 계층 (`courses/services.py`)

공통 헬퍼: `_get_course(course_id) -> Course` — `Course.objects.get(pk=course_id)`, `DoesNotExist`는 `ApiError(ErrorCode.COURSE_NOT_FOUND)`로 변환. 4개 서비스 함수 전부 이 헬퍼로 시작한다.

**`save_course(*, user, course_id) -> Course`**
1. `course = _get_course(course_id)`
2. `course.status = Course.Status.SAVED`로 갱신·저장(이미 `SAVED`여도 그대로 — 멱등).
3. `CourseProgress.objects.update_or_create(user=user, course=course, defaults={"status": CourseProgress.Status.SAVED})`
4. `course` 반환.

**`start_course(*, user, course_id) -> CourseProgress`**
1. `course = _get_course(course_id)`
2. `CourseProgress.objects.update_or_create(user=user, course=course, defaults={"status": CourseProgress.Status.IN_PROGRESS, "started_at": timezone.now()})` — `save` 선행 여부와 무관하게 항상 성공(Notion 계약에 "먼저 저장해야 함" 같은 전제·에러코드가 없다).
3. 반환.

**상태 upsert 규칙에 대한 결정 — 의도적으로 단순하게 간다.** `save`/`start`/`complete`는 각자 맡은 상태값을 **조건 없이** `update_or_create`로 덮어쓴다. 예를 들어 이미 `COMPLETED`인 코스에 `save`를 다시 호출하면 `CourseProgress.status`는 `SAVED`로 되돌아간다. "진행 상태는 앞으로만 간다" 같은 상태 머신 가드는 이슈 완료 조건 어디에도 없고 Notion 계약도 4개 엔드포인트를 서로 독립적인 단발 액션으로만 정의하므로, 요구되지 않은 보호 로직을 임의로 추가하지 않았다(0절 원칙 2). 실제 운영 중 "완주한 코스를 재저장하면 진행 상태가 사라지는" 문제가 관측되면 별도 이슈로 상태 머신 가드를 추가한다(7.12.8-①).

**`complete_course(*, user, course_id, check_in_locations) -> CourseProgress`** — 이 브랜치의 핵심 로직.
1. `course = _get_course(course_id)`
2. `course_places = list(CoursePlace.objects.filter(course=course).order_by("order"))`
3. **개수 검증**: `len(check_in_locations) != len(course_places)`면 `ApiError(LOCATION_MISMATCH)`.
4. **반경 검증**: `zip(check_in_locations, course_places)`으로 순서대로 짝지어, 각 쌍마다 `places.services.calculate_distance_km(loc.lat, loc.lng, cp.place.latitude, cp.place.longitude) * 1000`(km→m 환산)이 `settings.COURSE_CHECKIN_RADIUS_M`을 초과하면 `ApiError(LOCATION_MISMATCH)`. 하나라도 실패하면 즉시 예외를 던지고 `CourseProgress`는 건드리지 않는다(부분 갱신 없음).
5. 전부 통과하면 `CourseProgress.objects.update_or_create(user=user, course=course, defaults={"status": CourseProgress.Status.COMPLETED, "completed_at": timezone.now()})`.
6. 반환. `cardId`는 서비스가 아니라 뷰/시리얼라이저에서 항상 `None`으로 고정한다(Stage 5의 `CompletionCard` 완료 전까지).

체크인 지점과 코스 장소의 매칭은 **`order` 순서 기반 1:1 페어링**으로 확정한다 — Notion 요청 스펙이 `checkInLocations`를 순서 있는 배열로만 정의하고 각 지점이 어느 장소용인지 별도 식별자를 주지 않으므로, "사용자가 코스 순서대로 방문하며 그 순서대로 체크인한다"는 유일하게 검증 가능한 해석을 택했다(7.12.8-④). 반경 계산은 `places/services.py`의 `calculate_distance_km`(haversine, km 단위)를 그대로 재사용해 m로 환산 비교한다 — 새 거리 계산 로직을 만들지 않는다.

**`share_course(*, course_id) -> str`**
1. `course = _get_course(course_id)`
2. `f"{settings.COURSE_SHARE_BASE_URL}/{course.id}"` 반환. 요청한 사용자 정보는 URL에 넣지 않는다 — Notion 응답이 `shareUrl` 문자열 하나뿐이고, 공유 링크를 연 다른 사용자가 그 코스를 독립적으로 저장/시작할 수 있어야 하므로 사용자 종속 값을 넣을 이유가 없다.

#### 7.12.4 엔드포인트

4개 전부 `permission_classes = [IsAuthenticated]`(Notion `authorization: required`), `POST`, path param `courseId`(int, 로컬 PK).

**`POST /api/v1/courses/{courseId}/save`** — 요청 본문 없음

```json
{ "success": true, "data": { "saved": true }, "error": null }
```

**`POST /api/v1/courses/{courseId}/start`** — 요청 본문 없음

```json
{ "success": true, "data": { "startedAt": "2026-08-06T10:00:00Z" }, "error": null }
```

**`POST /api/v1/courses/{courseId}/complete`**

```json
{ "checkInLocations": [{ "lat": 34.8, "lng": 126.4 }, { "lat": 34.81, "lng": 126.42 }] }
```

```json
{ "success": true, "data": { "completed": true, "cardId": null }, "error": null }
```

검증 실패 시 `LOCATION_MISMATCH`(400). `checkInLocations`는 `allow_empty=False`(빈 배열은 개수 불일치 판정 이전에 시리얼라이저 검증에서 422로 걸러진다), 각 원소는 `lat`(-90~90)/`lng`(-180~180) 범위 검증(`places`의 쿼리 시리얼라이저와 동일한 방식).

**`POST /api/v1/courses/{courseId}/share`** — 요청 본문 없음

```json
{ "success": true, "data": { "shareUrl": "https://eodiganam.app/courses/1" }, "error": null }
```

4개 전부 `courseId`가 존재하지 않으면 `COURSE_NOT_FOUND`(404).

#### 7.12.5 URL 등록

`places`와 달리 4개 엔드포인트가 전부 `/courses/{courseId}/...` 아래 있으므로 `accounts`와 같은 방식(prefix `include`)을 쓴다.

`config/urls.py`에 `path("api/v1/courses/", include("courses.urls"))` 추가.

`courses/urls.py`:

```python
urlpatterns = [
    path("<int:courseId>/save", CourseSaveView.as_view(), name="save"),
    path("<int:courseId>/start", CourseStartView.as_view(), name="start"),
    path("<int:courseId>/complete", CourseCompleteView.as_view(), name="complete"),
    path("<int:courseId>/share", CourseShareView.as_view(), name="share"),
]
```

#### 7.12.6 환경 변수 (`.env.example` 추가)

| 변수 | 기본값 | 비고 |
|---|---|---|
| `COURSE_CHECKIN_RADIUS_M` | `200` | 완주 인증 반경 임계값(미터). 운영 데이터 확인 후 조정 |
| `COURSE_SHARE_BASE_URL` | `https://eodiganam.app/courses` | **placeholder** — 실제 프론트엔드 배포 도메인이 정해지면 교체(7.12.8-②) |

`config/settings.py`에 `COURSE_CHECKIN_RADIUS_M=(int, 200)` 타입 캐스팅을 `environ.Env(...)` 초기화 인자에 등록하고, `COURSE_SHARE_BASE_URL`은 문자열 그대로 읽는다.

#### 7.12.7 테스트 관점 (`tests/test_courses.py`, 신규)

`Course`/`CoursePlace`는 공개 API가 없으므로 테스트에서 직접 ORM으로 생성한다(`TouristSpot` 2~3개 + `CoursePlace(order=0/1/2)`).

- 저장 — 성공: `Course.status == SAVED`, `CourseProgress(user, course).status == SAVED` 생성 확인.
- 저장 — 존재하지 않는 `courseId`: `COURSE_NOT_FOUND`, 404.
- 시작 — 성공: `CourseProgress.status == IN_PROGRESS`, `started_at` not null, 응답 `startedAt`이 그 값과 일치.
- 시작 — 존재하지 않는 `courseId`: `COURSE_NOT_FOUND`, 404.
- 완주 인증 — 성공: 코스 장소 좌표와 동일(또는 반경 이내)한 `checkInLocations` → `COMPLETED` + `completed_at` 설정, 응답 `completed: true, cardId: null`.
- 완주 인증 — 반경 밖: 장소 좌표에서 `COURSE_CHECKIN_RADIUS_M`보다 먼 좌표를 하나라도 포함 → `LOCATION_MISMATCH`, 400, `CourseProgress` 상태는 호출 전과 동일하게 유지.
- 완주 인증 — 개수 불일치: 코스 장소가 3개인데 `checkInLocations`는 2개 → `LOCATION_MISMATCH`, 400.
- 완주 인증 — 존재하지 않는 `courseId`: `COURSE_NOT_FOUND`, 404.
- 공유 — 성공: `shareUrl`에 `courseId`가 포함되는지 확인.
- 공유 — 존재하지 않는 `courseId`: `COURSE_NOT_FOUND`, 404.
- 인증 — 4개 중 최소 1개는 토큰 없이 호출 시 401(`IsAuthenticated` 배선 확인용 — 나머지 3개까지 반복 검증할 필요는 없음).

#### 7.12.8 미해결 사항 / 후속 작업

1. **상태 되돌림 미보호**: 7.12.3에서 서술한 대로 `save`/`start`/`complete`는 서로의 상태를 덮어쓸 수 있다(예: 완주 후 재저장하면 `SAVED`로 후퇴). 프론트엔드가 실제로 이 3개 호출을 어떤 순서로 쓰는지 확인한 뒤 필요하면 상태 머신 가드를 추가한다.
2. **`COURSE_SHARE_BASE_URL`은 placeholder다.** 실제 프론트엔드 도메인이 정해지면 값을 교체해야 한다 — 지금은 "유효한 URL 형식의 문자열을 반환한다"는 계약만 만족시킨다.
3. **`Course.owner`가 여러 사용자의 저장/시작을 어떻게 다루는지는 이번 스테이지에서 실사용 검증이 안 된다** — `Course`를 만드는 공개 API(Stage 3-②/③)가 아직 없어서 "한 코스를 여러 사용자가 공유해 각자 저장"하는 흐름은 fixture로만 테스트한다. Stage 3-② 착수 시 실제 흐름으로 재검증이 필요하다.
4. 완주 인증의 순서 기반 1:1 페어링(7.12.3)은 Notion 계약상 유일하게 검증 가능한 해석이지만, 프론트엔드가 실제로 장소별 `placeId`를 체크인 요청에 함께 보낼 수 있다면(계약 확장) 순서 대신 명시적 매칭으로 바꾸는 게 더 안전하다 — 프론트 연동 시점에 재확인.

### 7.13 `courses` 앱 AI 맞춤 추천 (Stage 3-②, `feature/courses-recommend`, GitHub 이슈 #18 기준)

이 절의 근거는 GitHub 이슈 #18, Notion API spec "AI 맞춤 추천 요청"(`2b304d374d27839799ca01f2337488d5`), "데이터 모델링 (ERD)" 페이지의 `courses`/`course_places` 테이블(`39104d374d27814ea306e206cf41bf8c`)이다. 대상은 `POST /api/v1/recommend/ai` 한 엔드포인트뿐이다. 7.12절은 `Course`/`CoursePlace`가 "이미 존재한다고 가정"하고 그 위의 상태 전이 API만 다뤘는데, 이번 스테이지가 그 둘을 실제로 만드는 첫 공개 API다. 새 앱은 만들지 않고 기존 `courses` 앱에 필드 2개와 엔드포인트 1개만 추가한다.

#### 7.13.1 모델 (`courses/models.py`)

`Course`에 다음 두 필드만 추가한다. `mood`/`companion_type`/`transport_type`은 `feature/courses-base`에서 이미 `CharField(max_length=50, blank=True)`로 존재하므로(값 검증 없는 저장용 필드) 변경하지 않는다 — Notion 요청의 `companion`/`transport` 값 종류(아래 7.13.3) 검증은 시리얼라이저의 `ChoiceField`에서만 하고, 모델에는 `choices`를 걸지 않는다(7.13.5-②에서 이유 설명).

| 필드 | 타입 | 비고 |
|---|---|---|
| `time_available` | `CharField(max_length=50, blank=True)` | Notion 요청 `timeAvailable` 그대로 저장(형식 자유, 예: `"2시간"`) |
| `free_text` | `TextField(blank=True)` | Notion 요청 `freeText` 그대로 저장 |

`python manage.py makemigrations courses`로 마이그레이션을 생성한다. `CoursePlace`/`CourseProgress`는 변경 없음.

#### 7.13.2 에러 코드 (`common/exceptions.py` 추가)

| 코드 | 상태코드 | 메시지 | 발생 조건 |
|---|---|---|---|
| `MOOD_REQUIRED` | 400 | 기분을 선택해주세요. | 요청의 `mood`가 없거나 공백 |
| `AI_RECOMMEND_FAILED` | 500 | 추천 생성에 실패했습니다. | AI 추천 어댑터 호출 실패, 추천 결과에 장소가 하나도 없음, 또는 추천된 장소를 로컬 `TouristSpot`으로 확정(그라운딩)하는 데 실패(7.13.4) |

기존 `ErrorCode` enum의 `(code, status_code, message)` 튜플 관례를 그대로 따른다.

#### 7.13.3 엔드포인트

**`POST /api/v1/recommend/ai`** — `permission_classes = [IsAuthenticated]`(Notion `authorization: required`)

요청(`AIRecommendRequestSerializer`, `courses/serializers.py`):

```json
{
  "mood": "string",
  "companion": "혼자|커플|가족|친구",
  "transport": "도보|대중교통|자차",
  "timeAvailable": "string",
  "freeText": "string"
}
```

| 필드 | DRF 필드 | 비고 |
|---|---|---|
| `mood` | `CharField(required=False, allow_blank=True, default="", max_length=50)` | `mood`만 필수다. 필드를 `required=True`로 두면 DRF가 일반 `COMMON_422`로 먼저 걸러버려 `MOOD_REQUIRED`를 반환할 수 없으므로, 대신 `required=False, default=""`로 통과시킨 뒤 `validate_mood`에서 공백이면 `ApiError(ErrorCode.MOOD_REQUIRED)`를 직접 raise한다 — 6.4.2(`INVALID_CREDENTIALS`)와 같은 이유로 특정 도메인 에러 코드가 일반 422보다 우선한다. 길이는 모델과 동일하게 50자로 제한한다 |
| `companion` | `ChoiceField(choices=["혼자","커플","가족","친구"], required=False, allow_blank=True, default="")` | 값이 4개 중 하나가 아니면 DRF 기본 동작대로 `COMMON_422`(6.6.8의 `provider` 검증과 동일 패턴) |
| `transport` | `ChoiceField(choices=["도보","대중교통","자차"], required=False, allow_blank=True, default="")` | 위와 동일 |
| `timeAvailable` | `CharField(required=False, allow_blank=True, default="", max_length=50)` | 모델 필드와 동일하게 50자로 제한한다 |
| `freeText` | `CharField(required=False, allow_blank=True, default="", max_length=500)` | LLM 비용·지연 남용을 막기 위해 500자로 제한한다 |

`mood` 이외 필드는 이슈 완료 조건에 별도 에러 코드가 없으므로 전부 선택값으로 둔다(0절 원칙 2 — 명세에 없는 필수 검증을 임의로 추가하지 않음).

응답 `200`:

```json
{
  "success": true,
  "data": {
    "courseId": 12,
    "name": "...",
    "reason": "...",
    "places": [
      { "placeId": 5, "order": 1 },
      { "placeId": 9, "order": 2 }
    ]
  },
  "error": null
}
```

`courseId`/`placeId`는 Notion 명세상 타입이 `"string"`이지만, 이슈 완료 조건("응답의 courseId/placeId가 로컬 PK와 동일해 이후 장소 상세/코스 저장 API와 연결됨")에 따라 로컬 PK(정수)를 그대로 내려준다 — 7.11.6의 통합 검색 `id` 필드와 같은 판단이다. `reason`은 `Course.recommend_reason`과 키 이름이 다르다(6.4.3과 같은 이유로 이미 확정된 Notion 계약을 그대로 따르고 임의로 통일하지 않는다). `name`은 시리얼라이저 필드명이 요청 필드(`companion`/`transport`/`timeAvailable`)와 모델 필드명(`companion_type`/`transport_type`/`time_available`)이 달라 뷰에서 `courses/services.py`의 `request_ai_recommendation`을 호출할 때 명시적으로 매핑한다(6.5.3과 동일한 관례).

#### 7.13.4 AI 추천 어댑터 인터페이스 및 서비스 계층

**`courses/ai_recommend.py`** — `places/tourapi.py`(`TourApiClient`)·`places/kakao_mobility.py`(`KakaoMobilityClient`)와 같은 자리의 외부 연동 어댑터다.

```python
class AIRecommendError(Exception):
    pass

@dataclass(frozen=True)
class RecommendedPlace:
    content_id: str   # TourAPI content_id — places.TouristSpot.content_id와 동일 키(7.11.2)
    order: int

@dataclass(frozen=True)
class AIRecommendation:
    name: str
    reason: str
    places: list[RecommendedPlace]

class AIRecommendClient:
    def recommend(
        self, *, mood: str, companion: str, transport: str,
        time_available: str, free_text: str,
    ) -> AIRecommendation:
        raise NotImplementedError
```

**왜 장소를 로컬 PK가 아니라 `content_id`로 주고받는가**: AI 추천 로직이 자체 LLM 프롬프트든 외부 추천 API든, 이 서비스에서 실제 존재하는 관광지를 가리키는 안정적인 외부 식별자는 TourAPI `content_id`다(7.11.2). 어댑터는 `Course`/`CoursePlace` 모델이나 로컬 PK에 결합하지 않고 이 경계 계약을 유지한다. 후보를 가져오는 `search_spots`가 이미 모든 후보를 `TouristSpot`에 write-through하므로, 서비스는 추천된 `content_id`를 로컬 테이블에서 조회해 PK를 확정하며 TourAPI 상세를 다시 호출하지 않는다.

**후보 검색 전략**: `mood`/`companion`/`transport`/`timeAvailable`은 장소 검색어가 아니므로 LLM 프롬프트 컨텍스트로만 사용한다. `freeText`가 있으면 우선 그 값으로 `searchKeyword2` 검색을 수행하되 결과가 없으면, 또는 `freeText`가 비어 있으면 `keyword=None`으로 `areaBasedList2`를 호출해 전남 전체 후보로 폴백한다. 두 조회 모두 결과가 없거나 검색 호출이 실패하면 `AIRecommendError`로 변환한다.

**`courses/services.py` — `request_ai_recommendation`**

```python
def request_ai_recommendation(
    *, user, mood, companion, transport, time_available, free_text
) -> Course:
    try:
        recommendation = AIRecommendClient().recommend(
            mood=mood, companion=companion, transport=transport,
            time_available=time_available, free_text=free_text,
        )
    except AIRecommendError as exc:
        raise ApiError(ErrorCode.AI_RECOMMEND_FAILED) from exc

    if not recommendation.places:
        raise ApiError(ErrorCode.AI_RECOMMEND_FAILED)

    content_ids = [item.content_id for item in recommendation.places]
    spots_by_content_id = {
        spot.content_id: spot
        for spot in TouristSpot.objects.filter(content_id__in=content_ids)
    }
    resolved = []
    for item in recommendation.places:
        spot = spots_by_content_id.get(item.content_id)
        if spot is None:
            raise ApiError(ErrorCode.AI_RECOMMEND_FAILED)
        resolved.append((spot, item.order))

    try:
        with transaction.atomic():
            course = Course.objects.create(
                owner=user,
                name=recommendation.name,
                recommend_reason=recommendation.reason,
                mood=mood,
                companion_type=companion,
                transport_type=transport,
                time_available=time_available,
                free_text=free_text,
                status=Course.Status.TEMP,
            )
            CoursePlace.objects.bulk_create([
                CoursePlace(course=course, place=spot, order=order)
                for spot, order in resolved
            ])
    except IntegrityError as exc:
        raise ApiError(ErrorCode.AI_RECOMMEND_FAILED) from exc
    return course
```

- AI 호출과 후보 검색은 어댑터에서, 추천 장소의 로컬 조회는 서비스에서 모두 트랜잭션 밖에 수행한다. `transaction.atomic()`은 `Course`/`CoursePlace` DB 쓰기만 짧게 감싸며, 쓰기 실패 시 부분 생성된 코스를 전부 롤백한다.
- `RecommendedPlace.order`는 1부터 시작하는 연속된 정수여야 `CoursePlace`의 `(course, order)` UNIQUE 제약(7.12.1)을 통과한다. 이를 어댑터 구현체가 보장하지 못하면 `IntegrityError`가 나고 `AI_RECOMMEND_FAILED`로 변환된다 — 별도의 사전 검증 로직을 추가하지 않고 DB 제약에 위임한다(0절 원칙 3).
- `owner=user`로 항상 설정한다. 7.2절의 "AI 자동 생성 코스는 소유자 없을 수 있음"은 인증 없는 진입 경로를 상정한 서술이었지만, 이 엔드포인트는 `authorization: required`이므로 이번 스테이지에서는 `owner`가 항상 채워진다.
- `Course.status`는 모델 기본값(`TEMP`)을 그대로 쓴다.

#### 7.13.5 미해결 사항 (착수 시 결정 필요)

1. **[해결] AI 추천 연동 방식.** OpenAI 호환 Chat Completions API를 `requests`로 직접 호출하는 자체 LLM 프롬프트 방식을 채택했다. `LLM_API_BASE_URL`/`LLM_API_KEY`/`LLM_API_MODEL`/`LLM_API_TIMEOUT_SEC` 환경변수로 공급자를 설정하며, `AIRecommendClient`는 후보에 포함된 TourAPI `content_id`만 반환하도록 응답을 검증한다.
2. **[해결] AI가 고를 후보 관광지 풀의 범위.** 이미 로컬에 캐시된 장소로 한정하지 않고, `freeText`만 검색 키워드로 사용한다. 검색 결과가 없거나 `freeText`가 비어 있으면 키워드 없는 전남 전체 조회로 폴백하고, 그 결과를 로컬에 write-through한 뒤 LLM 후보 컨텍스트로 사용한다. 감정·동행·교통·시간 값은 LLM 컨텍스트로만 전달한다.
3. `companion_type`/`transport_type`을 모델 `choices`로 강제하지 않고 시리얼라이저 `ChoiceField`로만 검증하기로 한 것(7.13.1)은, 가능한 값이 Notion에서 이미 4개/3개로 확정돼 있어 마이그레이션 없이 시리얼라이저만 바꿔 값 종류를 조정할 수 있게 하기 위한 의도적 선택이다. 값 종류가 자주 바뀌게 되면 모델에도 `choices`를 추가하는 쪽으로 재검토한다.
4. `CoursePlace.travel_time_from_prev`는 이 API가 만든 `CoursePlace`에도 항상 `null`이다 — 동선 최적화(Stage 3-③, `feature/courses-optimize`) 착수 전까지는 채워지지 않는다.
5. 이 API로 만든 `Course`에 대해 기존 저장/시작/완주 인증/공유(7.12절, #15)가 실제로 정상 동작하는지는 이번 이슈의 회귀 테스트(7.13.6)로만 확인한다 — `Course.owner`가 항상 채워진다는 점을 제외하면 7.12.8-③에서 남겼던 "다중 사용자 저장/시작" 시나리오는 여전히 fixture 기반 검증에 머무른다.

#### 7.13.6 URL 등록 및 테스트 관점

4개 상태 전이 API(7.12.5)와 달리 `/api/v1/recommend/ai`는 `/courses/{courseId}/...` 프리픽스에 맞지 않는다. `courses/urls.py`(prefix `api/v1/courses/`)에 넣지 않고, `places.urls`처럼 별도 파일을 새로 만들 것도 없이 `config/urls.py`에 직접 한 줄 등록한다(0절 원칙 3 — 엔드포인트 1개를 위해 앱/파일을 새로 쪼개지 않는다).

```python
# config/urls.py
path("api/v1/recommend/ai", AIRecommendView.as_view(), name="recommend-ai"),
```

`AIRecommendView`는 `courses/views.py`에 추가하고, `courses/urls.py`의 4개 라우트와 마찬가지로 `drf_spectacular`의 `@extend_schema`를 붙인다.

테스트(`tests/test_courses_recommend.py`, 신규) — API 서비스 테스트는 `courses.services.AIRecommendClient.recommend`만 mock 처리하고, 추천 장소 그라운딩은 fixture로 생성한 로컬 `TouristSpot` 조회를 실제로 수행한다.

- 성공: 응답에 `courseId`/`name`/`reason`/`places`가 있고, 각 `places[i].order`가 요청 순서와 일치. 생성된 `Course.status == TEMP`, `Course.owner == request.user`, `CoursePlace`가 추천 순서대로 존재.
- `mood` 누락/공백: `MOOD_REQUIRED`, 400.
- AI 어댑터가 `AIRecommendError`를 던짐: `AI_RECOMMEND_FAILED`, 500, `Course`가 생성되지 않음(DB에 남지 않는지 확인).
- AI 어댑터가 빈 `places`를 반환: `AI_RECOMMEND_FAILED`, 500.
- 추천된 `content_id` 중 하나가 로컬 `TouristSpot`에 없음: `AI_RECOMMEND_FAILED`, 500, `Course`/`CoursePlace`가 생성되지 않음.
- `freeText` 키워드 검색 결과가 없으면 키워드 없는 전남 전체 후보로 폴백하며, 폴백 결과도 비면 `AI_RECOMMEND_FAILED`, 500.
- `mood`/`timeAvailable` 50자 및 `freeText` 500자 초과: `COMMON_422`.
- `companion`/`transport`에 허용되지 않은 값: `COMMON_422`.
- 인증 없이 호출: `AUTH_401`.
- **회귀**: 이 API로 생성한 `Course`/`CoursePlace`에 대해 `POST /courses/{courseId}/save`·`/start`·`/complete`·`/share`(7.12절, `feature/courses-base`)를 순서대로 호출해 전부 기존과 동일하게 동작하는지 확인.

### 7.14 `courses` 앱 상세 설계 (Stage 3-③ 실행용, `feature/courses-optimize`, GitHub 이슈 #20 기준)

> Notion API spec "코스 동선 최적화"(`d0904d374d2782a68116012c2f5c894f`) 페이지 근거. `Course`/`CoursePlace` 모델은 `feature/courses-base`(#15)에서 이미 존재하며, 이번 브랜치는 새 모델 없이 `courses` 앱에 엔드포인트 1개만 추가한다(이슈 #20 범위).

#### 7.14.1 에러 코드

| 코드 | 상태코드 | 메시지 | 발생 조건 |
|---|---|---|---|
| `MIN_PLACE_REQUIRED` | 400 | 장소를 2개 이상 선택해주세요. | `placeIds`가 2개 미만 |
| `ROUTE_CALC_FAILED` | 500 | 경로 계산에 실패했습니다. | `KakaoMobilityClient` 호출/파싱 실패(내부적으로 `get_traffic`이 `None`을 반환하는 모든 경우, 7.14.3) |

`PLACE_NOT_FOUND`(404)는 새로 추가하지 않는다 — `placeIds` 중 로컬 `TouristSpot`으로 존재하지 않는 값이 있을 때 Stage 2(`places` 앱, 7.11.4)의 기존 코드를 그대로 재사용한다(7.15.3의 재사용 판단과 동일한 근거).

#### 7.14.2 `POST /api/v1/courses/optimize`

**요청** (`CourseOptimizeRequestSerializer`, `permission_classes = [IsAuthenticated]` — Notion `authorization: required`)

```json
{ "placeIds": ["string"], "transport": "도보|차량|대중교통" }
```

| 필드 | DRF 필드 | 비고 |
|---|---|---|
| `placeIds` | `ListField(child=CharField(), max_length=8)` | 로컬 `TouristSpot` PK를 문자열로 담은 배열(7.11.6/7.13.3과 동일하게 응답에서도 로컬 PK를 그대로 쓰되, 이 엔드포인트는 요청에서도 Notion 타입(`"string"`)을 그대로 따른다 — 서비스 계층에서 `int()`로 변환해 조회). 2개 미만 여부는 시리얼라이저가 아니라 `optimize_route`가 검증한다(`MOOD_REQUIRED`와 같은 이유, 7.13.3) — `MIN_PLACE_REQUIRED`라는 도메인 에러 코드가 필요하기 때문에 `min_length`로 걸러 일반 `COMMON_422`를 내보내지 않는다. **상한(`max_length=8`)은 Notion 명세에 없는 값이며, 코드 리뷰에서 지적된 리스크(아래)를 근거로 의도적으로 추가한 제약이다** — 초과 시 DRF 기본 동작대로 `COMMON_422` |
| `transport` | `ChoiceField(choices=["도보","차량","대중교통"], required=True)` | 값 검증만 하고 이번 스테이지 계산 로직에는 반영하지 않는다 — 이유는 7.14.3 참고. 허용값 외 요청은 `COMMON_422` |

**`placeIds` 상한을 8개로 제한하는 이유(0절 원칙 2 예외 — 명세 확장이 아니라 제한이므로 근거를 남긴다)**: `optimize_route`는 `n*(n-1)`회의 순차 외부 API 호출과 `n!` 순열 전수 탐색(7.14.3)을 수행한다. 상한이 없으면 실존하는 `placeId`를 10개 이상 나열하는 것만으로(`places` 앱이 이미 수십~수백 건을 캐시하고 있어 어렵지 않다) 요청 하나가 워커를 몇 분 이상 점유할 수 있다는 것이 코드 리뷰에서 확인됐다(직접 측정: `n=12`일 때 순열 생성만 약 4.8억 개). 이는 정상적인 사용 패턴(장소가 많은 하루 코스)에서도 발생할 수 있는 서비스 지연/장애 위험이라 판단해, `freeText` 500자 제한(7.13.3, "LLM 비용·지연 남용 방지")과 같은 성격의 안전장치로 8을 채택했다. 8이라는 값 자체는 실제 프론트 UX(코스당 평균 장소 수)로 확정된 것이 아니므로 조정 가능한 잠정값으로 취급한다(7.14.7 미해결 사항).

**응답 `200`**

```json
{ "success": true, "data": { "orderedPlaces": ["3", "1", "2"], "segmentTimes": [12, 8], "totalTime": 20, "route": {} }, "error": null }
```

`orderedPlaces`는 입력 `placeIds`를 최적 순서로 재배열한 문자열 배열(요청에서 받은 문자열을 그대로 반환 — 로컬 PK로 왕복 변환하지 않는다), `segmentTimes`는 `orderedPlaces` 기준 인접 구간 소요시간(분) 배열로 길이는 항상 `len(placeIds) - 1`, `totalTime`은 `segmentTimes`의 합. `route`는 Notion 명세에 `{}` 외 구체 필드가 없어 이번 스테이지는 항상 빈 객체로 고정한다(7.14.7 미해결 사항 참고).

**중요한 미확정 지점**: 요청 바디에 `courseId`가 없다 — `Course`에 묶이지 않은 순수 계산 API이고, 응답을 실제 `CoursePlace.order`/`travel_time_from_prev`에 반영하는 저장 엔드포인트가 Notion 명세에 없다. 이번 브랜치는 **계산 결과만 응답하고 저장하지 않는다**(이슈 #20 완료조건 "CoursePlace를 직접 수정하지 않는지 확인"). 프론트가 이 결과로 무엇을 하는지는 착수 전 확인 필요(7.14.7 미해결 사항 1).

#### 7.14.3 동선 최적화 알고리즘 및 `KakaoMobilityClient` 재사용

**`transport` 값을 계산에 반영하지 않는 이유**: `places/kakao_mobility.py`의 `KakaoMobilityClient`(Stage 2에서 이미 구현)는 카카오모빌리티 **자동차 길찾기(Directions) API**만 감싼 어댑터이고, 도보·대중교통 경로를 계산하는 API는 이 프로젝트에 아직 연동돼 있지 않다. 이슈 #20이 "`KakaoMobilityClient`(Stage 2에서 이미 구현) 재사용"을 명시적으로 지시하므로, 이번 스테이지는 `transport` 값과 무관하게 항상 자동차 기준 소요시간으로 계산한다. 도보/대중교통 전용 API 연동은 명세에 없는 새 외부 연동을 임의로 추가하는 것이라 이번 브랜치 범위 밖으로 남긴다(0절 원칙 2, 7.14.7 미해결 사항 2). `transport` 필드 자체는 요청 계약대로 받아 값 검증(`ChoiceField`)만 수행한다.

**문제 정의**: `placeIds`로 주어진 장소들을 방문하는 **경로(왕복이 아닌 편도, order 없는 임의 시작점)** 중 총 이동 시간이 최소인 순서를 찾는다. 카카오모빌리티 Directions API는 두 지점 간 경로만 계산하므로(다중 목적지 최적화 API 없음), 모든 지점 쌍의 이동 시간을 먼저 구한 뒤 순서를 자체적으로 탐색해야 한다.

**서비스 로직** (`courses/services.py`, `optimize_route`)

```python
@dataclass(frozen=True)
class OptimizedRoute:
    ordered_place_ids: list[str]
    segment_times: list[int]
    total_time: int
    route: dict


def optimize_route(*, place_ids: list[str], transport: str) -> OptimizedRoute:
    if len(place_ids) < 2:
        raise ApiError(ErrorCode.MIN_PLACE_REQUIRED)

    try:
        pks = [int(place_id) for place_id in place_ids]
    except ValueError as exc:
        raise ApiError(ErrorCode.PLACE_NOT_FOUND) from exc

    spots_by_pk = {
        spot.pk: spot
        for spot in TouristSpot.objects.filter(pk__in=pks)
    }
    try:
        coords = [
            (spots_by_pk[pk].latitude, spots_by_pk[pk].longitude)
            for pk in pks
        ]
    except KeyError as exc:
        raise ApiError(ErrorCode.PLACE_NOT_FOUND) from exc

    duration_matrix = _build_duration_matrix(coords)
    if duration_matrix is None:
        raise ApiError(ErrorCode.ROUTE_CALC_FAILED)

    best_order = _shortest_path_order(duration_matrix)
    segment_times = [
        duration_matrix[best_order[i]][best_order[i + 1]]
        for i in range(len(best_order) - 1)
    ]
    return OptimizedRoute(
        ordered_place_ids=[place_ids[i] for i in best_order],
        segment_times=segment_times,
        total_time=sum(segment_times),
        route={},
    )


def _build_duration_matrix(coords: list[tuple]) -> list[list[int]] | None:
    client = KakaoMobilityClient()
    n = len(coords)
    matrix = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            traffic = client.get_traffic(origin=coords[i], destination=coords[j])
            if traffic is None:
                return None
            matrix[i][j] = traffic.eta_min
    return matrix


def _shortest_path_order(matrix: list[list[int]]) -> list[int]:
    n = len(matrix)
    best_order, best_total = None, None
    for perm in itertools.permutations(range(n)):
        total = sum(matrix[perm[i]][perm[i + 1]] for i in range(n - 1))
        if best_total is None or total < best_total:
            best_order, best_total = perm, total
    return list(best_order)
```

**정정(코드 리뷰 반영)**: 최초 초안은 `placeIds`를 `dict`(`{place_id: int(place_id) ...}`)로 변환해 조회했다. 이 방식은 중복된 `placeId`가 들어오면 키가 조용히 합쳐져 `coords`의 길이가 원본 `place_ids`보다 짧아지고, 이후 `ordered_place_ids=[place_ids[i] for i in best_order]`가 짧아진 인덱스로 원본(길이가 다른) 리스트를 참조해 **응답에서 장소가 조용히 사라지거나 중복 표시되는 버그**로 이어진다는 것이 코드 리뷰에서 확인됐다(예: `place_ids=["5","5","9"]` → 응답이 `["5","5"]`가 되어 `"9"`가 유실됨). 위 코드는 `dict` 대신 `list`(`pks`)를 그대로 써서 `place_ids`/`pks`/`coords`가 항상 같은 길이·같은 순서를 유지하도록 수정한 버전이다. 중복 `placeId` 자체를 막는 검증은 여전히 추가하지 않는다 — 이번 방식에서는 같은 장소를 두 번 방문하는 것으로 자연스럽게 계산될 뿐 에러가 되지 않는다(0절 원칙 2, 이 부분은 최초 의도와 동일).

- `_build_duration_matrix`는 지점 쌍마다 `KakaoMobilityClient.get_traffic`을 호출하므로 API 호출 횟수는 `n * (n - 1)`이다(방향성 고려 — 카카오 자동차 경로는 일방통행 등으로 왕복 시간이 다를 수 있어 대칭으로 가정하지 않는다). 호출 하나라도 `None`을 반환하면(내부적으로 `requests.RequestException`/파싱 실패를 이미 삼키고 `None`을 반환하는 기존 구현, `places/kakao_mobility.py`) 즉시 계산을 중단하고 `ROUTE_CALC_FAILED`로 처리한다 — 이미 성공한 나머지 쌍의 호출 결과는 버린다(부분 결과로 최적화하지 않음).
- `_shortest_path_order`는 순열 전수 탐색(편도 경로, 시작점 고정 없음)이다. `placeIds` 상한이 8(7.14.2)로 정해져 있어 최악의 경우도 순열 40,320개 × 비교 연산으로 무시할 수준이고, `_build_duration_matrix`의 외부 API 호출도 최대 `8*7=56`회로 유한하다. 다만 56회 호출이 전부 순차적으로 실행되는 것은 여전히 응답 지연 요인이다 — 병렬 호출(예: `ThreadPoolExecutor`)로 개선하는 것은 이번 브랜치 범위 밖으로 남긴다(7.14.7 미해결 사항 3).
- `KakaoMobilityClient`(`places/kakao_mobility.py`)는 변경하지 않는다 — 기존 `get_traffic(origin, destination) -> TrafficData | None` 시그니처를 그대로 재사용한다(이슈 #20 지시, 0절 원칙 3).

#### 7.14.4 URL 등록

`courses/urls.py`(prefix `api/v1/courses/`)에 한 줄만 추가한다 — `<int:courseId>` 컨버터는 숫자만 매칭하므로 `optimize`라는 고정 세그먼트와 경로 충돌이 없다.

```python
# courses/urls.py
urlpatterns = [
    path("optimize", CourseOptimizeView.as_view(), name="optimize"),
    path("<int:courseId>/save", CourseSaveView.as_view(), name="save"),
    ...
]
```

`CourseOptimizeView`는 `courses/views.py`에 다른 뷰와 같은 방식(`APIView`, `@extend_schema`)으로 추가한다.

#### 7.14.5 테스트 관점 (`tests/test_courses_optimize.py`, 신규)

`KakaoMobilityClient.get_traffic`을 mock 처리한다(`tests/test_kakao_mobility.py`와 동일한 방식). place는 fixture로 `TouristSpot` 2~3개를 미리 생성한다.

- 성공 — `placeIds` 3개: mock으로 지점 쌍별 `eta_min`을 다르게 반환시켜, 총 이동 시간이 최소인 순서로 `orderedPlaces`가 나오는지, `segmentTimes` 길이가 `len(placeIds) - 1`인지, `totalTime`이 `segmentTimes` 합과 같은지 확인.
- 성공 — `placeIds` 2개: `segmentTimes` 길이 1, `orderedPlaces`가 입력 2개의 순열 중 하나인지 확인.
- 실패 — `placeIds` 1개(또는 0개): `MIN_PLACE_REQUIRED`, 400.
- 실패 — `placeIds`에 로컬 `TouristSpot`으로 존재하지 않는 값 포함: `PLACE_NOT_FOUND`, 404.
- 실패 — `KakaoMobilityClient.get_traffic`이 mock에서 `None` 반환(지점 쌍 중 하나라도): `ROUTE_CALC_FAILED`, 500.
- 실패 — `transport`에 허용되지 않은 값: `COMMON_422`.
- 인증 없이 호출: `AUTH_401`.
- **계산 전용 확인**: 성공 케이스 실행 전후로 `CoursePlace.objects.count()`가 변하지 않는지 확인(이슈 #20 완료조건 "CoursePlace를 직접 수정하지 않는지").
- **회귀(코드 리뷰 반영) — 중복 `placeId`**: 같은 `placeId`를 두 번 포함한 요청이 원본 개수와 동일한 길이의 `orderedPlaces`를 반환하고, 응답에 원본 `placeIds`의 모든 값이 그대로 포함되는지 확인(인덱스 정합성 회귀 방지, 위 정정 참고).
- **회귀(코드 리뷰 반영) — `placeIds` 상한 초과**: `placeIds`가 9개 이상이면 `COMMON_422`인지 확인.

#### 7.14.6 완료 조건 매핑 (이슈 #20)

| 완료 조건 | 대응 |
|---|---|
| `POST /api/v1/courses/optimize`가 명세대로 응답 | 7.14.2 |
| `placeIds` 2개 미만 → `MIN_PLACE_REQUIRED`, 400 | 7.14.1, 7.14.3 |
| `KakaoMobilityClient` 호출 실패 → `ROUTE_CALC_FAILED`, 500 | 7.14.1, 7.14.3 |
| 응답에 `orderedPlaces`/`segmentTimes`/`totalTime`/`route` 포함 | 7.14.2 |
| `CoursePlace`를 직접 수정하지 않음 | 7.14.2(계산 전용), 7.14.5 회귀 확인 |
| pytest 전체 통과 | 7.14.5 |

#### 7.14.7 미해결 사항

1. 동선 최적화 결과를 실제 `CoursePlace`에 반영하는 흐름이 명세에 없다(7.14.2) — 프론트 연동 방식 확인 필요.
2. `transport`(도보/대중교통) 전용 경로 API 미연동 — 현재는 `transport` 값과 무관하게 자동차 기준으로만 계산한다(7.14.3). 실제로 도보/대중교통 소요시간이 필요해지면 별도 외부 API 연동을 검토한다.
3. `_build_duration_matrix`의 최대 56회(`8*7`) 호출이 여전히 순차 실행이다(7.14.3) — 병렬 호출(`ThreadPoolExecutor` 등)로 응답 지연을 줄이는 것은 코드 리뷰에서 제안됐으나 이번 승인 범위(인덱스 정합성 수정 + 상한 추가)에는 포함하지 않았다. 운영 중 지연이 문제가 되면 별도로 착수한다.
4. `route` 필드는 Notion 명세에 `{}` 외 구체 구조가 없어 항상 빈 객체로 응답한다(7.14.2) — 프론트가 실제로 필요한 데이터(예: 폴리라인, 좌표열)가 확인되면 채운다.
5. `placeIds` 상한 `8`(7.14.2)은 코드 리뷰에서 제안된 잠정값이며 Notion 명세에 없다 — 실제 프론트에서 코스당 선택 가능한 장소 수 UX가 확정되면 값을 재검토한다.

### 7.15 `reviews` 앱 상세 설계 (Stage 4 실행용, `feature/reviews`)

> Notion "API spec" DB의 "후기·만족도" 그룹(엔드포인트 5개 확정)과 "데이터 모델링 (ERD)" 페이지 근거(`docs/roadmap.md` 5절).

`feature/reviews` 브랜치 범위는 4개다: **후기 작성**(`POST /reviews`), **후기 목록 조회**(`GET /reviews`, `authorization: none`), **후기 도움돼요**(`POST /reviews/{reviewId}/helpful`), **후기 신고**(`POST /reviews/{reviewId}/report`). **AI 만족도·키워드 요약**(`GET /reviews/summary`, `authorization: none`, 7.15.8절)은 AI 연동 방식이 미확정이라 별도 이슈·브랜치로 분리한다 — 이번 브랜치에서 구현하지 않는다.

#### 7.15.1 `targetId` 대상 모호성 (착수 전 반드시 확인)

후기 작성·목록 조회·AI 만족도 요약 3개 엔드포인트 모두 요청에 `place`/`course` 구분 없이 **`targetId` 단일 필드**만 받는다(대상 타입을 알려주는 `targetType` 같은 필드가 없다). 반면 ERD의 `reviews` 테이블은 `tourist_spot_id`가 **NOT NULL**, `course_id`는 nullable이다.

**이번 스테이지는 ERD를 따라 `targetId`를 항상 `TouristSpot` PK로 해석한다.** `Review.place`는 필수 FK로 두고, 이번 API 3종만으로는 `course_id`를 채울 방법이 없다. 코스 단위 후기가 실제로 필요하면 `targetType` 파라미터 추가를 프론트와 협의해야 한다 — 이번 문서에서 임의로 추가하지 않는다(0절 원칙 2, 7.15.8 미해결 사항 1).

#### 7.15.2 모델

**`Review`**

| 필드 | 타입 | 비고 |
|---|---|---|
| `user` | FK to User | |
| `place` | FK to `places.TouristSpot` | ERD `tourist_spot_id`, NOT NULL — 7.15.1 참고 |
| `course` | FK to `courses.Course`, `null=True` | ERD `course_id`, nullable. 이번 3개 엔드포인트로는 채워지지 않음(7.15.1) |
| `rating` | `PositiveSmallIntegerField`, 1~5 | 요청의 `rating`(정수) |
| `content` | `TextField` | 요청 필드명은 `text` — 시리얼라이저에서 `text` → `content` 매핑 |
| `visit_date` | `DateField`, null 허용 | 요청의 `visitDate` |
| `weather_at_visit` | `CharField`, blank 허용 | 요청의 `visitWeather` |
| `like_count` | `PositiveIntegerField`, default 0 | ERD 캐시 컬럼. "후기 도움돼요" 호출 시 갱신(7.15.5) |

**`ReviewPhoto`** (ERD `review_photos`)

| 필드 | 타입 | 비고 |
|---|---|---|
| `review` | FK to `Review` | |
| `image_url` | `URLField` | 요청의 `photos: [string]` 배열 원소. URL 그대로 저장(Stage 2 `TouristSpotImage`와 동일 패턴) |
| `display_order` | `PositiveSmallIntegerField`, default 0 | 요청 배열 순서를 그대로 따른다 |

**`ReviewReaction`** (ERD `review_reactions`)

| 필드 | 타입 | 비고 |
|---|---|---|
| `review` | FK to `Review` | `(review, user)` unique |
| `user` | FK to User | |
| `reaction_type` | `CharField`, choices | 현재 확정된 액션은 "도움돼요" 하나뿐이라 `HELPFUL` 한 값만 사용한다 |

**`ReviewReport`** (ERD에는 없는 테이블 — API spec 기준으로 별도 유지)

| 필드 | 타입 | 비고 |
|---|---|---|
| `review` | FK to `Review` | |
| `user` | FK to User | |
| `reason` | `TextField` | 요청의 `reason` |
| `created_at` | `DateTimeField(auto_now_add=True)` | |

#### 7.15.3 에러 코드

| 코드 | 상태코드 | 메시지 | 발생 조건 |
|---|---|---|---|
| `RATING_REQUIRED` | 400 | 별점을 선택해주세요. | 후기 작성 시 `rating` 누락 |
| `PLACE_NOT_FOUND` | 404 | 장소 정보를 찾을 수 없습니다. | 후기 작성 시 `targetId`에 해당하는 `TouristSpot`이 없음(Stage 2 코드 재사용) |
| `REVIEW_NOT_FOUND` | 404 | 존재하지 않는 후기입니다. | 도움돼요/신고 요청의 `reviewId`가 없음 |

`AI 만족도·키워드 요약`의 `INSUFFICIENT_DATA`는 `ApiError`로 만들지 않는다 — HTTP 200 + 빈 `data`로 응답하는 정상 케이스(관광지 혼잡도 7.11.4와 동일 패턴).

#### 7.15.4 `POST /reviews` — 후기 작성

**요청**
```json
{ "targetId": "string", "rating": 0, "text": "string", "photos": ["string"], "visitDate": "string", "visitWeather": "string" }
```

**서비스 로직** (`reviews/services.py`, `create_review`)
1. `rating` 누락 시 `RATING_REQUIRED`.
2. `targetId`로 `TouristSpot` 조회(7.15.1) — 없으면 `PLACE_NOT_FOUND`.
3. `Review` 생성 후 `photos` 배열 순서대로 `ReviewPhoto` 일괄 생성.

**응답 `200`**: `{ "success": true, "data": { "reviewId": "1" }, "error": null }`

#### 7.15.5 `GET /reviews` — 후기 목록 조회 (`authorization: none`)

쿼리: `targetId`(필수), `sort`(`latest|rating`, 선택).

```json
{ "success": true, "data": { "reviews": [ { "reviewId": "1", "author": "여행자", "rating": 5, "text": "...", "photos": ["https://..."], "visitWeather": "맑음" } ] }, "error": null }
```

`author`는 작성자 `nickname`(6.4.3절과 동일). `sort=rating`은 내림차순, 기본은 최신순. 결과 없으면 `reviews: []`.

#### 7.15.6 `POST /reviews/{reviewId}/helpful` — 후기 도움돼요

**토글 방식으로 설계한다(Notion 명세에 명시는 없음, 이 문서의 설계 결정)**: 이미 해당 유저의 `ReviewReaction(reaction_type=HELPFUL)`이 있으면 삭제하고 `like_count` 감소, 없으면 생성하고 증가. 프론트가 취소 동작을 지원하지 않으면 add-only로 바꿔야 한다(7.15.8 미해결 사항 2).

**응답 `200`**: `{ "success": true, "data": { "count": 12 }, "error": null }`

#### 7.15.7 `POST /reviews/{reviewId}/report` — 후기 신고

**요청**: `{ "reason": "string" }`

`(review, user)` unique로 중복 신고를 막고, 이미 신고한 후기를 다시 신고하면 기존 신고를 그대로 성공 응답으로 처리한다(멱등).

**응답 `200`**: `{ "success": true, "data": { "reported": true }, "error": null }`

#### 7.15.8 `GET /reviews/summary` — AI 만족도·키워드 요약 (`authorization: none`)

쿼리: `targetId`(7.15.1과 동일하게 해석).

```json
{ "success": true, "data": { "score": 82, "keywords": { "positive": ["친절해요"], "negative": ["주차 불편"] } }, "error": null }
```

데이터 부족 시: `{ "success": true, "data": {}, "error": null }`. AI 연동 방식은 확정하지 않는다(미해결 사항 3). 완성되면 `places` 7.11.6절의 `reviewSummary` 고정값을 실제 값으로 교체해야 한다(7.11.8 미해결 사항 3과 연결).

**미해결 사항**
1. `targetId`가 코스 후기를 지원해야 하는지(7.15.1).
2. [확정] "도움돼요"는 토글 방식으로 동작한다(7.15.6).
3. [해결] AI 만족도·키워드 요약의 실제 분석 로직/연동 대상 — 7.21절(`feature/reviews-ai-summary`)에서 확정.
4. `places` 앱의 `avgRating`/`aiSatisfaction`/통합검색 `rating` 고정값 교체는 **7.21절에 포함하지 않고 별도 후속 이슈로 분리한다**(7.21.6).
5. `review_count` 캐시를 `TouristSpot`에 둘지 미정.

**테스트 관점** (`tests/test_reviews_*.py`, 신규)
- 후기 작성 성공/실패(`RATING_REQUIRED`/`PLACE_NOT_FOUND`).
- 후기 목록 조회 정렬 확인.
- 도움돼요 토글(증가/취소), `REVIEW_NOT_FOUND`.
- 신고 멱등 확인, `REVIEW_NOT_FOUND`.
- AI 만족도 — 데이터 충분/부족 케이스.

### 7.16 `interactions` 앱 상세 설계 (Stage 4 실행용, `feature/interactions-bookmark`)

> Notion API spec "찜하기 토글"(`50704d374d27825c967e8151fa82ed51`) 페이지 근거.

#### 7.16.1 모델

**`Bookmark`** (ERD `wishlists`)

| 필드 | 타입 | 비고 |
|---|---|---|
| `user` | FK to User | |
| `place` | FK to `places.TouristSpot` | `(user, place)` unique |
| `created_at` | `DateTimeField(auto_now_add=True)` | |

#### 7.16.2 에러 코드

| 코드 | 상태코드 | 메시지 | 발생 조건 |
|---|---|---|---|
| `PLACE_NOT_FOUND` | 404 | 장소 정보를 찾을 수 없습니다. | 찜하기 토글 요청의 `placeId`가 없음(Stage 2 코드 재사용) |

#### 7.16.3 `POST /places/{placeId}/like` — 찜하기 토글

1. `placeId`로 `TouristSpot` 조회 — 없으면 `PLACE_NOT_FOUND`.
2. `Bookmark(user, place)`가 있으면 삭제(`liked: false`), 없으면 생성(`liked: true`) — 후기 도움돼요(7.15.6)와 동일한 토글 패턴.

**응답 `200`**: `{ "success": true, "data": { "liked": true }, "error": null }`

**테스트 관점** (`tests/test_interactions_bookmark.py`, 신규)
- 찜하기 토글 최초 호출/재호출(취소), `PLACE_NOT_FOUND`.

### 7.17 `gamification` 앱 상세 설계 (Stage 5 실행용, `feature/gamification`)

> Notion "게이미피케이션" 그룹 API spec 6개 전부와 ERD를 근거로 한다. **중요**: `docs/roadmap.md` 5절에서 이미 정리했듯, "숨겨진 여행지"·"완주카드"는 ERD(`weather_unlocks`/`card_type`)와 실제 API 응답(`GET /courses/unlocked`의 `courseId`, `POST /cards/completion`의 `courseId` 필수)이 상충해 **API 계약을 우선**했다 — 코스 단위로 확정.

범위: **위치 체크인**(`POST /stamps/checkin`), **스탬프북 현황 조회**(`GET /stamps`), **숨겨진 여행지 목록 조회**(`GET /courses/unlocked`), **완주 카드 생성**(`POST /cards/completion`), **완주 카드 컬렉션 조회**(`GET /cards`), **완주 카드 공유**(`POST /cards/{cardId}/share`).

#### 7.17.1 스탬프 모델

**`Stamp`** (ERD `stamps` 방향 채택 — `RegionStamp` 마스터 테이블 없이 지역 코드를 choices로 직접 저장)

| 필드 | 타입 | 비고 |
|---|---|---|
| `user` | FK to User | `(user, city_code)` unique |
| `city_code` | `CharField`, choices | 전남 22개 시군 코드. 정확한 코드 체계는 착수 시 확인(미해결 사항 1) |
| `acquired_at` | `DateTimeField(auto_now_add=True)` | |

ERD의 `related_user_course_id`는 채택하지 않는다 — 체크인 요청이 `lat`/`lng`만 받고 `courseId`를 받지 않는다.

#### 7.17.2 숨겨진 여행지(코스) 모델

**`HiddenCourse`**: `course`(`OneToOneField` to `courses.Course`), `rarity`(choices `LEGENDARY`/`RARE`/`UNCOMMON`/`COMMON`), `unlock_condition`(`TextField`, 사람이 읽는 조건 설명 — 실제 매칭 로직은 서비스 계층).

**`UserHiddenCourseUnlock`**: `user` FK, `hidden_course` FK(`(user, hidden_course)` unique), `unlocked_at`.

#### 7.17.3 완주 카드 모델

**`CompletionCard`**: `user` FK, `course` FK(`(user, course)` unique), `user_photo`(`URLField`, null 허용, 요청의 `userPhoto`), `card_image_url`(`URLField`, `cardImageUrl`), `created_at`(`GET /cards` 응답의 `date`).

ERD `card_type` 기준 UNIQUE는 채택하지 않는다 — API 계약 전체가 "완주 한 코스당 카드 한 장"을 전제한다.

**완주 인증(7.12.3, `complete_course`)의 `cardId`와의 관계**: 완주 인증은 `CourseProgress`만 `COMPLETED`로 갱신할 뿐 `CompletionCard`를 생성하지 않는다 — 카드 생성은 사용자가 사진을 첨부해 별도로 호출하는 `POST /cards/completion`의 몫이다. 따라서 완주 인증 응답의 `cardId`는 이 스테이지 이후에도 계속 `null`이 맞다 — 두 API는 서로 다른 호출이므로 자동 연결되지 않는다.

#### 7.17.4 에러 코드

| 코드 | 상태코드 | 메시지 | 발생 조건 |
|---|---|---|---|
| `OUT_OF_REGION` | 400 | 해당 지역에서만 체크인할 수 있습니다. | 체크인 좌표가 전남 22개 시군 밖 |
| `COURSE_NOT_COMPLETED` | 400 | 완주하지 않은 코스입니다. | 완주 카드 생성 시 `CourseProgress.status`가 `COMPLETED`가 아님 |

`ALREADY_ACQUIRED`는 `ApiError`가 아니다 — HTTP 200 + `data.stampAcquired: false`인 정상 케이스.

#### 7.17.5 엔드포인트

**`POST /stamps/checkin`**: `{lat,lng}` → 좌표→시군 코드 변환(방식 미확정, 미해결 사항 2) 후 매칭 없으면 `OUT_OF_REGION`. 이미 보유하면 `{stampAcquired:false, cityCode}`(200), 없으면 생성 후 `{stampAcquired:true, cityCode}`.

**`GET /stamps`**: `{collected, totalCount:22, progress}`. `progress`는 `round(len(collected)/22*100)`(가정, 미해결 사항 3).

**`GET /courses/unlocked`** — query `lat`,`lng`: 주변 `HiddenCourse` 전체를 유저의 `UserHiddenCourseUnlock` 존재 여부로 `unlockedCourses`/`lockedCourses` 분리. "주변" 반경 미확정(미해결 사항 4).

**`POST /cards/completion`**: `{courseId, userPhoto}` → 해당 유저의 `CourseProgress(course_id=courseId)`가 `COMPLETED`가 아니면 `COURSE_NOT_COMPLETED`. 통과 시 `CompletionCard` upsert, `{cardId, cardImageUrl}` 응답. 이미지 합성 로직 미확정(미해결 사항 5).

**`GET /cards`**: `{cards:[{cardId, courseName, date, imageUrl}]}`.

**`POST /cards/{cardId}/share`**: 저장 없이 URL만 생성한다는 점은 코스 공유(7.12.3 `share_course`)와 같지만, 소유자 검증이 있다는 점은 다르다 — 7.17.8에서 리뷰 결과로 확정(요청 사용자의 카드가 아니면 공통 404). 전용 에러코드는 두지 않는다(미해결 사항 6).

#### 7.17.6 미해결 사항

1. `Stamp.city_code` 코드 체계 미확정. **[해결, 7.17.7]**
2. 좌표→시군 판별(reverse geocoding) 방식 미확정. **[해결, 7.17.7]**
3. `GET /stamps`의 `progress` 단위(퍼센트 vs 비율) 가정. **[해결, 7.17.7]**
4. `GET /courses/unlocked`의 "주변" 반경 미확정. **[해결, 7.17.8]**
5. 완주 카드 이미지 합성 로직 미확정. **[해결, 7.17.8]**
6. 완주 카드 공유의 `cardId` 없음 케이스 전용 에러코드 여부 미정. **[해결, 7.17.8]**

**테스트 관점** (`tests/test_gamification_*.py`, 신규)
- 체크인 성공/이미획득/`OUT_OF_REGION`.
- 스탬프북 조회 값 확인.
- 숨겨진 여행지 unlock 분리 확인.
- 완주 카드 생성 성공/`COURSE_NOT_COMPLETED`.
- 완주 카드 컬렉션 조회, 공유 확인.

#### 7.17.7 위치 체크인/스탬프북 실행 결과 (`feature/gamification-stamps`)

> 이 브랜치는 `gamification` 앱의 범위 중 `POST /stamps/checkin`·`GET /stamps` 2개 엔드포인트만 구현한다. 7.17.2~7.17.3의 숨겨진 여행지·완주 카드(모델 3종, 엔드포인트 4개)는 같은 앱에 추가할 후속 이슈로 남긴다(0절 원칙 1) — 7.17.6의 미해결 사항 4~6은 그 이슈에서 다룬다.

- **미해결 사항 1 [해결] — `Stamp.city_code` 코드 체계.** 새 코드 체계를 만들지 않고 `places/tourist_congestion.py`의 `SIGUNGU_NAME_TO_CODE`(전남 22개 시군 이름→법정동코드 앞5자리, 예: `"여수시": "46130"`)를 그대로 재사용한다 — 이미 관광지 혼잡도 연동(7.11)에서 검증된 전남 22개 시군 매핑이라 새 코드 체계를 도입하는 것은 불필요한 재구현이다(0절 원칙 3). `Stamp.city_code`의 `choices`는 `[(code, name) for name, code in SIGUNGU_NAME_TO_CODE.items()]`로 구성한다(`gamification/models.py`). `places/tourapi.py`에도 이름은 같지만 코드 값이 다른 별도의 `SIGUNGU_CODE_TO_NAME`(TourAPI 자체 코드, `"1".."24"`)이 있으므로 혼동하지 않는다 — 이번 재사용 대상은 `tourist_congestion.py` 쪽(법정동코드, 카카오 로컬 API 응답과 호환)이다.
- **미해결 사항 2 [해결] — reverse geocoding 방식.** 카카오 로컬 API `좌표로 행정구역정보 받기`(`GET https://dapi.kakao.com/v2/local/geo/coord2regioncode.json`)를 `gamification/kakao_local.py`의 `KakaoLocalClient`로 새로 감싼다. 인증은 기존 `settings.KAKAO_REST_API_KEY`(계정 소셜 로그인용으로 이미 선언돼 있었으나 미사용이던 값)를 그대로 쓰고, 새 API 키·env를 추가하지 않는다(이슈 지시). `KakaoMobilityClient`(7.14.3)처럼 base_url/timeout을 `settings`로 노출하는 대신 이번엔 모듈 상수로 고정했다 — "신규 env 없음" 지시를 코드로 강제하기 위함이며, 다른 카카오 어댑터와 달리 이 엔드포인트는 변경될 일이 없는 고정 API 경로라 설정으로 뺄 이유가 약하다.
  - 응답의 `documents` 중 `region_type: "B"`(법정동) 문서만 사용하고, `region_1depth_name`이 `"전라남도"`가 아니거나 `region_2depth_name`이 `SIGUNGU_NAME_TO_CODE`에 없으면 매칭 실패로 취급한다.
  - HTTP 실패·매칭 실패를 구분하지 않고 둘 다 `get_city_code`가 `None`을 반환하도록 통일했다 — 이슈 세부 작업 순서 5번이 "좌표→시군코드 변환 실패/매칭없음 시 OUT_OF_REGION"으로 두 경우를 같은 에러로 명시했기 때문이다.
- **미해결 사항 3 [해결] — `progress` 단위.** 가정대로 퍼센트로 확정한다: `round(len(collected) / 22 * 100)`. 22는 `TOTAL_STAMP_COUNT` 상수로 고정한다(`SIGUNGU_NAME_TO_CODE`의 길이에서 파생시키지 않음 — "전남 22개 시군 완주"는 코드 목록과 별개로 고정된 도메인 사실이라, 목록이 바뀌어도 이 상수가 조용히 따라 바뀌면 안 된다).
- 체크인 동시성은 `Stamp.objects.get_or_create(user=user, city_code=city_code)` 하나로 처리한다. `get_or_create`는 내부적으로 `IntegrityError` 재조회를 이미 포함하므로 `interactions.toggle_bookmark`(7.16.3)처럼 별도 `try/except IntegrityError`를 추가하지 않는다.

### 7.17.8 숨겨진 여행지·완주 카드 상세 설계 (`feature/gamification-cards`)

> 7.17.2~7.17.3에서 남겨둔 `HiddenCourse`/`UserHiddenCourseUnlock`/`CompletionCard` 모델 3종과 엔드포인트 4개(`GET /courses/unlocked`, `POST /cards/completion`, `GET /cards`, `POST /cards/{cardId}/share`)를 같은 `gamification` 앱에 추가한다(7.17.7의 예고대로, 0절 원칙 1). `Stamp`와는 독립된 서브도메인이라 이번 브랜치 코드는 `Stamp`를 참조하지 않는다. 근거는 Notion API spec "숨겨진 여행지(날씨 해금) 목록 조회"(`cc204d374d278226923e01e0e253afc0`)·"완주 카드 생성"(`6b404d374d2782789f3d01c250a9cfdd`)·"완주 카드 컬렉션 조회"(`48f04d374d278368b46e015a7e5f8ee6`)·"완주 카드 공유"(`1bc04d374d2782dd97968156d0993eb8`) 4개 페이지다. 이 4개 페이지의 실제 REQUEST/RESPONSE 예시를 착수 전에 재확인한 결과, 기존 7.17.5의 서술과 필드 단위까지 일치함을 확인했다 — 아래는 그 예시를 그대로 반영한 확정 스펙이다.

**착수 전 결정 두 가지**(이슈에서 이미 확정, 근거만 기록):

- **완주 카드 이미지 합성 안 함.** `cardImageUrl`은 요청의 `userPhoto`를 그대로 반환한다. 등급별 카드 템플릿 합성은 디자인 리소스가 없어 이번 스테이지 범위 밖이다 — 준비되면 별도 이슈(미해결 사항 5).
- **"주변" 반경 필터링 안 함.** `GET /courses/unlocked`의 `lat`/`lng`는 Notion 계약상 필수 쿼리 파라미터라 시리얼라이저 검증은 하지만, 서비스 로직은 이 값을 사용하지 않는다 — 전남 22개 시군 전체가 이미 서비스 범위이므로 `HiddenCourse` 전체를 유저의 `UserHiddenCourseUnlock` 존재 여부로만 나눈다(미해결 사항 4). 반경 필터링이 실제로 필요해지면(예: 프론트가 "내 주변" 배지를 원함) 별도 이슈에서 `places.services.calculate_distance_km`(7.12.3에서도 재사용한 haversine 유틸)로 추가한다.

#### 모델 (`gamification/models.py` 추가, 새 마이그레이션 1개)

**`HiddenCourse`**

| 필드 | 타입 | 비고 |
|---|---|---|
| `course` | `OneToOneField` to `courses.Course`, `on_delete=CASCADE` | 코스 1개당 숨겨진 여행지 설정 최대 1건 |
| `rarity` | `CharField`, choices `LEGENDARY`/`RARE`/`UNCOMMON`/`COMMON` | `unlockedCourses[].rarity` |
| `unlock_condition` | `TextField`, blank 허용 | `lockedCourses[].unlockCondition` — 사람이 읽는 조건 설명. 실제 조건 매칭(날씨/계절 등)을 자동 판정하는 로직은 이번 스테이지 범위 밖이다: `UserHiddenCourseUnlock` 레코드를 만드는 주체(관리자 수동 지정 또는 별도 배치)는 아직 없고, 이번 브랜치는 "이미 해금된 사람"과 "아직 해금 안 된 사람"을 나눠 보여주는 조회 API만 만든다 — Notion 계약에 해금 판정을 트리거하는 엔드포인트가 없다(0절 원칙 2). |

**`UserHiddenCourseUnlock`**

| 필드 | 타입 | 비고 |
|---|---|---|
| `user` | FK to `accounts.User`, `on_delete=CASCADE`, `related_name="hidden_course_unlocks"` | |
| `hidden_course` | FK to `HiddenCourse`, `on_delete=CASCADE`, `related_name="unlocks"` | |
| `unlocked_at` | `DateTimeField(auto_now_add=True)` | |

`Meta.constraints = [UniqueConstraint(fields=["user", "hidden_course"])]`.

**`CompletionCard`**

| 필드 | 타입 | 비고 |
|---|---|---|
| `user` | FK to `accounts.User`, `on_delete=CASCADE`, `related_name="completion_cards"` | |
| `course` | FK to `courses.Course`, `on_delete=CASCADE`, `related_name="completion_cards"` | |
| `user_photo` | `URLField`, null/blank 허용 | 요청의 `userPhoto` |
| `card_image_url` | `URLField` | 응답의 `cardImageUrl`. 이번 스테이지는 `user_photo`와 항상 같은 값 |
| `created_at` | `DateTimeField(auto_now_add=True)` | `GET /cards` 응답의 `date` |

`Meta.constraints = [UniqueConstraint(fields=["user", "course"])]` — "완주 한 코스당 카드 한 장", ERD `card_type` 기준 UNIQUE는 7.17.3에서 이미 기각.

#### 에러 코드

`COURSE_NOT_COMPLETED`(400, "완주하지 않은 코스입니다.")를 `common/exceptions.py`의 `ErrorCode`에 추가(7.17.4에 이미 정의돼 있었으나 코드에는 반영 전이었다). 전용 `CARD_NOT_FOUND`류 코드는 추가하지 않는다(미해결 사항 6, 아래).

#### 서비스 계층 (`gamification/services.py` 추가)

**`get_unlocked_courses(*, user) -> dict`**
1. `HiddenCourse.objects.all()` 전체를 조회한다(반경 필터링 없음, 위 결정 참고).
2. `UserHiddenCourseUnlock.objects.filter(user=user).values_list("hidden_course_id", flat=True)`로 이 유저가 해금한 `hidden_course_id` 집합을 구한다.
3. 각 `HiddenCourse`를 그 집합에 있으면 `{"courseId": hc.course_id, "rarity": hc.rarity}`로 `unlockedCourses`에, 없으면 `{"courseId": hc.course_id, "unlockCondition": hc.unlock_condition}`로 `lockedCourses`에 담는다. `courseId`는 `hc.course_id`(코스 PK) — `hc.pk`(`HiddenCourse` 자체 PK)가 아니다, Notion 응답이 코스 단위이기 때문(7.17.1 상단 결정과 동일 원칙).
4. `{"unlockedCourses": [...], "lockedCourses": [...]}` 반환.

**`create_completion_card(*, user, course_id, user_photo) -> CompletionCard`**
1. `courses.models.CourseProgress.objects.filter(user=user, course_id=course_id).first()`로 진행 기록을 조회한다. 기록이 없거나 `status != CourseProgress.Status.COMPLETED`면 `ApiError(ErrorCode.COURSE_NOT_COMPLETED)`. `courseId` 자체가 존재하지 않는 코스를 가리키는 경우도 자연히 이 분기로 걸러진다 — `Course.DoesNotExist`를 별도로 잡는 전용 404 처리는 추가하지 않는다(Notion 에러 코드 표에 `COURSE_NOT_FOUND`가 없다, 0절 원칙 2).
2. `CompletionCard.objects.update_or_create(user=user, course_id=course_id, defaults={"user_photo": user_photo, "card_image_url": user_photo})` — 같은 코스로 재요청하면 사진만 갱신(멱등), `courses.services.save_course`(7.12.3)와 같은 upsert 패턴.
3. 반환.

**`share_completion_card(*, user, card_id) -> str`** — **[7.17.8 최초 확정 이후 코드 리뷰로 수정, 2026-08-10]** 최초 확정판은 `share_course`(7.12.3, 소유자 무관 공개 공유)와 동일 패턴으로 `card_id`만 받았으나, `CompletionCard`는 `Course`와 달리 `user_photo`(개인 사진)를 담은 개인 소유 리소스라는 점이 리뷰에서 지적됐다 — `card_id`가 순차 정수 PK라 소유자 검증이 없으면 로그인한 임의의 사용자가 남의 `cardId`를 넣어 존재 여부·`shareUrl`을 얻어갈 수 있는 IDOR이 된다. `courses.share_course`는 코스(공개돼도 무방한 여행 정보)를 다루므로 소유자 무관 설계가 맞지만, 완주 카드는 그 전제가 성립하지 않는다고 판단해 아래로 확정한다.
1. `CompletionCard.objects.get(pk=card_id, user=user)` — 소유자 조건을 쿼리에 포함한다. 본인 카드가 아니거나 애초에 존재하지 않는 `card_id`나 동일하게 `DoesNotExist`가 발생하므로 `ApiError(ErrorCode.COMMON_404)`로 변환한다. **타인 카드의 존재 여부를 구분해서 알려주지 않는다** — "존재하지만 내 것이 아님"과 "존재하지 않음"을 다른 응답으로 구분하면 그 자체로 카드 존재 여부를 흘리는 사이드채널이 되므로, 두 경우 모두 동일한 404로 응답한다. 전용 에러코드를 새로 만들지 않고 기존 `COMMON_404`를 그대로 쓰는 결론(미해결 사항 6)은 유지 — Notion "완주 카드 공유" 페이지의 에러 코드 표가 "공통 에러 코드만 해당"이라고 명시하기 때문이다.
2. `f"{settings.CARD_SHARE_BASE_URL}/{card.id}"` 반환. `COURSE_SHARE_BASE_URL`(7.12.6)을 그대로 재사용하지 않고 `CARD_SHARE_BASE_URL`을 새로 둔다 — 코스 공유 URL 경로(`/courses/{id}`)와 카드 공유 URL 경로(`/cards/{id}`)는 프론트 라우팅상 서로 다른 리소스라 값도 달라야 하기 때문이며, 선언 방식은 7.12.6과 완전히 동일한 패턴(placeholder, `.env.example`/`config/settings.py`에 한 쌍 추가)을 따른다.

뷰(`CompletionCardShareView.post`)는 `share_completion_card(user=request.user, card_id=cardId)`로 호출한다 — 다른 3개 엔드포인트와 마찬가지로 `IsAuthenticated`만으로는 부족하고, 서비스 호출 시 반드시 `request.user`를 넘겨야 한다.

```python
# config/settings.py, COURSE_SHARE_BASE_URL 바로 아래
CARD_SHARE_BASE_URL = env(
    "CARD_SHARE_BASE_URL",
    default="https://eodiganam.app/cards",
)
```

```
# .env.example, COURSE_SHARE_BASE_URL 바로 아래
CARD_SHARE_BASE_URL=https://eodiganam.app/cards
```

**`GET /cards` 목록**은 서비스 함수를 따로 두지 않고 뷰에서 바로 조회한다(7.17.5의 `GET /stamps`처럼 단순 조회라 서비스 계층 분리가 과하다): `CompletionCard.objects.filter(user=request.user).select_related("course").order_by("-id")` — 최신 카드가 먼저 나오도록, `reviews.services`(7.15)의 기본 목록 정렬(`-id`)과 동일한 관례를 따른다.

#### 시리얼라이저 (`gamification/serializers.py` 추가)

```python
class HiddenCourseUnlockedQuerySerializer(serializers.Serializer):
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lng = serializers.FloatField(min_value=-180, max_value=180)


class CompletionCardCreateSerializer(serializers.Serializer):
    courseId = serializers.IntegerField()
    userPhoto = serializers.URLField()
```

`lat`/`lng`는 `StampCheckinSerializer`(7.17절 기존 코드)와 동일한 범위 검증을 재사용하되, 서비스에는 전달하지 않는다(위 결정). 나머지 응답 필드는 `inline_serializer`로 뷰에 직접 선언한다 — `StampCheckinView`(기존 코드)와 동일한 관례.

#### 뷰 (`gamification/views.py` 추가, 4개 전부 `IsAuthenticated`)

| API | Endpoint | 뷰 |
|---|---|---|
| 숨겨진 여행지 목록 조회 | `GET /api/v1/courses/unlocked` | `HiddenCourseUnlockedView` |
| 완주 카드 생성 | `POST /api/v1/cards/completion` | `CompletionCardCreateView` |
| 완주 카드 컬렉션 조회 | `GET /api/v1/cards` | `CompletionCardListView` |
| 완주 카드 공유 | `POST /api/v1/cards/{cardId}/share` | `CompletionCardShareView` |

`CompletionCardListView`는 `select_related("course")`한 쿼리셋을 `{"cards": [{"cardId": c.id, "courseName": c.course.name, "date": c.created_at, "imageUrl": c.card_image_url} for c in ...]}` 형태로 직접 조립한다(별도 `ModelSerializer` 없이 `StampbookView`와 같은 관례).

#### URL 등록 (`gamification/urls.py` 추가)

4개 다 `gamification/urls.py`에 전체 경로(full path)로 직접 추가한다 — `courses/urls.py`(prefix `api/v1/courses/`, path param `<int:courseId>/...` 4개)를 건드리지 않는다. `HiddenCourse`는 `courses` 도메인이 아니라 `gamification` 도메인 소유이므로, 기존 `StampCheckinView`/`StampbookView`가 `api/v1/stamps/...` 전체 경로를 직접 선언한 것과 같은 관례를 그대로 따른다(0절 원칙 3 — 앱 경계를 지키기 위해 새 파일을 쪼개지 않되, `courses` 앱에 종속시키지도 않는다). `config/urls.py`의 `path("", include("gamification.urls"))`가 `path("api/v1/courses/", include("courses.urls"))`보다 뒤에 등록돼 있어도 문제없다 — Django `URLResolver`는 `include()`로 진입한 하위 패턴이 전부 매치 실패(`Resolver404`)하면 그 예외가 상위 루프까지 전파돼 다음 최상위 패턴(`gamification.urls`)으로 자연히 넘어간다. `unlocked`는 `courses.urls`의 `<int:courseId>/save`류 2세그먼트 패턴과 세그먼트 수 자체가 달라 오매치 걱정도 없다.

```python
urlpatterns = [
    path("api/v1/stamps/checkin", StampCheckinView.as_view(), name="stamps-checkin"),
    path("api/v1/stamps", StampbookView.as_view(), name="stamps-status"),
    path("api/v1/courses/unlocked", HiddenCourseUnlockedView.as_view(), name="courses-unlocked"),
    path("api/v1/cards/completion", CompletionCardCreateView.as_view(), name="cards-completion"),
    path("api/v1/cards", CompletionCardListView.as_view(), name="cards-list"),
    path("api/v1/cards/<int:cardId>/share", CompletionCardShareView.as_view(), name="cards-share"),
]
```

#### 관리자 (`gamification/admin.py` 추가)

`HiddenCourse`/`CompletionCard`를 `StampAdmin`과 같은 패턴으로 등록(`UserHiddenCourseUnlock`은 `HiddenCourse` 인라인으로 노출할 수도 있으나, 이번 스테이지는 최소한으로 모델 3개 다 개별 `ModelAdmin` 등록만 한다 — 인라인 편집 UX는 요구되지 않았다).

#### 응답 예시 (Notion 원문 그대로)

```json
// GET /courses/unlocked
{
  "success": true,
  "data": {
    "unlockedCourses": [{ "courseId": 1, "rarity": "RARE" }],
    "lockedCourses": [{ "courseId": 2, "unlockCondition": "비 오는 날 방문" }]
  },
  "error": null
}
```

```json
// POST /cards/completion  { "courseId": 1, "userPhoto": "https://..." }
{ "success": true, "data": { "cardId": 1, "cardImageUrl": "https://..." }, "error": null }
```

```json
// GET /cards
{
  "success": true,
  "data": { "cards": [{ "cardId": 1, "courseName": "여수 밤바다 코스", "date": "2026-08-09T10:00:00Z", "imageUrl": "https://..." }] },
  "error": null
}
```

```json
// POST /cards/{cardId}/share
{ "success": true, "data": { "shareUrl": "https://eodiganam.app/cards/1" }, "error": null }
```

**테스트 관점** (`tests/test_gamification_cards.py`, 신규 — 7.17.7의 `test_gamification_stamps.py`와 분리)
- 숨겨진 여행지 목록: 해금/미해금 fixture 각각 준비 후 `unlockedCourses`/`lockedCourses` 분리와 필드(`rarity` vs `unlockCondition`) 확인.
- 완주 카드 생성: `CourseProgress.status=COMPLETED` fixture로 성공(`cardId`/`cardImageUrl=userPhoto` 확인) / 기록 없음·`SAVED`·`IN_PROGRESS` 각각 `COURSE_NOT_COMPLETED`(400) 확인 / 같은 코스 재요청 시 카드 upsert(행 1개 유지) 확인.
- 완주 카드 컬렉션 조회: 본인 카드만 노출, `courseName`/`date`/`imageUrl` 필드 확인, 정렬(최신순) 확인.
- 완주 카드 공유: 본인 카드 `shareUrl` 생성 확인 / 존재하지 않는 `cardId`는 404 / **타인 카드의 `cardId`를 넣어도 404**(소유자 검증, 2026-08-10 리뷰 반영) 확인.

### 7.18 `mypage` 앱 상세 설계 (Stage 6 실행용, `feature/mypage`)

> Notion "마이페이지" 그룹 API spec 6개 확정 경로(`/users/me/...`) 근거.

#### 7.18.1 착수 전 확인 필요 — `accounts.User` 필드 보강

**`PATCH /users/me`(프로필 수정) 요청에 `profileImg`가 있는데, Stage 1에서 구현된 `accounts.User`(`accounts/models.py`)에는 프로필 이미지 필드가 없다.** 이번 스테이지에서 `accounts.User.profile_img`(`URLField`, null/blank 허용) 필드와 마이그레이션을 추가해야 한다.

또한 `PATCH /users/me`는 `NICKNAME_DUPLICATE`(409) 에러를 정의하는데, 실제 구현된 `accounts.User.nickname`은 `CharField(max_length=50)`로 `unique` 제약이 없다(`accounts/models.py:11`). 이번 스테이지에서 `nickname`에 `unique=True` 마이그레이션을 추가해야 하며, 기존 데이터에 중복 닉네임이 있으면 마이그레이션이 실패하므로 착수 전에 실제 DB를 확인해야 한다(미해결 사항 1).

#### 7.18.2 엔드포인트

| API | Endpoint | 비고 |
|---|---|---|
| 내 프로필·활동요약 조회 | `GET /users/me` | `profile:{nickname, profileImg}`, `stats:{completedCourses, stamps, reviews}` |
| 프로필 수정 | `PATCH /users/me` | `{nickname, profileImg}` → `{updated:true}`, `NICKNAME_DUPLICATE`(409) |
| 저장한 코스 목록 조회 | `GET /users/me/courses` | `{courses:[{courseId, name}]}` |
| 내 후기 목록 조회 | `GET /users/me/reviews` | `{reviews:[{reviewId, targetName, rating}]}` |
| 찜 목록 조회 | `GET /users/me/likes` | `{places:[{placeId, name}]}` |

(찜하기 자체는 `POST /places/{placeId}/like`로 `interactions` 앱 소관, 7.16절.)

#### 7.18.3 서비스 로직

- **`GET /users/me`**: `stats.completedCourses`는 `CourseProgress.objects.filter(user=..., status="COMPLETED").count()`, `stats.stamps`는 `Stamp.objects.filter(user=...).count()`, `stats.reviews`는 `Review.objects.filter(user=...).count()`.
- **`PATCH /users/me`**: `nickname` 변경 시 자신을 제외한 중복 검사 후 `NICKNAME_DUPLICATE`(signup의 `DUPLICATE_ID` 검증과 동일 패턴, 6.2절).
- **`GET /users/me/courses`**: `CourseProgress.objects.filter(user=request.user, status__in=["SAVED","IN_PROGRESS","COMPLETED"])` → `course.name`.
- **`GET /users/me/reviews`**: `Review.objects.filter(user=request.user)` → `targetName`은 `review.place.name`.
- **`GET /users/me/likes`**: `Bookmark.objects.filter(user=request.user)` → `place.id`/`place.name`.
- **목록 정렬 기준**: 저장 코스는 `CourseProgress.updated_at` 내림차순(최근 활동 순), 후기는 `Review.id` 내림차순(기존 후기 목록 기본 정렬과 동일), 찜은 `Bookmark.created_at` 내림차순(최근 찜한 순).

**미해결 사항 갱신**
1. **[해결]** `nickname` unique 마이그레이션 전 현재 Docker MySQL에서 중복을 확인했고 결과는 `[]`였다. 데이터 수정 없이 `profile_img` 추가(`accounts.0004`)와 `nickname unique` 적용(`accounts.0005`)을 별도 마이그레이션으로 분리했다.
2. **[해결]** `profileImg`는 URL 문자열로 확정한다. 파일 업로드 엔드포인트는 두지 않으며 `ReviewPhoto.image_url`/`CompletionCard.card_image_url`과 같은 외부 업로드·백엔드 URL 저장 패턴을 따른다.
3. **[후속]** 목록 3종의 페이지네이션·응답 상한은 Notion 요청/응답 계약에 파라미터가 없어 이번 이슈에서 임의로 추가하지 않는다. 운영 데이터 증가 전에 공통 페이지네이션 계약을 정하고 별도 이슈로 적용한다.

**테스트 관점** (`tests/test_mypage_*.py`, 신규)
- 프로필·활동요약 조회, 프로필 수정 성공/`NICKNAME_DUPLICATE`.
- 저장한 코스/내 후기/찜 목록 — 본인 데이터만 노출 확인.

### 7.19 `home` 앱 상세 설계 (Stage 6 실행용, `feature/home`)

> Notion "Home" 그룹 API spec 2개 확정 경로 근거. `authorization: none`.

#### 7.19.1 엔드포인트

**`GET /weather/current`** — query `lat`,`lng`: `{weatherType, temp, icon}`. 에러: `WEATHER_FETCH_FAILED`(502).

**`GET /home`** — query `lat`,`lng`: `{weather:{type,temp,icon}, recommendedCourses:[{courseId,name,duration,distance,thumbnail}], unlockBanner:{available}}`. 에러: `WEATHER_FETCH_FAILED`(502).

#### 7.19.2 서비스 로직

- **날씨**: 기상청(KMA) 연동 — API 종류·좌표→격자 변환 미확정(미해결 사항 1). `home/kma.py` 어댑터로 분리, 실패 시 `WEATHER_FETCH_FAILED` 변환.
- **추천 코스**: 선정 기준 미확정(미해결 사항 2).
- **`unlockBanner.available`**: 요청 좌표 기준 아직 잠금 해제 안 된 `gamification.HiddenCourse` 존재 여부(`GET /courses/unlocked`의 `lockedCourses`와 같은 조회, 7.17.5) — `gamification`(Stage 5) 완료 선행 필요.

**미해결 사항**
1. 기상청 API 연동 방식 미확정.
2. `recommendedCourses` 선정 기준 미확정.
3. `courses`(Stage 3)·`gamification`(Stage 5) 의존 — `/weather/current`만 먼저 만들고 `/home`은 미루는 분할도 고려.

**테스트 관점**: 현재 날씨 성공/실패(`WEATHER_FETCH_FAILED`), 메인 홈 데이터 필드 확인.

### 7.20 `common` 앱 상세 설계 (Stage 6 실행용, `feature/common-settings`)

> Notion "공통" 그룹 API spec 2개 확정 경로 근거.

#### 7.20.1 모델

**`UserSettings`**: `user`(`OneToOneField`), `push_notification_enabled`(응답 `notifications.push`), `golden_hour_notification_enabled`(응답 `notifications.goldenHour`, 정확한 정의 미해결 사항 1), `language`(choices `ko`/`en`/`ja`/`zh`), `location_permission_granted`(응답 `permissions.location` — OS 권한이 아니라 사용자 동의 값으로 해석, 미해결 사항 2).

#### 7.20.2 엔드포인트

**`GET /settings`**: `{notifications:{push,goldenHour}, language, permissions:{location}}`.

**`PATCH /settings`**: 동일 구조 요청 → `{updated:true}`. `UserSettings.objects.get_or_create(user=request.user)`로 최초 접근 시 기본값 생성.

**미해결 사항**
1. `goldenHour` 알림 정확한 정의는 기능명세서 재확인 필요.
2. `permissions.location`의 정확한 의미 재확인 필요.

**테스트 관점**: 최초 접근 시 기본값 자동 생성, 설정 변경 각 필드 갱신 확인.

### 7.21 `reviews` 앱 AI 만족도·키워드 요약 상세 설계 (`feature/reviews-ai-summary`)

> Notion "AI 만족도·키워드 요약"(`00504d374d27826496f481a2e8f4e0c1`) 페이지 근거. 7.15에서 "AI 연동 방식 미확정"을 이유로 분리해 둔 `GET /reviews/summary` 1개 엔드포인트를 이번 브랜치에서 구현한다. 새 모델은 캐시 테이블(7.21.3) 하나뿐이고, `targetId` 해석은 7.15.1과 동일하게 `TouristSpot` PK다.

#### 7.21.1 AI 연동 방식 결정 (착수 전 필수 결정)

- **[해결] 외부 LLM 재사용.** `courses/ai_recommend.py`(7.13.4)와 동일하게 OpenAI 호환 Chat Completions API를 `requests`로 직접 호출한다. `courses` 앱을 위해 이미 도입된 `LLM_API_BASE_URL`/`LLM_API_KEY`/`LLM_API_MODEL`/`LLM_API_TIMEOUT_SEC` 환경변수를 그대로 재사용하므로 `.env.example`/`config/settings.py` 변경이 없다. 자체 키워드 사전 방식(대안 A)은 채택하지 않는다 — 한국어 형태소 처리 없이는 품질이 낮고, 이미 검증된 어댑터 패턴이 있는데 별도 방식을 새로 들이는 것은 불필요한 재구현이다(0절 원칙 3).
- **[해결] 캐시 도입.** 리뷰가 적은 장소에서 매 요청마다 LLM을 호출하면 비용·지연이 크므로, 7.21.3의 `ReviewSummaryCache`로 재계산 빈도를 제한한다.

#### 7.21.2 `reviews/ai_summary.py` — AI 어댑터

`places/tourapi.py`·`courses/ai_recommend.py`와 같은 자리 규칙(7.13.4)의 외부 연동 어댑터다.

```python
class AISummaryError(Exception):
    pass

@dataclass(frozen=True)
class ReviewSummaryResult:
    score: int              # 0~100
    positive: list[str]
    negative: list[str]

class AISummaryClient:
    def __init__(self):
        self.base_url = settings.LLM_API_BASE_URL.rstrip("/")
        self.api_key = settings.LLM_API_KEY
        self.model = settings.LLM_API_MODEL
        self.timeout = settings.LLM_API_TIMEOUT_SEC

    def summarize(self, *, reviews: list[str]) -> ReviewSummaryResult:
        raise NotImplementedError
```

- 리뷰 `content` 텍스트 목록을 system/user 메시지로 구성해 `response_format: json_object`로 `{"score": int, "positive": [...], "negative": [...]}` 형태를 요청한다(`courses/ai_recommend.py`의 프롬프트 구성과 동일 패턴).
- 리뷰가 많은 장소는 프롬프트가 비대해지므로 최신순 최대 50개까지만 잘라 보낸다.
- HTTP 실패, JSON 파싱 실패, `score`가 0~100 범위 밖, `positive`/`negative`가 리스트가 아님 → 전부 `AISummaryError`로 변환한다(`courses/ai_recommend.py`의 `_parse_recommendation`과 동일하게 `_parse_summary`에서 일괄 검증).

#### 7.21.3 캐시 모델 — `ReviewSummaryCache`

```python
class ReviewSummaryCache(models.Model):
    place = models.OneToOneField(
        "places.TouristSpot", on_delete=models.CASCADE,
        related_name="review_summary_cache",
    )
    score = models.PositiveSmallIntegerField()
    positive_keywords = models.JSONField(default=list)
    negative_keywords = models.JSONField(default=list)
    review_count_at_calc = models.PositiveIntegerField()
    updated_at = models.DateTimeField(auto_now=True)
```

- `reviews` 앱에 신설한다 — `places.TouristSpot`에 필드를 추가하지 않는다. 이번 브랜치 범위를 reviews 쪽으로 한정한다(0절 원칙 1).
- `place` 1:1 — 장소당 캐시 레코드 1개.
- **재계산 조건**: 캐시가 없거나, 현재 리뷰 수가 `review_count_at_calc`보다 `RECOMPUTE_INTERVAL`(=5) 이상 늘었을 때만 LLM을 다시 호출한다. 그 외에는 캐시값을 그대로 응답한다.
- **최소 데이터 조건**: 리뷰 수가 `MIN_REVIEWS_FOR_SUMMARY`(=5) 미만이면 캐시 존재 여부와 무관하게 항상 `INSUFFICIENT_DATA`(빈 `data`)를 응답한다 — 캐시가 이미 있어도 이후 리뷰가 신고 등으로 삭제되어 임계값 아래로 떨어지면 빈 응답으로 되돌아간다.
- `MIN_REVIEWS_FOR_SUMMARY`·`RECOMPUTE_INTERVAL` 두 상수는 Notion 명세에 없는 이번 문서의 임의 결정이다 — 운영 데이터로 조정이 필요하다(7.21.6).

#### 7.21.4 서비스 계층 (`reviews/services.py`, `get_review_summary`)

```python
MIN_REVIEWS_FOR_SUMMARY = 5
RECOMPUTE_INTERVAL = 5

def get_review_summary(*, target_id) -> dict:
    reviews = list(Review.objects.filter(place_id=target_id).order_by("-id"))
    count = len(reviews)
    if count < MIN_REVIEWS_FOR_SUMMARY:
        return {}

    cache = ReviewSummaryCache.objects.filter(place_id=target_id).first()
    if cache and count - cache.review_count_at_calc < RECOMPUTE_INTERVAL:
        return _serialize(cache)

    try:
        result = AISummaryClient().summarize(reviews=[r.content for r in reviews[:50]])
    except AISummaryError:
        if cache:
            return _serialize(cache)   # 실패 시 기존 캐시로 폴백
        return {}                       # 캐시도 없으면 데이터 부족과 동일하게 처리

    cache, _ = ReviewSummaryCache.objects.update_or_create(
        place_id=target_id,
        defaults={
            "score": result.score,
            "positive_keywords": result.positive,
            "negative_keywords": result.negative,
            "review_count_at_calc": count,
        },
    )
    return _serialize(cache)
```

- **`targetId`가 존재하지 않는 `TouristSpot`을 가리켜도 `PLACE_NOT_FOUND`를 내지 않는다.** 같은 `authorization: none`·`targetId` 쿼리 구조의 형제 엔드포인트인 `GET /reviews`(7.15.5)도 `TouristSpot` 존재를 검증하지 않고 `Review.objects.filter(place_id=...)`만 수행하는 것과 동일하게 맞춘다. Notion 명세의 에러 코드 표에도 이 엔드포인트는 `INSUFFICIENT_DATA` 하나뿐이라 이 결정이 명세와 어긋나지 않는다.
- LLM 실패를 `ApiError`(예: `EXTERNAL_API_ERROR`)로 올리지 않고 캐시 폴백 또는 빈 데이터로 흡수한다 — 관광지 혼잡도·교통(7.11.4)과 같은 "보조 데이터, 실패해도 200 유지" 패턴을 그대로 따른다.
- `update_or_create` 단일 문으로 충분해 `transaction.atomic()`으로 감싸지 않는다(0절 원칙 3).

#### 7.21.5 시리얼라이저 / 뷰 / URL

- `reviews/serializers.py`: `ReviewSummaryQuerySerializer(targetId=IntegerField())`. 응답 `data`는 서비스가 만든 dict(`{}` 또는 `{"score", "keywords": {"positive", "negative"}}`)를 그대로 `ApiResponse(data=...)`에 넣는다 — 별도 응답 시리얼라이저 없이 서비스 계층에서 최종 shape을 만든다.
- `reviews/views.py`: `ReviewSummaryView(APIView)`, `permission_classes = [AllowAny]`, `GET`만 구현. `@extend_schema(summary="AI 만족도·키워드 요약", operation_id="reviews_summary", tags=["Reviews"], auth=[], ...)`.
- `reviews/urls.py`에 한 줄 추가:
```python
path("api/v1/reviews/summary", ReviewSummaryView.as_view(), name="summary"),
```
`api/v1/reviews`(컬렉션)·`api/v1/reviews/<int:reviewId>/...`와 URL 세그먼트가 겹치지 않아 등록 순서와 무관하게 충돌이 없다.

#### 7.21.6 미해결 사항 갱신

- 7.15.8 미해결 사항 3 **[해결]**: AI 연동은 LLM 재사용(7.21.1), 재계산 빈도는 `ReviewSummaryCache`(7.21.3)로 확정.
- 7.15.8 미해결 사항 4(`places` 앱 `avgRating`/`aiSatisfaction`/통합검색 `rating` 고정값 교체)는 **이번 이슈에 포함하지 않는다.** `feature/reviews-ai-summary` 브랜치는 reviews 앱 범위로 한정하고(0절 원칙 1), `places/services.py`·`places/views.py` 변경은 별도 후속 이슈(가칭 "장소 상세/통합검색 리뷰 집계 반영")로 분리한다. 그 이슈에서 `avgRating`은 `Review.objects.filter(place=spot).aggregate(Avg("rating"))`, `aiSatisfaction`은 이번 절의 `get_review_summary` 결과를 재사용하는 방향으로 설계한다.
- 새 미해결 사항: `MIN_REVIEWS_FOR_SUMMARY`/`RECOMPUTE_INTERVAL`(각 5)은 운영 데이터 없이 임의로 정한 값이다. 초기 리뷰가 거의 없는 서비스 특성상 값이 너무 낮으면 캐시 효과가 없고, 너무 높으면 요약이 오래 갱신되지 않는다 — 프론트/기획과 조정 필요.

#### 7.21.7 테스트 관점 (`tests/test_reviews_summary.py`, 신규)

`AISummaryClient.summarize`는 `unittest.mock.patch`로 모킹한다.

- 리뷰 0~4개(임계값 미만): `summarize`가 호출되지 않고 `data: {}`.
- 리뷰 5개 이상, 캐시 없음: `summarize` 호출, 응답에 `score`/`keywords.positive`/`keywords.negative`, `ReviewSummaryCache` 생성 확인.
- 캐시 있음 + 이후 리뷰 증가량이 `RECOMPUTE_INTERVAL` 미만: `summarize`가 호출되지 않고 캐시값 그대로 응답.
- 캐시 있음 + 증가량이 `RECOMPUTE_INTERVAL` 이상: `summarize` 재호출, 캐시 갱신.
- `AISummaryError` 발생 + 캐시 없음: `data: {}`.
- `AISummaryError` 발생 + 캐시 있음: 기존 캐시값으로 폴백 응답.
- 존재하지 않는 `targetId`: `PLACE_NOT_FOUND`가 아니라 `data: {}`(200) — 7.21.4 결정 검증.
- 인증 없이 호출해도 200(`AllowAny`) 확인.

## 8. 단계별 구현 계획

- **Stage 0** — Django 프로젝트 뼈대: `config/` 생성, MySQL 연결, 빈 상태로 `manage.py migrate`/`runserver` 동작 확인. 도메인 앱 없음.
- **Stage 1** — `accounts` 앱: 6절 모델/엔드포인트 구현. `common` 앱의 응답 포맷/에러 핸들러도 이 단계에서 함께 구현 (auth가 이를 바로 사용하므로).
- **Stage 2** — `places` 앱: `TouristSpot`/`TouristSpotImage` 모델과 통합 검색(`/search`)/장소 상세/관광지 예상 방문 집중도/실시간 교통 혼잡 안내 4개 API. TourAPI는 조회 시 로컬 write-through 캐시, 집중률은 관광공사 예측 API, 교통은 카카오모빌리티 Directions API를 사용한다.
- **Stage 3** — `courses` 앱: `Course`/`CoursePlace`/`CourseProgress` 모델 + 저장/시작/완주인증/공유 API(`feature/courses-base`, **완료** — 7.12절) → AI 맞춤 추천(`feature/courses-recommend`, **완료** — 7.13절) → 동선 최적화(`feature/courses-optimize`, 7.14절, **다음 착수 대상**), 3개 이슈로 순서대로 진행(`docs/roadmap.md` 4절).
- **Stage 4** — `reviews`(7.15절, **완료**) + `interactions`(7.16절, **완료**) 앱: `Review`/`ReviewPhoto`/`ReviewReaction`/`ReviewReport`, `Bookmark`(장소 전용) → AI 만족도·키워드 요약(`feature/reviews-ai-summary`, 7.21절, **다음 착수 대상**).
- **Stage 5** — `gamification` 앱(7.17절): `Stamp`/`HiddenCourse`/`UserHiddenCourseUnlock`/`CompletionCard`(`RegionStamp` 마스터 테이블 없음, 완주카드는 course 단위). 위치 체크인/스탬프북(`feature/gamification-stamps`, **완료** — 7.17.7절) → 숨겨진 여행지/완주 카드(`feature/gamification-cards`, 7.17.8절, **다음 착수 대상**), 2개 이슈로 순서대로 진행.
- **Stage 6** — `mypage`(7.18절, `accounts.User`에 `profile_img` 필드·`nickname` unique 마이그레이션 추가 포함) + `home`(7.19절, 조회 전용, `courses`·`gamification` 완료 후 전체 구현 가능) + `common.UserSettings`(7.20절, 중첩 응답 구조).
- **Stage 7** — 배포 준비: settings dev/prod 분리, Dockerfile, Nginx, CI(`.github/workflows/ci.yml`) 갱신.

각 스테이지는 별도 커밋/PR 단위로 진행하고, 다음 스테이지로 넘어가기 전에 리뷰를 거친다.

## 9. 폐기 대상 (Stage 0에서 제거)

- `app/` 전체 (FastAPI 코드)
- `tests/test_api_skeleton.py`, `tests/test_auth_signup.py`, `tests/conftest.py`, `tests/test_error_response.py`, `tests/test_health.py` (Django 버전 테스트로 재작성)
- `data/eodiganam.sqlite3`
- `pyproject.toml`의 `fastapi`, `uvicorn`, `pydantic-settings`, `httpx` 의존성

`.github/workflows/ci.yml`은 Stage 1에서 pytest-django 기준으로 갱신한다 (Stage 0에서는 임시로 실패 상태를 허용하거나 스킵).
