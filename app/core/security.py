from fastapi import Header

from app.exceptions.base import BusinessException
from app.exceptions.codes import ErrorCode


def require_auth(authorization: str | None = Header(default=None)) -> dict[str, str]:
    if not authorization:
        raise BusinessException(ErrorCode.AUTH_401)
    return {"user_id": "mock-user"}
