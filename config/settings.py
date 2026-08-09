from datetime import timedelta
from pathlib import Path

import environ


BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    MYSQL_PORT=(int, 3306),
    JWT_ACCESS_TOKEN_LIFETIME_MIN=(int, 60),
    JWT_REFRESH_TOKEN_LIFETIME_DAYS=(int, 14),
    EMAIL_VERIFICATION_CODE_LIFETIME_MIN=(int, 5),
    TOUR_API_TIMEOUT_SEC=(int, 5),
    TOUR_CONGESTION_API_TIMEOUT_SEC=(int, 5),
    KAKAO_MOBILITY_TIMEOUT_SEC=(int, 5),
    COURSE_CHECKIN_RADIUS_M=(int, 200),
    LLM_API_TIMEOUT_SEC=(int, 15),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY", default="change-me-in-env")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "common",
    "accounts",
    "places",
    "courses",
    "reviews",
    "interactions",
    "gamification",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": env("MYSQL_DATABASE", default="eodiganam"),
        "USER": env("MYSQL_USER", default="eodiganam"),
        "PASSWORD": env("MYSQL_PASSWORD", default="change-me-in-env"),
        "HOST": env("MYSQL_HOST", default="127.0.0.1"),
        "PORT": env("MYSQL_PORT"),
        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ko-kr"
TIME_ZONE = "Asia/Seoul"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "common.exception_handler.custom_exception_handler",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "어디가남 API",
    "DESCRIPTION": (
        "전남 날씨 기반 여행 추천 서비스 백엔드 API 문서입니다. "
        "모든 애플리케이션 응답은 success/data/error 공통 포맷을 사용합니다."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "persistAuthorization": True,
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=env("JWT_ACCESS_TOKEN_LIFETIME_MIN")
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=env("JWT_REFRESH_TOKEN_LIFETIME_DAYS")
    ),
}

EMAIL_VERIFICATION_CODE_LIFETIME_MIN = env(
    "EMAIL_VERIFICATION_CODE_LIFETIME_MIN"
)
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)

GOOGLE_CLIENT_ID = env("GOOGLE_CLIENT_ID", default="")
KAKAO_REST_API_KEY = env("KAKAO_REST_API_KEY", default="")

TOUR_API_BASE_URL = env(
    "TOUR_API_BASE_URL",
    default="https://apis.data.go.kr/B551011/KorService2",
)
TOUR_API_SERVICE_KEY = env("TOUR_API_SERVICE_KEY", default="")
TOUR_API_TIMEOUT_SEC = env("TOUR_API_TIMEOUT_SEC")

TOUR_CONGESTION_API_BASE_URL = env(
    "TOUR_CONGESTION_API_BASE_URL",
    default="https://apis.data.go.kr/B551011/TatsCnctrRateService",
)
TOUR_CONGESTION_API_SERVICE_KEY = env(
    "TOUR_CONGESTION_API_SERVICE_KEY", default=""
)
TOUR_CONGESTION_API_TIMEOUT_SEC = env("TOUR_CONGESTION_API_TIMEOUT_SEC")

KAKAO_MOBILITY_BASE_URL = env(
    "KAKAO_MOBILITY_BASE_URL",
    default="https://apis-navi.kakaomobility.com/v1",
)
KAKAO_MOBILITY_REST_API_KEY = env(
    "KAKAO_MOBILITY_REST_API_KEY", default=""
)
KAKAO_MOBILITY_TIMEOUT_SEC = env("KAKAO_MOBILITY_TIMEOUT_SEC")

LLM_API_BASE_URL = env(
    "LLM_API_BASE_URL",
    default="https://api.openai.com/v1",
)
LLM_API_KEY = env("LLM_API_KEY", default="")
LLM_API_MODEL = env("LLM_API_MODEL", default="gpt-4.1-mini")
LLM_API_TIMEOUT_SEC = env("LLM_API_TIMEOUT_SEC")

COURSE_CHECKIN_RADIUS_M = env("COURSE_CHECKIN_RADIUS_M")
COURSE_SHARE_BASE_URL = env(
    "COURSE_SHARE_BASE_URL",
    default="https://eodiganam.app/courses",
)
CARD_SHARE_BASE_URL = env(
    "CARD_SHARE_BASE_URL",
    default="https://eodiganam.app/cards",
)
