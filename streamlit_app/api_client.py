"""Typed HTTP helpers for the Stream Lite Streamlit dashboard.

WP11-A keeps the dashboard foundation API-only. This module uses the Python
standard library so it does not add a runtime dependency, and it deliberately
avoids imports from repositories, database sessions, Redis clients, and worker
internals.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import time
from typing import Any, Callable, Mapping
from urllib import error, parse, request

JsonDict = dict[str, Any]
_TERMINAL_COMMAND_STATUSES = {"succeeded", "failed", "expired"}
_WATCHER_ACTIONS = {"start", "pause", "resume", "stop"}


class StreamLiteApiError(RuntimeError):
    """Raised when the FastAPI control plane returns a non-2xx response."""

    def __init__(
        self,
        *,
        status_code: int,
        error_code: str | None = None,
        message: str | None = None,
        payload: JsonDict | None = None,
    ) -> None:
        self.status_code = status_code
        self.error_code = error_code
        self.payload = payload or {}
        self.message = message or error_code or f"HTTP {status_code}"
        super().__init__(self.message)


@dataclass(frozen=True)
class CommandPollResult:
    """Result returned by command status polling."""

    command_id: str
    status: str | None
    attempts: int
    result: JsonDict | None
    error: JsonDict | None
    last_payload: JsonDict | None


class StreamLiteApiClient:
    """Small API client for Streamlit views and command controls."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: float = 5.0,
        default_headers: Mapping[str, str] | None = None,
    ) -> None:
        if not base_url or not base_url.strip():
            raise ValueError("base_url is required")
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.default_headers = dict(default_headers or {})

    def get_health(self) -> JsonDict:
        return self._request("GET", "/health")

    def get_dependency_health(self) -> JsonDict:
        return self._request("GET", "/health/dependencies")

    def get_metrics_summary(self) -> JsonDict:
        return self._request("GET", "/metrics/summary")

    def get_dashboard_presentation(self) -> JsonDict:
        return self._request("GET", "/config/dashboard-presentation")

    def list_watchers(self, params: Mapping[str, Any] | None = None) -> JsonDict:
        return self._request("GET", "/watchers", params=params)

    def get_watcher(self, watcher_id: str) -> JsonDict:
        return self._request("GET", f"/watchers/{_quote_path(watcher_id)}")

    def create_watcher(self, payload: Mapping[str, Any]) -> JsonDict:
        return self._request("POST", "/watchers", payload=payload)

    def patch_watcher(self, watcher_id: str, payload: Mapping[str, Any]) -> JsonDict:
        return self._request("PATCH", f"/watchers/{_quote_path(watcher_id)}", payload=payload)

    def preview_routes(self, watcher_id: str, payload: Mapping[str, Any]) -> JsonDict:
        return self._request("POST", f"/watchers/{_quote_path(watcher_id)}/preview-routes", payload=payload)

    def watcher_command(
        self,
        watcher_id: str,
        action: str,
        payload: Mapping[str, Any],
        *,
        idempotency_key: str | None = None,
    ) -> JsonDict:
        if action not in _WATCHER_ACTIONS:
            allowed = ", ".join(sorted(_WATCHER_ACTIONS))
            raise ValueError(f"Unsupported watcher action {action!r}; expected one of: {allowed}")
        headers = {"Idempotency-Key": idempotency_key} if idempotency_key else None
        return self._request("POST", f"/watchers/{_quote_path(watcher_id)}/{action}", payload=payload, headers=headers)

    def browse_files(self, params: Mapping[str, Any]) -> JsonDict:
        return self._request("GET", "/files/browse", params=params)

    def validate_path(self, payload: Mapping[str, Any]) -> JsonDict:
        return self._request("POST", "/files/validate-path", payload=payload)

    def list_jobs(self, params: Mapping[str, Any] | None = None) -> JsonDict:
        return self._request("GET", "/jobs", params=params)

    def get_job(self, job_id: str) -> JsonDict:
        return self._request("GET", f"/jobs/{_quote_path(job_id)}")

    def get_job_history(self, job_id: str) -> JsonDict:
        return self._request("GET", f"/jobs/{_quote_path(job_id)}/history")

    def retry_job(
        self,
        job_id: str,
        payload: Mapping[str, Any],
        *,
        idempotency_key: str | None = None,
    ) -> JsonDict:
        headers = {"Idempotency-Key": idempotency_key} if idempotency_key else None
        return self._request("POST", f"/jobs/{_quote_path(job_id)}/retry", payload=payload, headers=headers)

    def get_command_status(self, command_id: str) -> JsonDict:
        return self._request("GET", f"/commands/{_quote_path(command_id)}")

    def list_events(self, params: Mapping[str, Any] | None = None) -> JsonDict:
        return self._request("GET", "/events", params=params)

    def list_logs(self, params: Mapping[str, Any] | None = None) -> JsonDict:
        return self._request("GET", "/logs", params=params)

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        payload: Mapping[str, Any] | None = None,
        headers: Mapping[str, str | None] | None = None,
    ) -> JsonDict:
        url = self._build_url(path, params=params)
        body: bytes | None = None
        request_headers = dict(self.default_headers)
        request_headers.update({key: value for key, value in (headers or {}).items() if value is not None})
        if payload is not None:
            body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
            request_headers.setdefault("Content-Type", "application/json")
            request_headers.setdefault("Accept", "application/json")
        else:
            request_headers.setdefault("Accept", "application/json")

        req = request.Request(url, data=body, headers=request_headers, method=method)
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:  # noqa: S310 - local control-plane URL supplied by deployment.
                return _decode_json_response(response.read())
        except error.HTTPError as exc:
            payload_dict = _decode_json_response(exc.read())
            raise StreamLiteApiError(
                status_code=exc.code,
                error_code=_extract_error_code(payload_dict),
                message=_extract_error_message(payload_dict),
                payload=payload_dict,
            ) from exc
        except error.URLError as exc:
            raise StreamLiteApiError(status_code=0, error_code="API_UNAVAILABLE", message=str(exc.reason)) from exc

    def _build_url(self, path: str, *, params: Mapping[str, Any] | None = None) -> str:
        if not path.startswith("/"):
            path = f"/{path}"
        url = f"{self.base_url}{path}"
        query = _encode_query(params or {})
        return f"{url}?{query}" if query else url


def poll_command_until_terminal(
    client: StreamLiteApiClient,
    command_id: str,
    *,
    interval_seconds: float = 1.0,
    max_attempts: int = 30,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> CommandPollResult:
    """Poll a command until it reaches a terminal status or attempts are exhausted."""

    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    last_payload: JsonDict | None = None
    for attempt in range(1, max_attempts + 1):
        last_payload = client.get_command_status(command_id)
        status = last_payload.get("status")
        if status in _TERMINAL_COMMAND_STATUSES or attempt == max_attempts:
            return CommandPollResult(
                command_id=str(last_payload.get("command_id", command_id)),
                status=None if status is None else str(status),
                attempts=attempt,
                result=_dict_or_none(last_payload.get("result")),
                error=_dict_or_none(last_payload.get("error")),
                last_payload=last_payload,
            )
        sleep_fn(interval_seconds)

    # Unreachable because max_attempts is validated, retained for type checkers.
    return CommandPollResult(
        command_id=command_id,
        status=None,
        attempts=max_attempts,
        result=None,
        error=None,
        last_payload=last_payload,
    )


def _encode_query(params: Mapping[str, Any]) -> str:
    pairs: list[tuple[str, Any]] = []
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            pairs.extend((key, item) for item in value if item is not None)
        else:
            pairs.append((key, value))
    return parse.urlencode(pairs, doseq=True)


def _quote_path(value: str) -> str:
    return parse.quote(str(value), safe="")


def _decode_json_response(raw: bytes) -> JsonDict:
    if not raw:
        return {}
    try:
        decoded = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"raw_body": raw.decode("utf-8", errors="replace")}
    return decoded if isinstance(decoded, dict) else {"data": decoded}


def _extract_error_code(payload: Mapping[str, Any]) -> str | None:
    value = payload.get("error_code") or payload.get("code")
    if value is None and isinstance(payload.get("error"), Mapping):
        value = payload["error"].get("error_code") or payload["error"].get("code")
    return None if value is None else str(value)


def _extract_error_message(payload: Mapping[str, Any]) -> str | None:
    value = payload.get("message") or payload.get("detail")
    if value is None and isinstance(payload.get("error"), Mapping):
        value = payload["error"].get("message") or payload["error"].get("detail")
    return None if value is None else str(value)


def _dict_or_none(value: Any) -> JsonDict | None:
    return value if isinstance(value, dict) else None


__all__ = [
    "CommandPollResult",
    "StreamLiteApiClient",
    "StreamLiteApiError",
    "poll_command_until_terminal",
]
