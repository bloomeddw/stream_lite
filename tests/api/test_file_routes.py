from __future__ import annotations

from fastapi.testclient import TestClient

from tests.api.test_app_factory import FakeFilesystemReader, build_test_app


def test_browse_folders_only_allowlisted(sqlite_engine) -> None:
    fs = FakeFilesystemReader()
    for path in (
        "/data/sources",
        "/data/sources/source-a",
        "/data/sources/source-b",
        "/data/outputs",
        "/data/quarantine",
    ):
        fs.add_directory(path)
    app = build_test_app(sqlite_engine, filesystem_reader=fs)
    client = TestClient(app)

    response = client.get("/files/browse", params={"purpose": "source"})

    assert response.status_code == 200
    payload = response.json()
    assert all(item["display_path"].startswith("/") for item in payload["items"])
    assert {item["display_path"] for item in payload["items"]} == {"/source-a", "/source-b"}


def test_validate_path_uses_path_policy(sqlite_engine) -> None:
    app = build_test_app(sqlite_engine)
    client = TestClient(app)

    allowed = client.post(
        "/files/validate-path",
        json={"purpose": "source", "path": "/data/sources/source-a"},
    )
    blocked = client.post(
        "/files/validate-path",
        json={"purpose": "source", "path": "/unsafe/source-a"},
    )

    assert allowed.status_code == 200
    assert allowed.json()["status"] == "green"
    assert allowed.json()["reason_code"] == "OK"
    assert blocked.status_code == 200
    assert blocked.json()["status"] == "red"
    assert blocked.json()["reason_code"] == "PATH_NOT_ALLOWLISTED"


def test_browse_folders_rejects_invalid_purpose_with_domain_error(sqlite_engine) -> None:
    app = build_test_app(sqlite_engine)
    client = TestClient(app)

    response = client.get("/files/browse", params={"purpose": "archive"})

    assert response.status_code == 422
    assert response.json()["error_code"] == "PURPOSE_INVALID"
