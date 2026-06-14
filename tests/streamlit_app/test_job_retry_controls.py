from __future__ import annotations

import pytest

from streamlit_app.api_client import StreamLiteApiError
from streamlit_app.commands import build_command_status_display
from streamlit_app.pages.jobs import build_retry_request_payload, submit_job_retry
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


class _RetryClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []
        self.raise_retry = False
        self.statuses = ["succeeded"]

    def retry_job(self, job_id, payload, *, idempotency_key=None):
        self.calls.append(("retry_job", (job_id, payload, idempotency_key)))
        if self.raise_retry:
            raise StreamLiteApiError(
                status_code=409,
                error_code="JOB_NOT_RETRYABLE",
                message="Job is not retryable.",
                payload={"correlation_id": "33333333-3333-4333-8333-333333333333"},
            )
        return {
            "status": "accepted",
            "command_id": "22222222-2222-4222-8222-222222222222",
            "target_resource_type": "job",
            "target_resource_id": job_id,
            "accepted_at": "2026-05-06T12:00:00Z",
            "correlation_id": "33333333-3333-4333-8333-333333333333",
        }

    def get_command_status(self, command_id):
        status = self.statuses.pop(0)
        return {
            "command_id": command_id,
            "status": status,
            "target_resource_type": "job",
            "target_resource_id": "11111111-1111-4111-8111-111111111111",
            "result": {"locator": "/stream-lite/output/orders.csv"} if status == "succeeded" else None,
            "error": {"error_code": "COMMAND_FAILED", "message": "Command failed."} if status == "failed" else None,
            "correlation_id": "33333333-3333-4333-8333-333333333333",
        }


def test_build_retry_request_payload_strips_and_rejects_empty_fields() -> None:
    assert build_retry_request_payload(requested_by=" operator ", reason=" retry delivery ") == {
        "requested_by": "operator",
        "reason": "retry delivery",
    }
    with pytest.raises(ValueError, match="Operator"):
        build_retry_request_payload(requested_by=" ", reason="retry")
    with pytest.raises(ValueError, match="Reason"):
        build_retry_request_payload(requested_by="operator", reason=" ")


def test_submit_job_retry_calls_api_with_payload_and_idempotency_key() -> None:
    client = _RetryClient()

    card = submit_job_retry(
        client,
        _config(),
        job_id="11111111-1111-4111-8111-111111111111",
        requested_by="operator",
        reason="retry delivery",
        idempotency_key="retry-key",
        sleep_fn=lambda _: None,
    )

    assert client.calls[0] == (
        "retry_job",
        (
            "11111111-1111-4111-8111-111111111111",
            {"requested_by": "operator", "reason": "retry delivery"},
            "retry-key",
        ),
    )
    assert card["accepted"] is True
    assert card["terminal_status"] == "succeeded"
    assert card["latest_message"] == "/stream-lite/output/orders.csv"


def test_submit_job_retry_returns_api_error_card_for_not_retryable() -> None:
    client = _RetryClient()
    client.raise_retry = True

    card = submit_job_retry(
        client,
        _config(),
        job_id="11111111-1111-4111-8111-111111111111",
        requested_by="operator",
        reason="retry delivery",
        idempotency_key="retry-key",
    )

    assert card["accepted"] is False
    assert card["status"] == "failed"
    assert card["error_code"] == "JOB_NOT_RETRYABLE"
    assert card["message"] == "Job is not retryable."


def test_submit_job_retry_returns_input_error_without_api_call() -> None:
    client = _RetryClient()

    card = submit_job_retry(
        client,
        _config(),
        job_id="11111111-1111-4111-8111-111111111111",
        requested_by="operator",
        reason=" ",
    )

    assert card["accepted"] is False
    assert card["error_code"] == "DASHBOARD_RETRY_INPUT_INVALID"
    assert client.calls == []


def test_command_feedback_display_includes_retry_rejection_without_raw_exception_text() -> None:
    display = build_command_status_display(
        {
            "accepted": False,
            "status": "failed",
            "error_code": "JOB_NOT_RETRYABLE",
            "message": "Job is not retryable.",
            "correlation_id": "33333333-3333-4333-8333-333333333333",
        }
    )

    assert display["status"] == "failed"
    assert display["error_code"] == "JOB_NOT_RETRYABLE"
    assert display["message"] == "Job is not retryable."
    assert display["correlation_id"] == "33333333-3333-4333-8333-333333333333"
    assert "StreamLiteApiError" not in str(display)
