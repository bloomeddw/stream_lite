"""Health routes for the Stream Lite control plane."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

import sqlalchemy as sa
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.dependencies import (
    DependencyProbeResult,
    FilesystemReader,
    RedisProbe,
    get_db_session,
    get_filesystem_reader,
    get_or_create_correlation_id,
    get_redis_probe,
    get_settings,
)
from app.api.schemas.api_models import DependencyHealthItem, DependencyHealthResponse, HealthResponse
from app.config.settings import StreamLiteSettings

router = APIRouter()
API_VERSION = "0.1.0"


@router.get("/health", response_model=HealthResponse)
def get_health(
    correlation_id: Annotated[str, Depends(get_or_create_correlation_id)],
) -> HealthResponse:
    checked_at = _now_text()
    return HealthResponse(
        status="ready",
        service="stream_lite_api",
        version=API_VERSION,
        checked_at=checked_at,
        correlation_id=correlation_id,
    )


@router.get("/health/dependencies", response_model=DependencyHealthResponse)
def get_dependency_health(
    settings: Annotated[StreamLiteSettings, Depends(get_settings)],
    session: Annotated[Session, Depends(get_db_session)],
    filesystem_reader: Annotated[FilesystemReader, Depends(get_filesystem_reader)],
    redis_probe: Annotated[RedisProbe, Depends(get_redis_probe)],
    correlation_id: Annotated[str, Depends(get_or_create_correlation_id)],
):
    checked_at = _now_text()
    db_probe = _probe_database(session)
    redis_result = redis_probe(settings)
    spark_probe = DependencyProbeResult(status="ready", message="ready")
    filesystem_probe = _probe_filesystem_roots(settings, filesystem_reader)

    items = [
        _item("postgres", db_probe, checked_at),
        _item("redis_streams", redis_result, checked_at),
        _item("spark", spark_probe, checked_at),
        _item("filesystem_roots", filesystem_probe, checked_at),
    ]
    overall_status = "ready" if all(item.status == "ready" for item in items) else "not_ready"
    response = DependencyHealthResponse(
        status=overall_status,
        dependencies=items,
        checked_at=checked_at,
        correlation_id=correlation_id,
    )
    if overall_status == "ready":
        return response
    return JSONResponse(status_code=503, content=response.model_dump(mode="json"))


def _probe_database(session: Session) -> DependencyProbeResult:
    try:
        session.execute(sa.text("SELECT 1"))
        return DependencyProbeResult(status="ready", message="ready")
    except Exception as exc:
        return DependencyProbeResult(
            status="unavailable",
            error_code="DB_UNAVAILABLE",
            message=str(exc),
        )


def _probe_filesystem_roots(
    settings: StreamLiteSettings,
    filesystem_reader: FilesystemReader,
) -> DependencyProbeResult:
    roots = (
        (settings.watch_root, "readable"),
        (settings.output_root, "writable"),
        (settings.quarantine_root, "writable"),
    )
    for root, mode in roots:
        if not filesystem_reader.exists(root) or not filesystem_reader.is_directory(root):
            return DependencyProbeResult(
                status="unavailable",
                error_code="PATH_ROOT_UNAVAILABLE",
                message=f"{root} is unavailable.",
            )
        if mode == "readable" and not filesystem_reader.is_readable(root):
            return DependencyProbeResult(
                status="unavailable",
                error_code="PATH_ROOT_UNAVAILABLE",
                message=f"{root} is not readable.",
            )
        if mode == "writable" and not filesystem_reader.is_writable(root):
            return DependencyProbeResult(
                status="unavailable",
                error_code="PATH_ROOT_UNAVAILABLE",
                message=f"{root} is not writable.",
            )
    return DependencyProbeResult(status="ready", message="ready")


def _item(name: str, result: DependencyProbeResult, checked_at: str) -> DependencyHealthItem:
    return DependencyHealthItem(
        name=name,
        status=result.status,
        checked_at=checked_at,
        message=result.message,
        error_code=result.error_code,
    )


def _now_text() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


__all__ = ["router"]
