"""FastAPI dependency helpers for the WP-05 control plane."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any, Callable

from fastapi import Depends, Header, Query, Request
from sqlalchemy.orm import Session, sessionmaker

from app import ensure_uuid_str, generate_uuid_str
from app.api.errors import ApiError
from app.config.path_policy import PathPolicy
from app.config.settings import SettingsError, StreamLiteSettings
from app.db.session import create_session_factory
from app.events.redis_streams import RedisStreamClient
from app.observability.logging import configure_structured_logging, emit_structured_log
from app.repositories.commands import CommandRepository
from app.repositories.delivery import DeliveryRepository
from app.repositories.events import EventOutboxRepository
from app.repositories.jobs import JobRepository
from app.repositories.observability import HealthRepository, OperationalLogRepository
from app.repositories.processing import ProcessingRepository
from app.repositories.retry import RetryRepository
from app.repositories.validation import ValidationRepository
from app.repositories.watchers import WatcherRepository

DEFAULT_PAGE_LIMIT = 50
MAX_PAGE_LIMIT = 500
_SETTINGS_STATUS_BY_ERROR_CODE = {
    "BROKER_UNAVAILABLE": 503,
    "CONFIG_INVALID_ENUM": 500,
    "CONFIG_MISSING": 500,
    "CONFIG_UNSUPPORTED_DEFERRED_PROFILE": 500,
    "DB_UNAVAILABLE": 503,
    "PATH_ROOT_UNAVAILABLE": 503,
    "PRESENTATION_CONFIG_INVALID": 500,
}


@dataclass(frozen=True, slots=True)
class PaginationParams:
    limit: int = DEFAULT_PAGE_LIMIT
    offset: int = 0


@dataclass(frozen=True, slots=True)
class FilesystemEntry:
    name: str
    path: str
    is_directory: bool


@dataclass(frozen=True, slots=True)
class DependencyProbeResult:
    status: str
    error_code: str | None = None
    message: str | None = None


class FilesystemReader:
    """Small filesystem adapter that tests can replace through app state."""

    def exists(self, path: str) -> bool:
        return Path(path).exists()

    def is_directory(self, path: str) -> bool:
        return Path(path).is_dir()

    def is_readable(self, path: str) -> bool:
        return os.access(Path(path), os.R_OK)

    def is_writable(self, path: str) -> bool:
        return os.access(Path(path), os.W_OK)

    def list_entries(self, path: str) -> list[FilesystemEntry]:
        entries: list[FilesystemEntry] = []
        for child in sorted(Path(path).iterdir(), key=lambda item: (not item.is_dir(), item.name.lower())):
            entries.append(
                FilesystemEntry(
                    name=child.name,
                    path=child.as_posix(),
                    is_directory=child.is_dir(),
                ),
            )
        return entries


RedisProbe = Callable[[StreamLiteSettings], DependencyProbeResult]


@lru_cache(maxsize=1)
def _load_settings_from_environment() -> StreamLiteSettings:
    try:
        return StreamLiteSettings.from_environment()
    except SettingsError as exc:
        raise ApiError(
            _SETTINGS_STATUS_BY_ERROR_CODE.get(exc.error_code, 500),
            error_code=exc.error_code,
            message=str(exc),
        ) from exc


@lru_cache(maxsize=None)
def _session_factory_for_database_url(database_url: str) -> sessionmaker[Session]:
    return create_session_factory(database_url=database_url, expire_on_commit=False)


@lru_cache(maxsize=None)
def _logger_for_level(level: str) -> logging.Logger:
    return configure_structured_logging("api", level=level, logger_name="stream_lite.api")


def _default_redis_probe(settings: StreamLiteSettings) -> DependencyProbeResult:
    try:
        client = RedisStreamClient(redis_url=settings.redis_url).client
        ping = getattr(client, "ping", None)
        if callable(ping):
            ping()
        return DependencyProbeResult(status="ready", message="ready")
    except Exception as exc:  # pragma: no cover - exercised through route tests via overrides
        error_code = getattr(exc, "error_code", "BROKER_UNAVAILABLE")
        return DependencyProbeResult(status="unavailable", error_code=error_code, message=str(exc))


def get_settings(request: Request) -> StreamLiteSettings:
    settings = getattr(request.app.state, "settings", None)
    if settings is not None:
        return settings
    return _load_settings_from_environment()


def get_session_factory(
    request: Request,
    settings: Annotated[StreamLiteSettings, Depends(get_settings)],
) -> sessionmaker[Session]:
    session_factory = getattr(request.app.state, "session_factory", None)
    if session_factory is not None:
        return session_factory
    return _session_factory_for_database_url(settings.database_url)


def get_db_session(
    session_factory: Annotated[sessionmaker[Session], Depends(get_session_factory)],
):
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def get_path_policy(
    request: Request,
    settings: Annotated[StreamLiteSettings, Depends(get_settings)],
) -> PathPolicy:
    policy = getattr(request.app.state, "path_policy", None)
    if policy is not None:
        return policy
    return settings.to_path_policy()


def get_or_create_correlation_id(request: Request) -> str:
    existing = getattr(request.state, "correlation_id", None)
    if isinstance(existing, str) and existing:
        return existing

    header_value = request.headers.get("X-Correlation-ID") or request.headers.get("Correlation-ID")
    try:
        correlation_id = ensure_uuid_str(header_value, field_name="correlation_id")
    except ValueError:
        correlation_id = generate_uuid_str()
    request.state.correlation_id = correlation_id
    return correlation_id


def get_idempotency_key(
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> str | None:
    if idempotency_key is None:
        return None
    value = idempotency_key.strip()
    return value or None


def get_pagination(
    limit: int = Query(DEFAULT_PAGE_LIMIT),
    offset: int = Query(0),
    correlation_id: Annotated[str, Depends(get_or_create_correlation_id)] = "",
) -> PaginationParams:
    if limit < 1 or limit > MAX_PAGE_LIMIT:
        raise ApiError(
            422,
            error_code="PAGINATION_INVALID",
            message=f"limit must be between 1 and {MAX_PAGE_LIMIT}.",
            field="limit",
            correlation_id=correlation_id,
        )
    if offset < 0:
        raise ApiError(
            422,
            error_code="PAGINATION_INVALID",
            message="offset must be greater than or equal to 0.",
            field="offset",
            correlation_id=correlation_id,
        )
    return PaginationParams(limit=limit, offset=offset)


def get_filesystem_reader(request: Request) -> FilesystemReader:
    reader = getattr(request.app.state, "filesystem_reader", None)
    if reader is not None:
        return reader
    return FilesystemReader()


def get_redis_probe(request: Request) -> RedisProbe:
    probe = getattr(request.app.state, "redis_probe", None)
    if probe is not None:
        return probe
    return _default_redis_probe


def get_api_logger(
    request: Request,
    settings: Annotated[StreamLiteSettings, Depends(get_settings)],
) -> logging.Logger:
    logger = getattr(request.app.state, "api_logger", None)
    if logger is not None:
        return logger
    return _logger_for_level(settings.log_level)


def emit_api_route_log(
    logger: logging.Logger,
    settings: StreamLiteSettings,
    *,
    event: str,
    message: str,
    route: str,
    method: str,
    status_code: int,
    correlation_id: str,
    watcher_id: str | None = None,
    job_id: str | None = None,
    error_code: str | None = None,
    duration_ms: int | None = None,
) -> None:
    emit_structured_log(
        logger,
        service="api",
        component="routes",
        event=event,
        message=message,
        correlation_id=correlation_id,
        duration_ms=duration_ms,
        route=route,
        method=method,
        status_code=status_code,
        watcher_id=watcher_id,
        job_id=job_id,
        error_code=error_code,
        secret_values=(settings.database_url,),
        allowed_container_roots=(
            settings.watch_root,
            settings.output_root,
            settings.quarantine_root,
        ),
    )


def get_watcher_repository(
    session: Annotated[Session, Depends(get_db_session)],
) -> WatcherRepository:
    return WatcherRepository(session)


def get_job_repository(
    session: Annotated[Session, Depends(get_db_session)],
) -> JobRepository:
    return JobRepository(session)


def get_command_repository(
    session: Annotated[Session, Depends(get_db_session)],
) -> CommandRepository:
    return CommandRepository(session)


def get_event_outbox_repository(
    session: Annotated[Session, Depends(get_db_session)],
) -> EventOutboxRepository:
    return EventOutboxRepository(session)


def get_validation_repository(
    session: Annotated[Session, Depends(get_db_session)],
) -> ValidationRepository:
    return ValidationRepository(session)


def get_processing_repository(
    session: Annotated[Session, Depends(get_db_session)],
) -> ProcessingRepository:
    return ProcessingRepository(session)


def get_delivery_repository(
    session: Annotated[Session, Depends(get_db_session)],
) -> DeliveryRepository:
    return DeliveryRepository(session)


def get_retry_repository(
    session: Annotated[Session, Depends(get_db_session)],
) -> RetryRepository:
    return RetryRepository(session)


def get_operational_log_repository(
    session: Annotated[Session, Depends(get_db_session)],
) -> OperationalLogRepository:
    return OperationalLogRepository(session)


def get_health_repository(
    session: Annotated[Session, Depends(get_db_session)],
) -> HealthRepository:
    return HealthRepository(session)


__all__ = [
    "DEFAULT_PAGE_LIMIT",
    "MAX_PAGE_LIMIT",
    "DependencyProbeResult",
    "FilesystemEntry",
    "FilesystemReader",
    "PaginationParams",
    "emit_api_route_log",
    "get_api_logger",
    "get_command_repository",
    "get_db_session",
    "get_delivery_repository",
    "get_event_outbox_repository",
    "get_filesystem_reader",
    "get_health_repository",
    "get_idempotency_key",
    "get_job_repository",
    "get_operational_log_repository",
    "get_or_create_correlation_id",
    "get_pagination",
    "get_path_policy",
    "get_processing_repository",
    "get_redis_probe",
    "get_retry_repository",
    "get_session_factory",
    "get_settings",
    "get_validation_repository",
    "get_watcher_repository",
]
