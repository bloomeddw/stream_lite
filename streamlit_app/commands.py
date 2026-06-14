"""Command submission and display helpers for the Streamlit dashboard."""

from __future__ import annotations

import inspect
import time
from typing import Any, Callable, Mapping

from streamlit_app.api_client import StreamLiteApiError, poll_command_until_terminal

JsonDict = dict[str, Any]


def submit_and_track_command(
    *,
    submit_fn: Callable[..., Mapping[str, Any]],
    submit_payload: dict,
    client: Any,
    config: Any,
    idempotency_key: str | None = None,
    poll: bool = True,
    max_attempts: int = 30,
    sleep_fn: Callable[[float], None] | None = None,
) -> JsonDict:
    """Submit a dashboard mutation and optionally poll its command status."""

    try:
        response = _submit(submit_fn, submit_payload, idempotency_key=idempotency_key)
    except StreamLiteApiError as exc:
        return _api_error_card(exc)

    card: JsonDict = {
        "accepted": response.get("status") == "accepted" and bool(response.get("command_id")),
        "command_id": response.get("command_id"),
        "status": response.get("status"),
        "target_resource_type": response.get("target_resource_type"),
        "target_resource_id": response.get("target_resource_id"),
        "accepted_at": response.get("accepted_at"),
        "correlation_id": response.get("correlation_id"),
    }
    if not card["accepted"]:
        card.update(
            {
                "accepted": False,
                "status": "failed",
                "error_code": response.get("error_code") or "COMMAND_SUBMISSION_INVALID",
                "message": response.get("message") or "Command response was not accepted.",
                "payload": response,
            }
        )
        return card

    if poll:
        poll_result = poll_command_until_terminal(
            client,
            str(card["command_id"]),
            interval_seconds=float(getattr(config, "refresh_interval_seconds", 2)),
            max_attempts=max_attempts,
            sleep_fn=sleep_fn or time.sleep,
        )
        card.update(
            {
                "terminal_status": poll_result.status,
                "result": poll_result.result,
                "error": poll_result.error,
                "attempts": poll_result.attempts,
                "latest_message": _latest_message(poll_result.status, poll_result.result, poll_result.error),
            }
        )
    return card


def build_command_status_display(command_card: Mapping[str, Any]) -> JsonDict:
    """Return display-safe command status fields for Streamlit rendering."""

    error = _dict_or_empty(command_card.get("error"))
    result = _dict_or_empty(command_card.get("result"))
    return {
        "command_id": command_card.get("command_id"),
        "status": command_card.get("status"),
        "terminal_status": command_card.get("terminal_status"),
        "message": command_card.get("latest_message") or command_card.get("message") or error.get("message"),
        "error_code": command_card.get("error_code") or error.get("error_code"),
        "target_resource_type": command_card.get("target_resource_type"),
        "target_resource_id": command_card.get("target_resource_id"),
        "correlation_id": command_card.get("correlation_id") or error.get("correlation_id"),
        "result_locator": result.get("locator"),
    }


def _submit(
    submit_fn: Callable[..., Mapping[str, Any]],
    submit_payload: dict,
    *,
    idempotency_key: str | None,
) -> JsonDict:
    if idempotency_key and _accepts_idempotency_key(submit_fn):
        return _dict_or_empty(submit_fn(submit_payload, idempotency_key=idempotency_key))
    return _dict_or_empty(submit_fn(submit_payload))


def _accepts_idempotency_key(submit_fn: Callable[..., Mapping[str, Any]]) -> bool:
    try:
        signature = inspect.signature(submit_fn)
    except (TypeError, ValueError):
        return False
    for parameter in signature.parameters.values():
        if parameter.kind == inspect.Parameter.VAR_KEYWORD:
            return True
        if parameter.name == "idempotency_key":
            return True
    return False


def _api_error_card(exc: StreamLiteApiError) -> JsonDict:
    payload = _dict_or_empty(exc.payload)
    error = _dict_or_empty(payload.get("error"))
    return {
        "accepted": False,
        "status": "failed",
        "error_code": exc.error_code or error.get("error_code") or payload.get("error_code"),
        "message": exc.message,
        "payload": payload,
        "correlation_id": payload.get("correlation_id") or error.get("correlation_id"),
    }


def _latest_message(status: str | None, result: Mapping[str, Any] | None, error: Mapping[str, Any] | None) -> str | None:
    error_dict = _dict_or_empty(error)
    result_dict = _dict_or_empty(result)
    return error_dict.get("message") or result_dict.get("locator") or status


def _dict_or_empty(value: Any) -> JsonDict:
    return dict(value) if isinstance(value, Mapping) else {}


__all__ = ["build_command_status_display", "submit_and_track_command"]
