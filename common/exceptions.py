from enum import Enum

from rest_framework.exceptions import APIException


class ErrorCode(Enum):
    COMMON_400 = ("COMMON_400", 400, "잘못된 요청입니다.")
    COMMON_404 = ("COMMON_404", 404, "요청한 리소스를 찾을 수 없습니다.")
    COMMON_422 = ("COMMON_422", 422, "요청 값이 올바르지 않습니다.")
    COMMON_500 = ("COMMON_500", 500, "서버 내부 오류가 발생했습니다.")
    AUTH_401 = ("AUTH_401", 401, "인증이 필요합니다.")
    DUPLICATE_ID = ("DUPLICATE_ID", 409, "이미 사용 중인 아이디입니다.")
    DUPLICATE_EMAIL = (
        "DUPLICATE_EMAIL",
        409,
        "이미 사용 중인 이메일입니다.",
    )
    CODE_MISMATCH = ("CODE_MISMATCH", 400, "인증번호가 일치하지 않습니다.")
    PASSWORD_MISMATCH = ("PASSWORD_MISMATCH", 400, "비밀번호가 일치하지 않습니다.")
    TERMS_NOT_AGREED = (
        "TERMS_NOT_AGREED",
        400,
        "이용약관에 동의해야 합니다.",
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
