"""Path validation and allowlisted folder-browse routes."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import (
    FilesystemReader,
    get_filesystem_reader,
    get_or_create_correlation_id,
    get_path_policy,
)
from app.api.errors import ApiError
from app.api.schemas.api_models import (
    FolderBrowseItem,
    FolderBrowseResponse,
    PathValidationRequest,
    PathValidationResponse,
)
from app.config.path_policy import PathPolicy, safe_display_path

router = APIRouter()


@router.get("/files/browse", response_model=FolderBrowseResponse)
def browse_folders(
    purpose: str = Query(...),
    root: str | None = Query(default=None),
    path_policy: Annotated[PathPolicy, Depends(get_path_policy)] = None,  # type: ignore[assignment]
    filesystem_reader: Annotated[FilesystemReader, Depends(get_filesystem_reader)] = None,  # type: ignore[assignment]
    correlation_id: Annotated[str, Depends(get_or_create_correlation_id)] = "",
) -> FolderBrowseResponse:
    validated_purpose = _validate_purpose(purpose, correlation_id)
    allowed_roots = _roots_for(path_policy, validated_purpose)
    root_candidate = root or allowed_roots[0]
    validation = path_policy.validate_path(
        validated_purpose,
        root_candidate,
        correlation_id=correlation_id,
    )
    if validation.status != "green":
        raise ApiError(
            503,
            error_code="PATH_ROOT_UNAVAILABLE",
            message=f"{validated_purpose.capitalize()} root is unavailable.",
            field="root",
            correlation_id=correlation_id,
        )
    if not filesystem_reader.exists(validation.normalized_path) or not filesystem_reader.is_directory(
        validation.normalized_path,
    ):
        raise ApiError(
            503,
            error_code="PATH_ROOT_UNAVAILABLE",
            message=f"{validated_purpose.capitalize()} root is unavailable.",
            field="root",
            correlation_id=correlation_id,
        )

    items = [
        FolderBrowseItem(
            name=entry.name,
            display_path=safe_display_path(entry.path, allowed_roots=allowed_roots),
            is_directory=entry.is_directory,
            is_selectable=entry.is_directory,
            reason_code=None,
        )
        for entry in filesystem_reader.list_entries(validation.normalized_path)
        if entry.is_directory
    ]
    return FolderBrowseResponse(
        purpose=validated_purpose,
        root=safe_display_path(validation.normalized_path, allowed_roots=allowed_roots),
        items=items,
        correlation_id=correlation_id,
    )


@router.post("/files/validate-path", response_model=PathValidationResponse)
def validate_path(
    payload: PathValidationRequest,
    path_policy: Annotated[PathPolicy, Depends(get_path_policy)],
    correlation_id: Annotated[str, Depends(get_or_create_correlation_id)],
) -> PathValidationResponse:
    resolved_correlation_id = str(payload.correlation_id or correlation_id)
    result = path_policy.validate_path(
        payload.purpose,
        payload.path,
        correlation_id=resolved_correlation_id,
    )
    return PathValidationResponse(
        purpose=result.purpose,
        path=result.path,
        normalized_path=result.normalized_path,
        display_path=result.display_path,
        status=result.status,
        reason_code=result.reason_code or "OK",
        message=result.message,
        correlation_id=result.correlation_id,
    )


def _validate_purpose(value: str, correlation_id: str) -> Literal["source", "destination"]:
    if value not in {"source", "destination"}:
        raise ApiError(
            422,
            error_code="PURPOSE_INVALID",
            message="purpose must be 'source' or 'destination'.",
            field="purpose",
            correlation_id=correlation_id,
        )
    return value


def _roots_for(
    path_policy: PathPolicy,
    purpose: Literal["source", "destination"],
) -> tuple[str, ...]:
    return path_policy.source_roots if purpose == "source" else path_policy.destination_roots


__all__ = ["router"]
