"""Documented environment-backed settings for Stream Lite WP-01."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Callable, ClassVar, Mapping
from urllib.parse import urlsplit

_MISSING = object()
_WINDOWS_DRIVE_PATTERN = re.compile(r"^[A-Za-z]:[\\/]")


class SettingsError(ValueError):
    """Raised when documented runtime settings are missing or invalid."""

    def __init__(self, env_var: str, error_code: str, message: str) -> None:
        super().__init__(message)
        self.env_var = env_var
        self.error_code = error_code
        self.message = message

    def __str__(self) -> str:
        return f"{self.env_var}: {self.message}"


@dataclass(frozen=True, slots=True)
class _EnvVarSpec:
    env_var: str
    field_name: str
    default: str | object
    required: bool
    sensitive: bool
    parser: Callable[[str, str], Any]


def _fail(env_var: str, error_code: str, message: str) -> None:
    raise SettingsError(env_var=env_var, error_code=error_code, message=message)


def _normalize_absolute_container_path(
    env_var: str,
    raw_value: str,
    *,
    error_code: str,
) -> str:
    value = raw_value.strip()
    if not value:
        _fail(env_var, error_code, "must not be empty.")
    if "\x00" in value:
        _fail(env_var, error_code, "must not contain a null byte.")
    if "\\" in value or _WINDOWS_DRIVE_PATTERN.match(value):
        _fail(env_var, error_code, "must use an absolute container path.")
    if not value.startswith("/"):
        _fail(env_var, error_code, "must use an absolute container path.")

    normalized_parts: list[str] = []
    had_parent_reference = False
    for part in value.split("/"):
        if part in {"", "."}:
            continue
        if part == "..":
            had_parent_reference = True
            if normalized_parts:
                normalized_parts.pop()
                continue
            _fail(env_var, error_code, "must not escape its configured root.")
        normalized_parts.append(part)

    if had_parent_reference:
        _fail(env_var, error_code, "must not contain traversal segments.")

    return "/" + "/".join(normalized_parts) if normalized_parts else "/"


def _parse_int_range(env_var: str, raw_value: str, minimum: int, maximum: int) -> int:
    try:
        parsed = int(raw_value.strip())
    except ValueError as exc:
        _fail(
            env_var,
            "CONFIG_INVALID_ENUM",
            f"must be an integer between {minimum} and {maximum}.",
        )
        raise AssertionError("unreachable") from exc
    if not minimum <= parsed <= maximum:
        _fail(
            env_var,
            "CONFIG_INVALID_ENUM",
            f"must be an integer between {minimum} and {maximum}.",
        )
    return parsed


def _parse_float_range(env_var: str, raw_value: str, minimum: float, maximum: float) -> float:
    try:
        parsed = float(raw_value.strip())
    except ValueError as exc:
        _fail(
            env_var,
            "CONFIG_INVALID_ENUM",
            f"must be a number between {minimum:g} and {maximum:g}.",
        )
        raise AssertionError("unreachable") from exc
    if not minimum <= parsed <= maximum:
        _fail(
            env_var,
            "CONFIG_INVALID_ENUM",
            f"must be a number between {minimum:g} and {maximum:g}.",
        )
    return parsed


def _parse_bool(env_var: str, raw_value: str) -> bool:
    lowered = raw_value.strip().lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    _fail(env_var, "CONFIG_INVALID_ENUM", "must be 'true' or 'false'.")


def _parse_log_level(env_var: str, raw_value: str) -> str:
    value = raw_value.strip().upper()
    if value not in {"DEBUG", "INFO", "WARNING", "ERROR"}:
        _fail(
            env_var,
            "CONFIG_INVALID_ENUM",
            "must be one of DEBUG, INFO, WARNING, ERROR.",
        )
    return value


def _parse_broker_profile(env_var: str, raw_value: str) -> str:
    value = raw_value.strip()
    if value != "redis_streams":
        _fail(
            env_var,
            "CONFIG_UNSUPPORTED_DEFERRED_PROFILE",
            "supports only the active v0.1 profile 'redis_streams'.",
        )
    return value


def _parse_processing_engine(env_var: str, raw_value: str) -> str:
    value = raw_value.strip()
    if value != "spark":
        _fail(
            env_var,
            "CONFIG_UNSUPPORTED_DEFERRED_PROFILE",
            "supports only the active v0.1 profile 'spark'.",
        )
    return value


def _parse_database_url(env_var: str, raw_value: str) -> str:
    value = raw_value.strip()
    parsed = urlsplit(value)
    if (
        not value
        or not parsed.scheme.startswith("postgresql")
        or parsed.hostname is None
        or parsed.path in {"", "/"}
    ):
        _fail(
            env_var,
            "DB_UNAVAILABLE",
            "must be a valid PostgreSQL connection URL.",
        )
    return value


def _parse_redis_url(env_var: str, raw_value: str) -> str:
    value = raw_value.strip()
    parsed = urlsplit(value)
    if not value or parsed.scheme != "redis" or parsed.hostname is None:
        _fail(
            env_var,
            "BROKER_UNAVAILABLE",
            "must be a valid Redis connection URL.",
        )
    return value


def _parse_root_path(env_var: str, raw_value: str) -> str:
    return _normalize_absolute_container_path(
        env_var=env_var,
        raw_value=raw_value,
        error_code="PATH_ROOT_UNAVAILABLE",
    )


def _parse_presentation_file(env_var: str, raw_value: str) -> str:
    return _normalize_absolute_container_path(
        env_var=env_var,
        raw_value=raw_value,
        error_code="PRESENTATION_CONFIG_INVALID",
    )


_ENV_SPECS: tuple[_EnvVarSpec, ...] = (
    _EnvVarSpec("STREAM_LITE_API_PORT", "api_port", "8000", True, False, lambda name, value: _parse_int_range(name, value, 1024, 65535)),
    _EnvVarSpec("STREAM_LITE_DASHBOARD_PORT", "dashboard_port", "8501", True, False, lambda name, value: _parse_int_range(name, value, 1024, 65535)),
    _EnvVarSpec("STREAM_LITE_BROKER_PROFILE", "broker_profile", "redis_streams", True, False, _parse_broker_profile),
    _EnvVarSpec("STREAM_LITE_PROCESSING_ENGINE", "processing_engine", "spark", True, False, _parse_processing_engine),
    _EnvVarSpec("STREAM_LITE_WATCH_ROOT", "watch_root", "/data/sources", True, False, _parse_root_path),
    _EnvVarSpec("STREAM_LITE_OUTPUT_ROOT", "output_root", "/data/outputs", True, False, _parse_root_path),
    _EnvVarSpec("STREAM_LITE_QUARANTINE_ROOT", "quarantine_root", "/data/quarantine", True, False, _parse_root_path),
    _EnvVarSpec("STREAM_LITE_DATABASE_URL", "database_url", _MISSING, True, True, _parse_database_url),
    _EnvVarSpec("STREAM_LITE_REDIS_URL", "redis_url", _MISSING, True, False, _parse_redis_url),
    _EnvVarSpec("STREAM_LITE_DEBUG", "debug", "false", False, False, _parse_bool),
    _EnvVarSpec("STREAM_LITE_FILE_STABILITY_SECONDS", "file_stability_seconds", "2", True, False, lambda name, value: _parse_int_range(name, value, 1, 3600)),
    _EnvVarSpec("STREAM_LITE_MAX_FILE_SIZE_MB", "max_file_size_mb", "100", True, False, lambda name, value: _parse_int_range(name, value, 1, 10240)),
    _EnvVarSpec("STREAM_LITE_RETRY_MAX_ATTEMPTS", "retry_max_attempts", "3", True, False, lambda name, value: _parse_int_range(name, value, 0, 10)),
    _EnvVarSpec("STREAM_LITE_RETRY_INITIAL_BACKOFF_SECONDS", "retry_initial_backoff_seconds", "1", True, False, lambda name, value: _parse_int_range(name, value, 1, 3600)),
    _EnvVarSpec("STREAM_LITE_RETRY_BACKOFF_MULTIPLIER", "retry_backoff_multiplier", "2", True, False, lambda name, value: _parse_float_range(name, value, 1, 10)),
    _EnvVarSpec("STREAM_LITE_RETRY_MAX_BACKOFF_SECONDS", "retry_max_backoff_seconds", "30", True, False, lambda name, value: _parse_int_range(name, value, 1, 86400)),
    _EnvVarSpec("STREAM_LITE_RETRY_JITTER_ENABLED", "retry_jitter_enabled", "true", True, False, _parse_bool),
    _EnvVarSpec("STREAM_LITE_DASHBOARD_PRESENTATION_FILE", "dashboard_presentation_file", "/app/config/dashboard_presentation.yaml", True, False, _parse_presentation_file),
    _EnvVarSpec("STREAM_LITE_LOG_LEVEL", "log_level", "INFO", False, False, _parse_log_level),
    _EnvVarSpec("STREAM_LITE_RECONCILIATION_INTERVAL_SECONDS", "reconciliation_interval_seconds", "10", True, False, lambda name, value: _parse_int_range(name, value, 1, 60)),
)

_SPECS_BY_ENV_VAR = {spec.env_var: spec for spec in _ENV_SPECS}
_FIELD_BY_ENV_VAR = {spec.env_var: spec.field_name for spec in _ENV_SPECS}
_ENV_VAR_BY_FIELD = {spec.field_name: spec.env_var for spec in _ENV_SPECS}
_SENSITIVE_FIELDS = {spec.field_name for spec in _ENV_SPECS if spec.sensitive}


@dataclass(frozen=True, slots=True)
class StreamLiteSettings:
    """Documented runtime configuration loaded from environment variables."""

    api_port: int
    dashboard_port: int
    broker_profile: str
    processing_engine: str
    watch_root: str
    output_root: str
    quarantine_root: str
    database_url: str
    redis_url: str
    debug: bool
    file_stability_seconds: int
    max_file_size_mb: int
    retry_max_attempts: int
    retry_initial_backoff_seconds: int
    retry_backoff_multiplier: float
    retry_max_backoff_seconds: int
    retry_jitter_enabled: bool
    dashboard_presentation_file: str
    log_level: str
    reconciliation_interval_seconds: int

    DOCUMENTED_ENV_VARS: ClassVar[tuple[str, ...]] = tuple(spec.env_var for spec in _ENV_SPECS)

    @classmethod
    def documented_env_vars(cls) -> tuple[str, ...]:
        return cls.DOCUMENTED_ENV_VARS

    @classmethod
    def from_environment(
        cls,
        environ: Mapping[str, str] | None = None,
    ) -> "StreamLiteSettings":
        source = os.environ if environ is None else environ
        parsed_values: dict[str, Any] = {}

        for spec in _ENV_SPECS:
            raw_value = source.get(spec.env_var)
            if raw_value is None or not raw_value.strip():
                if spec.default is not _MISSING:
                    raw_value = str(spec.default)
                elif spec.required:
                    _fail(
                        spec.env_var,
                        "CONFIG_MISSING",
                        "is required and has no documented default.",
                    )
                else:
                    continue
            parsed_values[spec.field_name] = spec.parser(spec.env_var, raw_value)

        return cls(**parsed_values)

    def as_dict(self) -> dict[str, Any]:
        return {
            field_name: getattr(self, field_name)
            for field_name in _ENV_VAR_BY_FIELD
        }

    def as_environ(self, *, sanitized: bool = False) -> dict[str, Any]:
        values: dict[str, Any] = {}
        for field_name, env_var in _ENV_VAR_BY_FIELD.items():
            value = getattr(self, field_name)
            if sanitized and field_name in _SENSITIVE_FIELDS:
                values[env_var] = "[redacted]"
            else:
                values[env_var] = value
        return values

    def to_path_policy(self) -> "PathPolicy":
        from .path_policy import PathPolicy

        return PathPolicy(
            source_roots=(self.watch_root,),
            destination_roots=(self.output_root,),
            debug=self.debug,
        )


__all__ = ["SettingsError", "StreamLiteSettings"]
