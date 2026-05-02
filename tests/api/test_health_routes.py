from __future__ import annotations

from fastapi.testclient import TestClient

from tests.api.test_app_factory import FakeFilesystemReader, build_test_app


def test_get_health_returns_schema(sqlite_engine) -> None:
    app = build_test_app(sqlite_engine)
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["service"] == "stream_lite_api"
    assert "correlation_id" in payload


def test_dependency_health_ready(sqlite_engine) -> None:
    fs = FakeFilesystemReader()
    fs.add_directory("/data/sources")
    fs.add_directory("/data/outputs")
    fs.add_directory("/data/quarantine")
    app = build_test_app(sqlite_engine, filesystem_reader=fs, redis_ready=True)
    client = TestClient(app)

    response = client.get("/health/dependencies")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert [item["name"] for item in payload["dependencies"]] == [
        "postgres",
        "redis_streams",
        "spark",
        "filesystem_roots",
    ]
    assert all("error_code" in item for item in payload["dependencies"])
    assert all(item["error_code"] is None for item in payload["dependencies"])


def test_dependency_health_unavailable_returns_503(sqlite_engine) -> None:
    fs = FakeFilesystemReader()
    fs.add_directory("/data/sources")
    fs.add_directory("/data/outputs")
    fs.add_directory("/data/quarantine")
    app = build_test_app(sqlite_engine, filesystem_reader=fs, redis_ready=False)
    client = TestClient(app)

    response = client.get("/health/dependencies")

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "not_ready"
    redis_item = next(item for item in payload["dependencies"] if item["name"] == "redis_streams")
    assert redis_item["error_code"] == "BROKER_UNAVAILABLE"


def test_dependency_health_filesystem_root_includes_error_code(sqlite_engine) -> None:
    fs = FakeFilesystemReader()
    fs.add_directory("/data/sources")
    fs.add_directory("/data/quarantine")
    app = build_test_app(sqlite_engine, filesystem_reader=fs, redis_ready=True)
    client = TestClient(app)

    response = client.get("/health/dependencies")

    assert response.status_code == 503
    filesystem_item = next(item for item in response.json()["dependencies"] if item["name"] == "filesystem_roots")
    assert filesystem_item["error_code"] == "PATH_ROOT_UNAVAILABLE"
