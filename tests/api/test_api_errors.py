from __future__ import annotations

from fastapi.testclient import TestClient

from tests.api.test_app_factory import build_test_app


def test_standard_error_response_shape(sqlite_engine) -> None:
    app = build_test_app(sqlite_engine)
    client = TestClient(app)

    response = client.get("/watchers", params={"limit": 0}, headers={"X-Correlation-ID": "11111111-1111-4111-8111-111111111111"})

    assert response.status_code == 422
    payload = response.json()
    assert payload["error_code"] == "PAGINATION_INVALID"
    assert payload["field"] == "limit"
    assert payload["resource_id"] is None
    assert payload["current_state"] is None
    assert payload["correlation_id"] == "11111111-1111-4111-8111-111111111111"


def test_request_validation_failed_uses_standard_envelope(sqlite_engine) -> None:
    app = build_test_app(sqlite_engine)
    client = TestClient(app)

    response = client.post("/watchers", json={"route_policy": "tag_match_all_destinations"})

    assert response.status_code == 422
    payload = response.json()
    assert payload["error_code"] == "REQUEST_VALIDATION_FAILED"
    assert "correlation_id" in payload
