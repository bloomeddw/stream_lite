from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("jsonschema")

from jsonschema import validate

from app.config import PathPolicy, safe_display_path

REPO_ROOT = Path(__file__).resolve().parents[2]
PATH_VALIDATION_RESPONSE_SCHEMA = json.loads(
    (REPO_ROOT / "schemas" / "api" / "path_validation_response.schema.json").read_text(
        encoding="utf-8"
    )
)


def test_safe_display_path_uses_mount_relative_output_for_allowlisted_paths() -> None:
    assert (
        safe_display_path(
            "/data/sources/acme/orders.csv",
            allowed_roots=("/data/sources",),
        )
        == "/acme/orders.csv"
    )


def test_path_policy_accepts_allowlisted_source_path() -> None:
    policy = PathPolicy(
        source_roots=("/data/sources",),
        destination_roots=("/data/outputs",),
    )

    result = policy.validate_path(
        "source",
        "/data/sources/acme/orders.csv",
        correlation_id="11111111-1111-4111-8111-111111111111",
    )

    assert result.status == "green"
    assert result.reason_code is None
    assert result.path == "/data/sources/acme/orders.csv"
    assert result.normalized_path == "/data/sources/acme/orders.csv"
    assert result.display_path == "/acme/orders.csv"
    validate(result.to_dict(), PATH_VALIDATION_RESPONSE_SCHEMA)


def test_path_policy_rejects_outside_allowlist_without_leaking_full_path() -> None:
    policy = PathPolicy(
        source_roots=("/data/sources",),
        destination_roots=("/data/outputs",),
    )

    result = policy.validate_path(
        "source",
        "/etc/passwd",
        correlation_id="11111111-1111-4111-8111-111111111111",
    )

    assert result.status == "red"
    assert result.reason_code == "PATH_NOT_ALLOWLISTED"
    assert result.path == "/passwd"
    assert result.normalized_path == "/passwd"
    assert result.display_path == "/passwd"
    assert "/etc/passwd" not in result.message
    validate(result.to_dict(), PATH_VALIDATION_RESPONSE_SCHEMA)


def test_path_policy_rejects_traversal_escape() -> None:
    policy = PathPolicy(
        source_roots=("/data/sources",),
        destination_roots=("/data/outputs",),
    )

    result = policy.validate_path(
        "source",
        "/data/sources/../../etc/passwd",
        correlation_id="11111111-1111-4111-8111-111111111111",
    )

    assert result.status == "red"
    assert result.reason_code == "PATH_TRAVERSAL_REJECTED"
    assert result.display_path == "/passwd"


def test_path_policy_sanitizes_host_absolute_paths() -> None:
    policy = PathPolicy(
        source_roots=("/data/sources",),
        destination_roots=("/data/outputs",),
    )

    result = policy.validate_path(
        "destination",
        r"C:\Users\alice\Desktop\drop",
        correlation_id="11111111-1111-4111-8111-111111111111",
    )

    payload = result.to_dict()
    joined = " ".join(str(value) for value in payload.values() if value is not None)

    assert result.status == "red"
    assert result.reason_code == "PATH_INVALID"
    assert result.display_path == "/drop"
    assert "C:\\Users\\alice" not in joined
