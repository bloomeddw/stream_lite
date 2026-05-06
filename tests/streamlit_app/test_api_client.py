from __future__ import annotations

import json
from pathlib import Path
from urllib.error import HTTPError

import pytest

from streamlit_app.api_client import StreamLiteApiClient, StreamLiteApiError


class _FakeResponse:
    def __init__(self, payload: dict[str, object], status: int = 200) -> None:
        self.payload = payload
        self.status = status

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_api_client_builds_paths_and_query_strings(monkeypatch) -> None:
    seen = []

    def fake_urlopen(req, timeout):
        seen.append((req.get_method(), req.full_url, timeout, dict(req.header_items())))
        return _FakeResponse({"ok": True})

    monkeypatch.setattr("streamlit_app.api_client.request.urlopen", fake_urlopen)

    client = StreamLiteApiClient(
        "http://api.local/",
        timeout_seconds=7,
        default_headers={"X-Correlation-ID": "11111111-1111-4111-8111-111111111111"},
    )
    assert client.list_jobs({"state": "FAILED", "limit": 25, "skip": None}) == {"ok": True}

    method, url, timeout, headers = seen[-1]
    assert method == "GET"
    assert url == "http://api.local/jobs?state=FAILED&limit=25"
    assert timeout == 7
    assert headers["X-correlation-id"] == "11111111-1111-4111-8111-111111111111"


def test_api_client_sends_idempotency_key_for_retry_job(monkeypatch) -> None:
    seen = []

    def fake_urlopen(req, timeout):
        seen.append((req.get_method(), req.full_url, dict(req.header_items()), req.data))
        return _FakeResponse({"status": "accepted"})

    monkeypatch.setattr("streamlit_app.api_client.request.urlopen", fake_urlopen)

    client = StreamLiteApiClient("http://api.local")
    payload = {"reason": "operator reviewed failed delivery"}
    client.retry_job("job-1", payload, idempotency_key="retry-key-1")

    method, url, headers, body = seen[-1]
    assert method == "POST"
    assert url == "http://api.local/jobs/job-1/retry"
    assert headers["Idempotency-key"] == "retry-key-1"
    assert json.loads(body.decode("utf-8")) == payload


def test_api_client_raises_api_error_with_error_code(monkeypatch) -> None:
    def fake_urlopen(req, timeout):
        body = json.dumps({"error_code": "JOB_NOT_RETRYABLE", "message": "Job is not retryable."}).encode("utf-8")
        raise HTTPError(req.full_url, 409, "Conflict", hdrs=None, fp=_ErrorBody(body))

    monkeypatch.setattr("streamlit_app.api_client.request.urlopen", fake_urlopen)

    client = StreamLiteApiClient("http://api.local")
    with pytest.raises(StreamLiteApiError) as exc_info:
        client.retry_job("job-1", {"reason": "try again"})

    assert exc_info.value.status_code == 409
    assert exc_info.value.error_code == "JOB_NOT_RETRYABLE"
    assert exc_info.value.message == "Job is not retryable."


def test_watcher_command_rejects_unknown_action() -> None:
    client = StreamLiteApiClient("http://api.local")
    with pytest.raises(ValueError):
        client.watcher_command("watcher-1", "delete", {})


def test_streamlit_helpers_do_not_import_direct_persistence_modules() -> None:
    forbidden = ("app.repositories", "app.db", "sqlalchemy", "redis", "app.processing", "app.delivery.service")
    for path in Path("streamlit_app").glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for forbidden_text in forbidden:
            assert forbidden_text not in text, f"{path} imports or references {forbidden_text}"


class _ErrorBody:
    def __init__(self, body: bytes) -> None:
        self._body = body
        self.closed = False

    def read(self) -> bytes:
        return self._body

    def close(self) -> None:
        self.closed = True
