from __future__ import annotations

from fastapi.testclient import TestClient

from tests.api.test_app_factory import build_test_app, seed_log, seed_watcher, session_for_app


def test_metrics_summary_schema(sqlite_engine) -> None:
    app = build_test_app(sqlite_engine)
    with session_for_app(app) as session:
        seed_watcher(session, lifecycle_state="ACTIVE")

    client = TestClient(app)
    response = client.get("/metrics/summary")

    assert response.status_code == 200
    payload = response.json()
    assert "job_counts" in payload
    assert "watcher_counts" in payload


def test_list_logs_sanitizes_paths(sqlite_engine) -> None:
    app = build_test_app(sqlite_engine)
    with session_for_app(app) as session:
        seed_log(session, message=r"C:\secret\unsafe.txt")

    client = TestClient(app)
    response = client.get("/logs")

    assert response.status_code == 200
    assert response.json()["items"][0]["message"] == "[redacted-host-path]"


def test_dashboard_presentation_schema(sqlite_engine) -> None:
    app = build_test_app(sqlite_engine)
    client = TestClient(app)

    response = client.get("/config/dashboard-presentation")

    assert response.status_code == 200
    payload = response.json()
    assert payload["theme_name"] == "default_light"
    assert payload["refresh_interval_seconds"] == 2
