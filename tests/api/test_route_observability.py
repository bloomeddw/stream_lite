from __future__ import annotations

import io
import json

from fastapi.testclient import TestClient

from app.observability.logging import configure_structured_logging
from tests.api.test_app_factory import build_test_app, seed_watcher, session_for_app


def _capture_logger(app):
    stream = io.StringIO()
    app.state.api_logger = configure_structured_logging(
        "api",
        level="INFO",
        stream=stream,
        logger_name="stream_lite.api.test",
    )
    return stream


def _last_log(stream: io.StringIO) -> dict[str, object]:
    lines = [line for line in stream.getvalue().splitlines() if line.strip()]
    assert lines
    return json.loads(lines[-1])


def test_route_observability_records_read_route(sqlite_engine) -> None:
    app = build_test_app(sqlite_engine)
    stream = _capture_logger(app)
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    observation = app.state.api_request_observations[-1]
    assert observation["metric_name"] == "stream_lite_api_request_duration_seconds"
    assert observation["route"] == "/health"
    assert observation["method"] == "GET"
    assert observation["status_code"] == "200"
    record = _last_log(stream)
    assert record["event"] == "api.health_checked"
    assert record["route"] == "/health"
    assert record["duration_ms"] >= 0
    assert record["error_code"] is None


def test_route_observability_records_mutation_route(sqlite_engine) -> None:
    app = build_test_app(sqlite_engine)
    stream = _capture_logger(app)
    with session_for_app(app) as session:
        watcher_ids = seed_watcher(session)
    client = TestClient(app)

    response = client.post(
        f"/watchers/{watcher_ids['watcher_id']}/start",
        json={"requested_by": "tester", "reason": "start"},
        headers={"X-Correlation-ID": "11111111-1111-4111-8111-111111111111"},
    )

    assert response.status_code == 202
    observation = app.state.api_request_observations[-1]
    assert observation["route"] == "/watchers/{watcher_id}/start"
    assert observation["method"] == "POST"
    assert observation["status_code"] == "202"
    record = _last_log(stream)
    assert record["event"] == "watcher.start_requested"
    assert record["correlation_id"] == "11111111-1111-4111-8111-111111111111"
    assert record["watcher_id"] == str(watcher_ids["watcher_id"])


def test_route_observability_records_error_route(sqlite_engine) -> None:
    app = build_test_app(sqlite_engine)
    stream = _capture_logger(app)
    client = TestClient(app)

    response = client.get("/watchers/11111111-1111-4111-8111-111111111111")

    assert response.status_code == 404
    observation = app.state.api_request_observations[-1]
    assert observation["route"] == "/watchers/{watcher_id}"
    assert observation["status_code"] == "404"
    record = _last_log(stream)
    assert record["event"] == "watcher.read_requested"
    assert record["level"] == "WARNING"
    assert record["error_code"] == "WATCHER_NOT_FOUND"
