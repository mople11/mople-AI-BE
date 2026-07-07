from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.exceptions.base import BusinessException
from app.exceptions.codes import ErrorCode
from app.schemas.error import ErrorDetail, ErrorResponse


def _error_response(error_code: ErrorCode) -> JSONResponse:
    body = ErrorResponse(
        error=ErrorDetail(code=error_code.code, message=error_code.message)
    )
    return JSONResponse(
        status_code=error_code.status_code,
        content=body.model_dump(),
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(BusinessException)
    async def business_exception_handler(
        request: Request,
        exc: BusinessException,
    ) -> JSONResponse:
        return _error_response(exc.error_code)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return _error_response(ErrorCode.COMMON_422)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        if exc.status_code == 404:
            return _error_response(ErrorCode.COMMON_404)
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error=ErrorDetail(
                    code=f"COMMON_{exc.status_code}",
                    message=str(exc.detail),
                )
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        return _error_response(ErrorCode.COMMON_500)
