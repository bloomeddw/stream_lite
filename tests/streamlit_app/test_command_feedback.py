from __future__ import annotations

from streamlit_app.api_client import StreamLiteApiError
from streamlit_app.commands import build_command_status_display, submit_and_track_command
from streamlit_app.theme import load_presentation_config


def _config():
    return load_presentation_config(
        {
            "schema_version": "1.0.0",
            "theme_name": "default_light",
            "color_tokens": {},
            "status_dot_tokens": {},
            "layout_profile": "operator_default",
            "layout_sections": [],
            "refresh_interval_seconds": 1,
            "correlation_id": "33333333-3333-4333-8333-333333333333",
        }
    )


class _CommandClient:
    def __init__(self) -> None:
        self.calls = 0

    def get_command_status(self, command_id: str) -> dict[str, object]:
        self.calls += 1
        if self.calls == 1:
            return {
                "command_id": command_id,
                "status": "running",
                "target_resource_type": "job",
                "target_resource_id": "11111111-1111-4111-8111-111111111111",
                "result": None,
                "error": None,
                "correlation_id": "33333333-3333-4333-8333-333333333333",
            }
        return {
            "command_id": command_id,
            "status": "succeeded",
            "target_resource_type": "job",
            "target_resource_id": "11111111-1111-4111-8111-111111111111",
            "result": {"locator": "/stream-lite/output/orders.csv"},
            "error": None,
            "correlation_id": "33333333-3333-4333-8333-333333333333",
        }


def test_submit_and_track_command_polls_accepted_to_terminal_status() -> None:
    seen = {}

    def submit(payload, *, idempotency_key=None):
        seen["payload"] = payload
        seen["idempotency_key"] = idempotency_key
        return {
            "status": "accepted",
            "command_id": "22222222-2222-4222-8222-222222222222",
            "target_resource_type": "job",
            "target_resource_id": "11111111-1111-4111-8111-111111111111",
            "accepted_at": "2026-05-06T12:00:00Z",
            "correlation_id": "33333333-3333-4333-8333-333333333333",
        }

    card = submit_and_track_command(
        submit_fn=submit,
        submit_payload={"requested_by": "operator"},
        client=_CommandClient(),
        config=_config(),
        idempotency_key="retry-key",
        sleep_fn=lambda _: None,
    )

    assert seen == {"payload": {"requested_by": "operator"}, "idempotency_key": "retry-key"}
    assert card["accepted"] is True
    assert card["status"] == "accepted"
    assert card["terminal_status"] == "succeeded"
    assert card["latest_message"] == "/stream-lite/output/orders.csv"


def test_submit_and_track_command_returns_api_error_card() -> None:
    def submit(payload):
        raise StreamLiteApiError(
            status_code=409,
            error_code="JOB_NOT_RETRYABLE",
            message="Job is not retryable.",
            payload={"correlation_id": "33333333-3333-4333-8333-333333333333"},
        )

    card = submit_and_track_command(submit_fn=submit, submit_payload={}, client=_CommandClient(), config=_config())

    assert card["accepted"] is False
    assert card["status"] == "failed"
    assert card["error_code"] == "JOB_NOT_RETRYABLE"
    assert card["correlation_id"] == "33333333-3333-4333-8333-333333333333"


def test_command_status_display_uses_safe_fields() -> None:
    display = build_command_status_display(
        {
            "command_id": "cmd-1",
            "status": "accepted",
            "terminal_status": "failed",
            "target_resource_type": "job",
            "target_resource_id": "job-1",
            "correlation_id": "corr-1",
            "error": {"error_code": "JOB_NOT_RETRYABLE", "message": "Job is not retryable."},
            "result": {"locator": "/stream-lite/output/orders.csv"},
        }
    )

    assert display["command_id"] == "cmd-1"
    assert display["status"] == "accepted"
    assert display["terminal_status"] == "failed"
    assert display["error_code"] == "JOB_NOT_RETRYABLE"
    assert display["message"] == "Job is not retryable."
    assert display["correlation_id"] == "corr-1"
    assert "Traceback" not in str(display)
