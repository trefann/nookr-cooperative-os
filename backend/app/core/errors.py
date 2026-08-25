"""Uniform API error envelope.

Every failure the client can encounter comes back as
{"error": {"code": ..., "message": ..., "details": ...}} so the frontend has a
single code path for surfacing problems.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

#: Starlette renamed this constant; support both without a deprecation warning.
UNPROCESSABLE_STATUS = getattr(
    status, "HTTP_422_UNPROCESSABLE_CONTENT", 422
)


class AppError(Exception):
    """Base class for expected, user-facing failures."""

    status_code = status.HTTP_400_BAD_REQUEST
    code = "bad_request"

    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class ConflictError(AppError):
    """The request is well formed but illegal in the current state."""

    status_code = status.HTTP_409_CONFLICT
    code = "conflict"


class PermissionDeniedError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "forbidden"


class UnauthorizedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "unauthorized"


class UnprocessableError(AppError):
    status_code = UNPROCESSABLE_STATUS
    code = "unprocessable"


def _envelope(code: str, message: str, details: Any = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details}}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(HTTPException)
    async def _http_error(_request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail
        message = detail if isinstance(detail, str) else "Request failed."
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(f"http_{exc.status_code}", message),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        fields = [
            {
                "field": ".".join(str(part) for part in err.get("loc", [])[1:]),
                "message": err.get("msg", "Invalid value."),
            }
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=UNPROCESSABLE_STATUS,
            content=_envelope(
                "validation_error", "Some fields need attention.", fields
            ),
        )

    @app.exception_handler(IntegrityError)
    async def _integrity_error(_request: Request, _exc: IntegrityError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=_envelope(
                "integrity_error",
                "That record conflicts with something that already exists.",
            ),
        )

    @app.exception_handler(SQLAlchemyError)
    async def _db_error(_request: Request, _exc: SQLAlchemyError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_envelope("database_error", "A database error occurred."),
        )
