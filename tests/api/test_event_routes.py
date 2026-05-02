from __future__ import annotations

from fastapi.testclient import TestClient

from tests.api.test_app_factory import build_test_app, seed_event, seed_watcher, session_for_app


def test_list_events_returns_safe_summary(sqlite_engine) -> None:
    app = build_test_app(sqlite_engine)
    with session_for_app(app) as session:
        watcher_ids = seed_watcher(session)
        event = seed_event(session, watcher_id=watcher_ids["watcher_id"])

    client = TestClient(app)
    response = client.get("/events")

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"][0]["event_id"] == str(event.event_id)
    assert "payload_json" not in payload["items"][0]


def test_event_filter_invalid_timestamp(sqlite_engine) -> None:
    app = build_test_app(sqlite_engine)
    client = TestClient(app)

    response = client.get("/events", params={"from_occurred_at": "not-a-timestamp"})

    assert response.status_code == 422
    assert response.json()["error_code"] == "FILTER_INVALID"
