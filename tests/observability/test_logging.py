from __future__ import annotations

import io
import json
from uuid import UUID

from app.observability import (
    build_structured_log,
    configure_structured_logging,
    emit_structured_log,
    redact_sensitive_fields,
)


def test_build_structured_log_includes_required_fields() -> None:
    record = build_structured_log(
        service="api",
        component="config.settings",
        event="config.loaded",
        message="Loaded documented settings.",
    )

    assert record["service"] == "api"
    assert record["component"] == "config.settings"
    assert record["event"] == "config.loaded"
    assert record["job_id"] is None
    assert record["watcher_id"] is None
    assert record["route_tags"] == []
    assert record["matched_route_tags"] == []
    assert record["timestamp"].endswith("Z")
    UUID(record["correlation_id"])


def test_redact_sensitive_fields_redacts_secrets_and_host_paths() -> None:
    payload = {
        "database_url": "postgresql://stream_lite:secret@postgres:5432/stream_lite",
        "password": "top-secret",
        "raw_path": r"C:\Users\alice\Desktop\drop",
        "display_path": "/drop",
    }

    safe_payload = redact_sensitive_fields(
        payload,
        secret_values={"top-secret"},
        allowed_container_roots=("/data/sources", "/data/outputs"),
    )

    assert safe_payload["database_url"] == "[redacted]"
    assert safe_payload["password"] == "[redacted]"
    assert safe_payload["raw_path"] == "[redacted-host-path]"
    assert safe_payload["display_path"] == "/drop"


def test_emit_structured_log_writes_redacted_json() -> None:
    stream = io.StringIO()
    logger = configure_structured_logging(
        "api",
        level="DEBUG",
        stream=stream,
        logger_name="tests.stream_lite.api",
    )
    database_url = "postgresql://stream_lite:secret@postgres:5432/stream_lite"

    record = emit_structured_log(
        logger,
        service="api",
        component="config.settings",
        event="config.loaded",
        message="Loaded documented settings.",
        level="INFO",
        database_url=database_url,
        normalized_path="/data/sources/acme/orders.csv",
        display_path="/acme/orders.csv",
        secret_values={database_url},
        allowed_container_roots=("/data/sources", "/data/outputs"),
    )

    rendered = stream.getvalue().strip()
    payload = json.loads(rendered)

    assert record["database_url"] == "[redacted]"
    assert payload["database_url"] == "[redacted]"
    assert payload["normalized_path"] == "/data/sources/acme/orders.csv"
    assert payload["display_path"] == "/acme/orders.csv"
    assert database_url not in rendered
