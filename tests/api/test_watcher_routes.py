from __future__ import annotations

from fastapi.testclient import TestClient

from tests.api.test_app_factory import (
    FakeFilesystemReader,
    build_test_app,
    seed_watcher,
    session_for_app,
)


def test_create_watcher_persists_config(sqlite_engine) -> None:
    fs = FakeFilesystemReader()
    for path in (
        "/data/sources",
        "/data/sources/source-a",
        "/data/outputs",
        "/data/outputs/destination-a",
        "/data/quarantine",
    ):
        fs.add_directory(path)
    app = build_test_app(sqlite_engine, filesystem_reader=fs)
    client = TestClient(app)

    response = client.post(
        "/watchers",
        json={
            "name": "demo watcher",
            "sources": [
                {
                    "folder_id": "11111111-1111-4111-8111-111111111111",
                    "display_path": "/source-a",
                    "route_tags": ["A"],
                    "route_tags_text": "A",
                }
            ],
            "destinations": [
                {
                    "folder_id": "22222222-2222-4222-8222-222222222222",
                    "display_path": "/destination-a",
                    "route_tags": ["A"],
                    "route_tags_text": "A",
                }
            ],
            "route_policy": "tag_match_all_destinations",
            "enabled": False,
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["name"] == "demo watcher"
    assert payload["route_preview"]["status"] == "green"


def test_list_watchers_paginates(sqlite_engine) -> None:
    app = build_test_app(sqlite_engine)
    with session_for_app(app) as session:
        seed_watcher(session, name="watcher-one")
        seed_watcher(session, name="watcher-two")

    client = TestClient(app)
    response = client.get("/watchers", params={"limit": 1, "offset": 1})

    assert response.status_code == 200
    payload = response.json()
    assert payload["limit"] == 1
    assert payload["offset"] == 1
    assert payload["total"] == 2
    assert len(payload["items"]) == 1


def test_get_watcher_not_found(sqlite_engine) -> None:
    app = build_test_app(sqlite_engine)
    client = TestClient(app)

    response = client.get("/watchers/11111111-1111-4111-8111-111111111111")

    assert response.status_code == 404
    assert response.json()["error_code"] == "WATCHER_NOT_FOUND"


def test_patch_watcher_empty_body_rejected(sqlite_engine) -> None:
    app = build_test_app(sqlite_engine)
    with session_for_app(app) as session:
        watcher_ids = seed_watcher(session)

    client = TestClient(app)
    response = client.patch(f"/watchers/{watcher_ids['watcher_id']}", json={})

    assert response.status_code == 422
    assert response.json()["error_code"] == "EMPTY_PATCH"


def test_patch_watcher_updates_sources(sqlite_engine) -> None:
    fs = FakeFilesystemReader()
    for path in (
        "/data/sources",
        "/data/sources/source-a",
        "/data/sources/source-b",
        "/data/outputs",
        "/data/outputs/destination-a",
        "/data/quarantine",
    ):
        fs.add_directory(path)
    app = build_test_app(sqlite_engine, filesystem_reader=fs)
    with session_for_app(app) as session:
        watcher_ids = seed_watcher(session)

    client = TestClient(app)
    response = client.patch(
        f"/watchers/{watcher_ids['watcher_id']}",
        json={
            "sources": [
                {
                    "folder_id": "33333333-3333-4333-8333-333333333333",
                    "display_path": "/source-b",
                    "route_tags": ["B"],
                    "route_tags_text": "B",
                }
            ]
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["sources"][0]["display_path"] == "/source-b"
    assert payload["route_preview"]["status"] == "red"


def test_start_persists_command_and_reuses_idempotency(sqlite_engine) -> None:
    app = build_test_app(sqlite_engine)
    with session_for_app(app) as session:
        watcher_ids = seed_watcher(session)

    client = TestClient(app)
    headers = {"Idempotency-Key": "watcher-start-key"}
    body = {"requested_by": "tester", "reason": "start"}

    first = client.post(f"/watchers/{watcher_ids['watcher_id']}/start", json=body, headers=headers)
    second = client.post(f"/watchers/{watcher_ids['watcher_id']}/start", json=body, headers=headers)

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["command_id"] == second.json()["command_id"]


def test_pause_rejects_created_state(sqlite_engine) -> None:
    app = build_test_app(sqlite_engine)
    with session_for_app(app) as session:
        watcher_ids = seed_watcher(session, lifecycle_state="CREATED")

    client = TestClient(app)
    response = client.post(
        f"/watchers/{watcher_ids['watcher_id']}/pause",
        json={"requested_by": "tester", "reason": "pause"},
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "WATCHER_STATE_CONFLICT"


def test_resume_requires_paused_state(sqlite_engine) -> None:
    app = build_test_app(sqlite_engine)
    with session_for_app(app) as session:
        watcher_ids = seed_watcher(session, lifecycle_state="CREATED")

    client = TestClient(app)
    response = client.post(
        f"/watchers/{watcher_ids['watcher_id']}/resume",
        json={"requested_by": "tester", "reason": "resume"},
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "WATCHER_STATE_CONFLICT"


def test_stop_accepts_active_state(sqlite_engine) -> None:
    app = build_test_app(sqlite_engine)
    with session_for_app(app) as session:
        watcher_ids = seed_watcher(session, lifecycle_state="ACTIVE")

    client = TestClient(app)
    response = client.post(
        f"/watchers/{watcher_ids['watcher_id']}/stop",
        json={"requested_by": "tester", "reason": "stop"},
    )

    assert response.status_code == 202
    assert response.json()["target_resource_type"] == "watcher"


def test_preview_routes_returns_unmatched_sources(sqlite_engine) -> None:
    fs = FakeFilesystemReader()
    for path in (
        "/data/sources",
        "/data/sources/source-a",
        "/data/outputs",
        "/data/outputs/destination-a",
        "/data/quarantine",
    ):
        fs.add_directory(path)
    app = build_test_app(sqlite_engine, filesystem_reader=fs)
    with session_for_app(app) as session:
        watcher_ids = seed_watcher(session)

    client = TestClient(app)
    response = client.post(
        f"/watchers/{watcher_ids['watcher_id']}/preview-routes",
        json={
            "sources": [
                {
                    "folder_id": "11111111-1111-4111-8111-111111111111",
                    "display_path": "/source-a",
                    "route_tags": ["A"],
                    "route_tags_text": "A",
                }
            ],
            "destinations": [
                {
                    "folder_id": "22222222-2222-4222-8222-222222222222",
                    "display_path": "/destination-a",
                    "route_tags": ["B"],
                    "route_tags_text": "B",
                }
            ],
            "route_policy": "tag_match_all_destinations",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "red"
    assert len(payload["unmatched_sources"]) == 1


def test_start_rejects_idempotency_key_payload_conflict(sqlite_engine) -> None:
    app = build_test_app(sqlite_engine)
    with session_for_app(app) as session:
        watcher_ids = seed_watcher(session)

    client = TestClient(app)
    headers = {"Idempotency-Key": "watcher-start-conflict-key"}
    first = client.post(
        f"/watchers/{watcher_ids['watcher_id']}/start",
        json={"requested_by": "tester", "reason": "start"},
        headers=headers,
    )
    second = client.post(
        f"/watchers/{watcher_ids['watcher_id']}/start",
        json={"requested_by": "tester", "reason": "different reason"},
        headers=headers,
    )

    assert first.status_code == 202
    assert second.status_code == 409
    assert second.json()["error_code"] == "IDEMPOTENCY_KEY_CONFLICT"
