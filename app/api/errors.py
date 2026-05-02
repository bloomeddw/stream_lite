"""Shared sanitized API error primitives aligned with the standard error schema."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app import ensure_uuid_str

_ERROR_CODE_PATTERN = re.compile(r"^[A-Z0-9_]{2,64}$")


@dataclass(frozen=True, slots=True)
class StandardError:
    """Shared API error envelope with explicit null serialization."""

    error_code: str
    message: str
    field: str | None = None
    resource_id: str | None = None
    current_state: str | None = None
    correlation_id: str | None = None

    def __post_init__(self) -> None:
        if not _ERROR_CODE_PATTERN.match(self.error_code):
            raise ValueError("error_code must match ^[A-Z0-9_]{2,64}$")
        if not (1 <= len(self.message) <= 512):
            raise ValueError("message must be between 1 and 512 characters")
        if self.field is not None and len(self.field) > 256:
            raise ValueError("field must be 256 characters or fewer")
        if self.current_state is not None and len(self.current_state) > 64:
            raise ValueError("current_state must be 64 characters or fewer")

        object.__setattr__(
            self,
            "correlation_id",
            ensure_uuid_str(self.correlation_id, field_name="correlation_id"),
        )
        if self.resource_id is not None:
            object.__setattr__(
                self,
                "resource_id",
                ensure_uuid_str(self.resource_id, field_name="resource_id"),
            )

    def to_dict(self) -> dict[str, str | None]:
        return {
            "error_code": self.error_code,
            "message": self.message,
            "field": self.field,
            "resource_id": self.resource_id,
            "current_state": self.current_state,
            "correlation_id": self.correlation_id,
        }


class ApiError(Exception):
    """Exception wrapper that carries an HTTP status plus a standard error body."""

    def __init__(
        self,
        status_code: int,
        *,
        error_code: str,
        message: str,
        field: str | None = None,
        resource_id: str | None = None,
        current_state: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        self.status_code = status_code
        self.error = StandardError(
            error_code=error_code,
            message=message,
            field=field,
            resource_id=resource_id,
            current_state=current_state,
            correlation_id=correlation_id,
        )
        super().__init__(self.error.message)

    def to_dict(self) -> dict[str, str | None]:
        return self.error.to_dict()


def api_error_response(request: Request, exc: ApiError) -> JSONResponse:
    request.state.api_error_code = exc.error.error_code
    correlation_id = getattr(request.state, "correlation_id", None)
    if correlation_id:
        exc.error = StandardError(
            error_code=exc.error.error_code,
            message=exc.error.message,
            field=exc.error.field,
            resource_id=exc.error.resource_id,
            current_state=exc.error.current_state,
            correlation_id=correlation_id,
        )
    return JSONResponse(status_code=exc.status_code, content=exc.to_dict())


def request_validation_error_response(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    first_error = exc.errors()[0] if exc.errors() else {}
    loc = first_error.get("loc", ())
    message = first_error.get("msg", "Request validation failed.")
    request.state.api_error_code = "REQUEST_VALIDATION_FAILED"
    error = StandardError(
        error_code="REQUEST_VALIDATION_FAILED",
        message=message,
        field=_format_error_location(loc),
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return JSONResponse(status_code=422, content=error.to_dict())


def _format_error_location(location: Any) -> str | None:
    if not isinstance(location, (list, tuple)):
        return None

    parts: list[str] = []
    for index, part in enumerate(location):
        if index == 0 and part in {"body", "query", "path"}:
            continue
        if isinstance(part, int):
            if not parts:
                parts.append(f"[{part}]")
            else:
                parts[-1] = f"{parts[-1]}[{part}]"
            continue
        text = str(part)
        if not parts:
            parts.append(text)
        else:
            parts.append(text)
    return ".".join(parts) if parts else None


__all__ = [
    "ApiError",
    "StandardError",
    "api_error_response",
    "request_validation_error_response",
]
