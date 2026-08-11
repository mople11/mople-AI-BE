import logging

from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler

from common.exceptions import ApiError, ErrorCode

logger = logging.getLogger(__name__)


def _error_response(error_code: ErrorCode, details=None) -> Response:
    error = {
        "code": error_code.code,
        "message": error_code.message,
    }
    if details is not None:
        error["details"] = details

    return Response(
        {"success": False, "data": None, "error": error},
        status=error_code.status_code,
    )


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if isinstance(exc, ApiError):
        return _error_response(exc.error_code)

    if isinstance(exc, ValidationError):
        return _error_response(ErrorCode.COMMON_422, details=exc.detail)

    if isinstance(exc, (AuthenticationFailed, NotAuthenticated)):
        return _error_response(ErrorCode.AUTH_401)

    if response is None or response.status_code >= 500:
        request = context["request"]
        logger.error(
            "Unhandled exception on %s %s", request.method, request.path,
            exc_info=exc,
        )
        return _error_response(ErrorCode.COMMON_500)

    if response.status_code == 404:
        return _error_response(ErrorCode.COMMON_404)

    return _error_response(ErrorCode.COMMON_400)
