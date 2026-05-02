from __future__ import annotations

from fastapi.testclient import TestClient

from tests.api.test_app_factory import build_test_app, seed_command, seed_watcher, session_for_app


def test_get_command_status(sqlite_engine) -> None:
    app = build_test_app(sqlite_engine)
    with session_for_app(app) as session:
        watcher_ids = seed_watcher(session)
        command = seed_command(session, target_resource_id=watcher_ids["watcher_id"])

    client = TestClient(app)
    response = client.get(f"/commands/{command.command_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["command_id"] == str(command.command_id)
    assert payload["status"] == "accepted"


def test_get_command_status_not_found(sqlite_engine) -> None:
    app = build_test_app(sqlite_engine)
    client = TestClient(app)

    response = client.get("/commands/11111111-1111-4111-8111-111111111111")

    assert response.status_code == 404
    assert response.json()["error_code"] == "COMMAND_NOT_FOUND"
