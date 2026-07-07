from enum import Enum


class ErrorCode(Enum):
    COMMON_400 = ("COMMON_400", 400, "잘못된 요청입니다.")
    COMMON_404 = ("COMMON_404", 404, "요청한 리소스를 찾을 수 없습니다.")
    COMMON_422 = ("COMMON_422", 422, "요청 값이 올바르지 않습니다.")
    COMMON_500 = ("COMMON_500", 500, "서버 내부 오류가 발생했습니다.")
    AUTH_401 = ("AUTH_401", 401, "인증이 필요합니다.")

    def __init__(self, code: str, status_code: int, message: str):
        self.code = code
        self.status_code = status_code
        self.message = message
