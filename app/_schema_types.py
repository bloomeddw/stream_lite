"""Shared Pydantic schema primitives for requirements-backed contract models."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from pydantic import AfterValidator, BaseModel, ConfigDict, StringConstraints
from typing_extensions import Annotated

SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
SERVICE_VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+(?:[-+][A-Za-z0-9_.-]+)?$")
RFC3339_UTC_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$"
)
ROUTE_TAG_PATTERN = re.compile(r"^[A-Z0-9_-]{1,32}$")
ERROR_CODE_PATTERN = re.compile(r"^[A-Z0-9_]{2,64}$")
SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")
SECTION_ID_PATTERN = re.compile(r"^[a-z0-9_]{1,64}$")
EVENT_TYPE_PATTERN = re.compile(r"^[a-z]+(?:\.[a-z_]+)+$")
WINDOWS_DRIVE_PATTERN = re.compile(r"^[A-Za-z]:[\\/]")


def _validate_rfc3339_utc(value: str) -> str:
    if not RFC3339_UTC_PATTERN.fullmatch(value):
        raise ValueError("value must be an RFC 3339 UTC string ending in Z")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("value must be a valid RFC 3339 UTC timestamp") from exc
    return value


def _validate_safe_reference(value: str) -> str:
    if "\x00" in value:
        raise ValueError("value must not contain a null byte")
    if "\\" in value or WINDOWS_DRIVE_PATTERN.match(value):
        raise ValueError("value must not use a host-only or Windows path form")
    if any(segment == ".." for segment in value.split("/")):
        raise ValueError("value must not contain traversal segments")
    return value


def _validate_safe_display_path(value: str) -> str:
    return _validate_safe_reference(value)


def _validate_safe_locator(value: str) -> str:
    if value.lower().startswith("file://"):
        raise ValueError("value must not use a file:// locator")
    return _validate_safe_reference(value)


def _validate_absolute_container_path(value: str) -> str:
    safe_value = _validate_safe_reference(value)
    if not safe_value.startswith("/"):
        raise ValueError("value must use an absolute container path")
    return safe_value


SchemaVersion = Annotated[
    str,
    StringConstraints(pattern=SEMVER_PATTERN.pattern),
]
ServiceVersion = Annotated[
    str,
    StringConstraints(pattern=SERVICE_VERSION_PATTERN.pattern),
]
Rfc3339Utc = Annotated[
    str,
    StringConstraints(pattern=RFC3339_UTC_PATTERN.pattern),
    AfterValidator(_validate_rfc3339_utc),
]
RouteTag = Annotated[
    str,
    StringConstraints(pattern=ROUTE_TAG_PATTERN.pattern),
]
ErrorCode = Annotated[
    str,
    StringConstraints(pattern=ERROR_CODE_PATTERN.pattern),
]
Sha256Hex = Annotated[
    str,
    StringConstraints(pattern=SHA256_PATTERN.pattern),
]
SectionId = Annotated[
    str,
    StringConstraints(pattern=SECTION_ID_PATTERN.pattern),
]
EventTypeName = Annotated[
    str,
    StringConstraints(pattern=EVENT_TYPE_PATTERN.pattern),
]
SafeDisplayPath = Annotated[
    str,
    AfterValidator(_validate_safe_display_path),
]
SafeLocator = Annotated[
    str,
    AfterValidator(_validate_safe_locator),
]
AbsoluteContainerPath = Annotated[
    str,
    AfterValidator(_validate_absolute_container_path),
]


class SchemaModel(BaseModel):
    """Base model for closed JSON schema objects."""

    model_config = ConfigDict(extra="forbid")


class ExtensibleSchemaModel(BaseModel):
    """Base model for schema objects that explicitly allow extra fields."""

    model_config = ConfigDict(extra="allow")


JsonObject = dict[str, Any]


__all__ = [
    "AbsoluteContainerPath",
    "ErrorCode",
    "EventTypeName",
    "ExtensibleSchemaModel",
    "JsonObject",
    "RFC3339_UTC_PATTERN",
    "Rfc3339Utc",
    "ROUTE_TAG_PATTERN",
    "RouteTag",
    "SafeDisplayPath",
    "SafeLocator",
    "SchemaModel",
    "SchemaVersion",
    "SectionId",
    "ServiceVersion",
    "Sha256Hex",
]
