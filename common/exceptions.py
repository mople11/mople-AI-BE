from enum import Enum

from rest_framework.exceptions import APIException


class ErrorCode(Enum):
    COMMON_400 = ("COMMON_400", 400, "잘못된 요청입니다.")
    COMMON_404 = ("COMMON_404", 404, "요청한 리소스를 찾을 수 없습니다.")
    COMMON_422 = ("COMMON_422", 422, "요청 값이 올바르지 않습니다.")
    COMMON_500 = ("COMMON_500", 500, "서버 내부 오류가 발생했습니다.")
    AUTH_401 = ("AUTH_401", 401, "인증이 필요합니다.")
    INVALID_CREDENTIALS = (
        "INVALID_CREDENTIALS",
        401,
        "아이디 또는 비밀번호가 일치하지 않습니다.",
    )
    INVALID_TOKEN = ("INVALID_TOKEN", 400, "유효하지 않은 토큰입니다.")
    DUPLICATE_ID = ("DUPLICATE_ID", 409, "이미 사용 중인 아이디입니다.")
    DUPLICATE_EMAIL = (
        "DUPLICATE_EMAIL",
        409,
        "이미 사용 중인 이메일입니다.",
    )
    NICKNAME_DUPLICATE = (
        "NICKNAME_DUPLICATE",
        409,
        "이미 사용 중인 닉네임입니다.",
    )
    CODE_MISMATCH = ("CODE_MISMATCH", 400, "인증번호가 일치하지 않습니다.")
    CODE_EXPIRED = ("CODE_EXPIRED", 400, "인증번호가 만료되었습니다.")
    CODE_ALREADY_USED = (
        "CODE_ALREADY_USED",
        400,
        "이미 사용된 인증번호입니다.",
    )
    PASSWORD_MISMATCH = ("PASSWORD_MISMATCH", 400, "비밀번호가 일치하지 않습니다.")
    TERMS_NOT_AGREED = (
        "TERMS_NOT_AGREED",
        400,
        "이용약관에 동의해야 합니다.",
    )
    OAUTH_FAILED = ("OAUTH_FAILED", 401, "소셜 인증에 실패했습니다.")
    SOCIAL_EMAIL_CONFLICT = (
        "SOCIAL_EMAIL_CONFLICT",
        409,
        "이미 가입된 이메일과 연결된 계정입니다.",
    )
    EXTERNAL_API_ERROR = (
        "EXTERNAL_API_ERROR",
        502,
        "외부 정보를 불러오지 못했습니다.",
    )
    WEATHER_FETCH_FAILED = (
        "WEATHER_FETCH_FAILED",
        502,
        "날씨 정보를 불러오지 못했습니다.",
    )
    PLACE_NOT_FOUND = (
        "PLACE_NOT_FOUND",
        404,
        "장소 정보를 찾을 수 없습니다.",
    )
    COURSE_NOT_FOUND = (
        "COURSE_NOT_FOUND",
        404,
        "존재하지 않는 코스입니다.",
    )
    COURSE_NOT_COMPLETED = (
        "COURSE_NOT_COMPLETED",
        400,
        "완주하지 않은 코스입니다.",
    )
    LOCATION_MISMATCH = (
        "LOCATION_MISMATCH",
        400,
        "코스 경로와 위치가 일치하지 않습니다.",
    )
    MOOD_REQUIRED = ("MOOD_REQUIRED", 400, "기분을 선택해주세요.")
    AI_RECOMMEND_FAILED = (
        "AI_RECOMMEND_FAILED",
        500,
        "추천 생성에 실패했습니다.",
    )
    MIN_PLACE_REQUIRED = (
        "MIN_PLACE_REQUIRED",
        400,
        "장소를 2개 이상 선택해주세요.",
    )
    ROUTE_CALC_FAILED = (
        "ROUTE_CALC_FAILED",
        500,
        "경로 계산에 실패했습니다.",
    )
    RATING_REQUIRED = ("RATING_REQUIRED", 400, "별점을 선택해주세요.")
    REVIEW_NOT_FOUND = (
        "REVIEW_NOT_FOUND",
        404,
        "존재하지 않는 후기입니다.",
    )
    OUT_OF_REGION = (
        "OUT_OF_REGION",
        400,
        "해당 지역에서만 체크인할 수 있습니다.",
    )

    def __init__(self, code: str, status_code: int, message: str):
        self.code = code
        self.status_code = status_code
        self.message = message


class ApiError(APIException):
    def __init__(self, error_code: ErrorCode):
        self.error_code = error_code
        self.status_code = error_code.status_code
        self.detail = error_code.message
