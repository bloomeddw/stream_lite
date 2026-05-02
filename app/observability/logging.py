"""Structured logging bootstrap primitives aligned with REQ-012."""

from __future__ import annotations

import json
import logging as stdlib_logging
import re
import sys
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

from app import ensure_uuid_str

_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR"}
_SENSITIVE_KEY_FRAGMENTS = ("password", "secret", "token", "api_key", "database_url")
_SAFE_PATH_KEYS = {"display_path", "source_display_path", "destination_display_path"}
_WINDOWS_DRIVE_PATTERN = re.compile(r"^[A-Za-z]:[\\/]")


def configure_structured_logging(
    service: str,
    *,
    level: str = "INFO",
    stream: Any | None = None,
    logger_name: str | None = None,
) -> stdlib_logging.Logger:
    """Create a stdout logger that emits pre-rendered JSON messages."""

    logger = stdlib_logging.getLogger(logger_name or f"stream_lite.{service}")
    logger.handlers.clear()
    logger.setLevel(_coerce_level(level))
    logger.propagate = False

    handler = stdlib_logging.StreamHandler(stream or sys.stdout)
    handler.setFormatter(stdlib_logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    return logger


def build_structured_log(
    *,
    service: str,
    component: str,
    event: str,
    message: str,
    level: str = "INFO",
    correlation_id: str | None = None,
    duration_ms: int | None = None,
    **fields: Any,
) -> dict[str, Any]:
    """Build a structured log payload without writing it yet."""

    if not service:
        raise ValueError("service must not be empty")
    if not component:
        raise ValueError("component must not be empty")
    if not event:
        raise ValueError("event must not be empty")
    if not message:
        raise ValueError("message must not be empty")

    level_name = _normalize_level_name(level)
    duration_value = None if duration_ms is None else int(duration_ms)
    if duration_value is not None and duration_value < 0:
        raise ValueError("duration_ms must be non-negative")

    record: dict[str, Any] = {
        "timestamp": _utc_timestamp(),
        "level": level_name,
        "service": service,
        "component": component,
        "event": event,
        "correlation_id": ensure_uuid_str(correlation_id, field_name="correlation_id"),
        "message": message,
        "duration_ms": duration_value,
        "job_id": None,
        "watcher_id": None,
        "event_type": None,
        "state_from": None,
        "state_to": None,
        "error_code": None,
        "folder_role": None,
        "folder_status": None,
        "route_policy": None,
        "route_tags": [],
        "matched_route_tags": [],
        "destination_folder_id": None,
        "dashboard_theme": None,
        "dashboard_layout_profile": None,
    }
    record.update(fields)
    return record


def redact_sensitive_fields(
    payload: Mapping[str, Any],
    *,
    secret_values: Iterable[str] = (),
    allowed_container_roots: Iterable[str] = (),
) -> dict[str, Any]:
    """Redact secrets and obvious host-only paths from a structured payload."""

    secret_set = {value for value in secret_values if value}
    allowed_roots = tuple(_normalize_allowed_root(root) for root in allowed_container_roots)
    return {
        key: _sanitize_value(
            key=key,
            value=value,
            secret_values=secret_set,
            allowed_container_roots=allowed_roots,
        )
        for key, value in payload.items()
    }


def emit_structured_log(
    logger: stdlib_logging.Logger,
    *,
    service: str,
    component: str,
    event: str,
    message: str,
    level: str = "INFO",
    correlation_id: str | None = None,
    duration_ms: int | None = None,
    secret_values: Iterable[str] = (),
    allowed_container_roots: Iterable[str] = (),
    **fields: Any,
) -> dict[str, Any]:
    """Build, redact, and emit a structured log line."""

    record = build_structured_log(
        service=service,
        component=component,
        event=event,
        message=message,
        level=level,
        correlation_id=correlation_id,
        duration_ms=duration_ms,
        **fields,
    )
    safe_record = redact_sensitive_fields(
        record,
        secret_values=secret_values,
        allowed_container_roots=allowed_container_roots,
    )
    logger.log(_coerce_level(level), json.dumps(safe_record, sort_keys=True))
    return safe_record


def _sanitize_value(
    *,
    key: str,
    value: Any,
    secret_values: set[str],
    allowed_container_roots: tuple[str, ...],
) -> Any:
    lowered_key = key.lower()

    if _is_sensitive_key(lowered_key):
        return "[redacted]"
    if isinstance(value, str) and value in secret_values:
        return "[redacted]"

    if isinstance(value, Mapping):
        return {
            nested_key: _sanitize_value(
                key=nested_key,
                value=nested_value,
                secret_values=secret_values,
                allowed_container_roots=allowed_container_roots,
            )
            for nested_key, nested_value in value.items()
        }
    if isinstance(value, list):
        return [
            _sanitize_value(
                key=key,
                value=item,
                secret_values=secret_values,
                allowed_container_roots=allowed_container_roots,
            )
            for item in value
        ]
    if isinstance(value, tuple):
        return tuple(
            _sanitize_value(
                key=key,
                value=item,
                secret_values=secret_values,
                allowed_container_roots=allowed_container_roots,
            )
            for item in value
        )

    if isinstance(value, str) and _is_pathlike_key(lowered_key) and key not in _SAFE_PATH_KEYS:
        if _looks_like_host_path(value, allowed_container_roots):
            return "[redacted-host-path]"

    return value


def _is_sensitive_key(lowered_key: str) -> bool:
    return any(fragment in lowered_key for fragment in _SENSITIVE_KEY_FRAGMENTS)


def _is_pathlike_key(lowered_key: str) -> bool:
    return lowered_key == "path" or lowered_key.endswith("_path") or lowered_key.endswith("_locator")


def _looks_like_host_path(value: str, allowed_container_roots: tuple[str, ...]) -> bool:
    if value.startswith("file://"):
        return True
    if "\\" in value or _WINDOWS_DRIVE_PATTERN.match(value):
        return True
    if not value.startswith("/"):
        return False
    if not allowed_container_roots:
        return False
    normalized = _normalize_allowed_root(value)
    return not any(
        normalized == root or normalized.startswith(f"{root}/")
        for root in allowed_container_roots
    )


def _normalize_allowed_root(value: str) -> str:
    parts = [part for part in value.replace("\\", "/").split("/") if part not in {"", "."}]
    return "/" + "/".join(parts) if parts else "/"


def _normalize_level_name(level: str) -> str:
    value = level.upper()
    if value not in _LEVELS:
        raise ValueError("level must be one of DEBUG, INFO, WARNING, ERROR")
    return value


def _coerce_level(level: str) -> int:
    return getattr(stdlib_logging, _normalize_level_name(level))


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


__all__ = [
    "build_structured_log",
    "configure_structured_logging",
    "emit_structured_log",
    "redact_sensitive_fields",
]
