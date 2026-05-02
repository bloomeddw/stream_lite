"""Asynchronous command status routes."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.dependencies import get_command_repository, get_or_create_correlation_id
from app.api.errors import ApiError, StandardError
from app.api.schemas.api_models import CommandStatusResponse
from app.repositories.commands import CommandRepository

router = APIRouter()


@router.get("/commands/{command_id}", response_model=CommandStatusResponse)
def get_command_status(
    command_id: UUID,
    repository: Annotated[CommandRepository, Depends(get_command_repository)],
    correlation_id: Annotated[str, Depends(get_or_create_correlation_id)],
) -> CommandStatusResponse:
    record = repository.get_command(command_id)
    if record is None:
        raise ApiError(
            404,
            error_code="COMMAND_NOT_FOUND",
            message=f"Command {command_id} was not found.",
            resource_id=str(command_id),
            correlation_id=correlation_id,
        )

    error = None
    if record.error_code is not None:
        error = StandardError(
            error_code=record.error_code,
            message="Command failed.",
            resource_id=str(record.command_id),
            current_state=record.status,
            correlation_id=correlation_id,
        )

    return CommandStatusResponse(
        command_id=record.command_id,
        status=record.status,
        target_resource_type=record.target_resource_type,
        target_resource_id=record.target_resource_id,
        result=None if record.result_locator is None else {"locator": record.result_locator},
        error=None if error is None else error.to_dict(),
        created_at=_format_datetime(record.created_at),
        updated_at=_format_datetime(record.updated_at),
        correlation_id=correlation_id,
    )


def _format_datetime(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


__all__ = ["router"]
