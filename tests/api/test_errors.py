from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

import pytest

pytest.importorskip("jsonschema")

from jsonschema import validate

from app.api import ApiError, StandardError

REPO_ROOT = Path(__file__).resolve().parents[2]
STANDARD_ERROR_SCHEMA = json.loads(
    (REPO_ROOT / "schemas" / "api" / "standard_error.schema.json").read_text(
        encoding="utf-8"
    )
)


def test_standard_error_matches_documented_schema() -> None:
    error = StandardError(
        error_code="TAG_INVALID",
        message="Route tag must match ^[A-Z0-9_-]{1,32}$.",
        field="sources[0].route_tags_text",
    )

    payload = error.to_dict()

    validate(payload, STANDARD_ERROR_SCHEMA)
    assert payload["resource_id"] is None
    assert payload["current_state"] is None
    UUID(payload["correlation_id"])


def test_api_error_wraps_standard_error_with_status_code() -> None:
    error = ApiError(
        422,
        error_code="PATH_NOT_ALLOWLISTED",
        message="Source path /passwd is outside the configured allowlist.",
    )

    payload = error.to_dict()

    assert error.status_code == 422
    assert payload["error_code"] == "PATH_NOT_ALLOWLISTED"
    validate(payload, STANDARD_ERROR_SCHEMA)
