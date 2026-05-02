"""FastAPI application factory for the Stream Lite control plane."""

from __future__ import annotations

import logging
from time import perf_counter
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError

from app import ensure_uuid_str, generate_uuid_str
from app.api.errors import api_error_response, request_validation_error_response
from app.api.routes import ROUTERS
from app.api import ApiError
from app.config.settings import StreamLiteSettings
from app.observability.logging import configure_structured_logging, emit_structured_log

API_VERSION = "0.1.0"
_REQUEST_DURATION_METRIC = "stream_lite_api_request_duration_seconds"
_REQUEST_COUNT_METRIC = "stream_lite_api_request_total"
_ROUTE_EVENT_BY_METHOD_AND_PATH = {
    ("GET", "/health"): "api.health_checked",
    ("GET", "/health/dependencies"): "api.dependency_health_checked",
    ("POST", "/watchers"): "watcher.create_requested",
    ("GET", "/watchers"): "watcher.list_requested",
    ("GET", "/watchers/{watcher_id}"): "watcher.read_requested",
    ("PATCH", "/watchers/{watcher_id}"): "watcher.patch_requested",
    ("POST", "/watchers/{watcher_id}/start"): "watcher.start_requested",
    ("POST", "/watchers/{watcher_id}/pause"): "watcher.pause_requested",
    ("POST", "/watchers/{watcher_id}/resume"): "watcher.resume_requested",
    ("POST", "/watchers/{watcher_id}/stop"): "watcher.stop_requested",
    ("POST", "/watchers/{watcher_id}/preview-routes"): "route.preview_requested",
    ("GET", "/jobs"): "job.list_requested",
    ("GET", "/jobs/{job_id}"): "job.read_requested",
    ("GET", "/jobs/{job_id}/history"): "job.history_requested",
    ("POST", "/jobs/{job_id}/retry"): "job.retry_requested",
    ("GET", "/commands/{command_id}"): "command.read_requested",
    ("GET", "/events"): "event.list_requested",
    ("GET", "/metrics/summary"): "metrics.summary_requested",
    ("GET", "/logs"): "log.list_requested",
    ("GET", "/files/browse"): "files.browse_requested",
    ("POST", "/files/validate-path"): "files.path_validated",
    ("GET", "/config/dashboard-presentation"): "config.dashboard_presentation_requested",
}


def create_app() -> FastAPI:
    app = FastAPI(title="Stream Lite API", version=API_VERSION)

    @app.middleware("http")
    async def _record_route_observability(request: Request, call_next):  # type: ignore[no-untyped-def]
        started_at = perf_counter()
        correlation_id = _resolve_correlation_id(request)
        request.state.correlation_id = correlation_id
        status_code = 500
        error_code: str | None = None
        response = None
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception as exc:
            error_code = _error_code_from_exception(exc) or "UNEXPECTED_ERROR"
            raise
        finally:
            duration_ms = max(0, int((perf_counter() - started_at) * 1000))
            error_code = error_code or getattr(request.state, "api_error_code", None)
            route_path = _route_path(request)
            method = request.method.upper()
            if response is not None:
                status_code = response.status_code
            _record_route_metric(
                request.app,
                route=route_path,
                method=method,
                status_code=status_code,
                duration_ms=duration_ms,
            )
            _emit_route_log(
                request.app,
                route=route_path,
                method=method,
                status_code=status_code,
                correlation_id=correlation_id,
                error_code=error_code,
                duration_ms=duration_ms,
                path_params=getattr(request, "path_params", {}),
            )

    @app.exception_handler(ApiError)
    async def _handle_api_error(request, exc: ApiError):  # type: ignore[no-untyped-def]
        return api_error_response(request, exc)

    @app.exception_handler(RequestValidationError)
    async def _handle_request_validation_error(request, exc: RequestValidationError):  # type: ignore[no-untyped-def]
        return request_validation_error_response(request, exc)

    for router in ROUTERS:
        app.include_router(router)

    return app


def _resolve_correlation_id(request: Request) -> str:
    header_value = request.headers.get("X-Correlation-ID") or request.headers.get("Correlation-ID")
    try:
        return ensure_uuid_str(header_value, field_name="correlation_id")
    except ValueError:
        return generate_uuid_str()


def _route_path(request: Request) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    if isinstance(path, str) and path:
        return path
    return request.url.path


def _error_code_from_exception(exc: Exception) -> str | None:
    direct = getattr(exc, "error_code", None)
    if isinstance(direct, str) and direct:
        return direct
    error = getattr(exc, "error", None)
    nested = getattr(error, "error_code", None)
    if isinstance(nested, str) and nested:
        return nested
    return None


def _record_route_metric(app: FastAPI, *, route: str, method: str, status_code: int, duration_ms: int) -> None:
    observations = getattr(app.state, "api_request_observations", None)
    if observations is None:
        observations = []
        app.state.api_request_observations = observations
    observations.append(
        {
            "metric_name": _REQUEST_DURATION_METRIC,
            "count_metric_name": _REQUEST_COUNT_METRIC,
            "route": route,
            "method": method,
            "status_code": str(status_code),
            "duration_ms": duration_ms,
            "duration_seconds": duration_ms / 1000.0,
        },
    )


def _emit_route_log(
    app: FastAPI,
    *,
    route: str,
    method: str,
    status_code: int,
    correlation_id: str,
    error_code: str | None,
    duration_ms: int,
    path_params: dict[str, Any],
) -> None:
    logger = _route_logger(app)
    settings = getattr(app.state, "settings", None)
    allowed_roots: tuple[str, ...] = ()
    secret_values: tuple[str, ...] = ()
    if isinstance(settings, StreamLiteSettings):
        allowed_roots = (settings.watch_root, settings.output_root, settings.quarantine_root)
        secret_values = (settings.database_url, settings.redis_url)
    level = "ERROR" if status_code >= 500 else "WARNING" if status_code >= 400 else "INFO"
    event = _ROUTE_EVENT_BY_METHOD_AND_PATH.get((method, route), "api.route_completed")
    emit_structured_log(
        logger,
        service="api",
        component="routes",
        event=event,
        message=f"{method} {route} completed with status {status_code}.",
        level=level,
        correlation_id=correlation_id,
        duration_ms=duration_ms,
        route=route,
        method=method,
        status_code=status_code,
        watcher_id=_path_param(path_params, "watcher_id"),
        job_id=_path_param(path_params, "job_id"),
        error_code=error_code,
        secret_values=secret_values,
        allowed_container_roots=allowed_roots,
    )


def _route_logger(app: FastAPI) -> logging.Logger:
    logger = getattr(app.state, "api_logger", None)
    if isinstance(logger, logging.Logger):
        return logger
    settings = getattr(app.state, "settings", None)
    level = settings.log_level if isinstance(settings, StreamLiteSettings) else "INFO"
    logger = configure_structured_logging("api", level=level, logger_name="stream_lite.api")
    app.state.api_logger = logger
    return logger


def _path_param(path_params: dict[str, Any], key: str) -> str | None:
    value = path_params.get(key)
    return str(value) if value is not None else None


__all__ = ["API_VERSION", "create_app"]
