"""Jobs page view-model, detail/history, and retry helpers."""

from __future__ import annotations

from typing import Any, Mapping
from uuid import uuid4

from streamlit_app.commands import build_command_status_display, submit_and_track_command
from streamlit_app.theme import get_status_token

JsonDict = dict[str, Any]
_RETRY_VISIBLE_STATES = {"FAILED", "COMPLETED_WITH_DELIVERY_ERRORS", "QUARANTINED"}


def build_jobs_view_model(client: Any, config: Mapping[str, Any] | Any, params: Mapping[str, Any] | None = None) -> JsonDict:
    """Build recent-job table rows from the FastAPI jobs endpoint."""

    payload = _dict_or_empty(client.list_jobs(params=params))
    rows: list[JsonDict] = []
    for item in _items(payload.get("items")):
        state = item.get("state")
        rows.append(
            {
                "job_id": item.get("job_id"),
                "watcher_id": item.get("watcher_id"),
                "state": state,
                "state_token": get_status_token(config, _job_state_status_key(state)),
                "source_display_path": item.get("source_display_path"),
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at"),
                "latest_error_code": item.get("latest_error_code"),
            }
        )
    return {
        "rows": rows,
        "total": int(payload.get("total", len(rows)) or 0),
        "limit": payload.get("limit"),
        "offset": payload.get("offset"),
        "empty_message": "No jobs found." if not rows else None,
        "refresh_interval_seconds": int(getattr(config, "refresh_interval_seconds", 2)),
        "correlation_id": payload.get("correlation_id"),
    }


def build_job_detail_view_model(client: Any, config: Mapping[str, Any] | Any, job_id: str) -> JsonDict:
    """Build job detail, attempts, latest error, and state history."""

    detail = _dict_or_empty(client.get_job(job_id))
    history = _dict_or_empty(client.get_job_history(job_id))
    state = detail.get("state")
    source = _dict_or_empty(detail.get("source"))
    attempt_summary = _dict_or_empty(detail.get("attempt_summary"))
    latest_error = _dict_or_none(detail.get("latest_error"))
    destinations = []
    for destination in _items(detail.get("destinations")):
        status = destination.get("status")
        reason_code = destination.get("reason_code")
        destinations.append(
            {
                "destination_folder_id": destination.get("destination_folder_id"),
                "display_path": destination.get("display_path"),
                "route_tags": _string_list(destination.get("route_tags")),
                "matched_tags": _string_list(destination.get("matched_tags")),
                "status": status,
                "reason_code": reason_code,
                "status_token": get_status_token(config, _destination_token_key(status, reason_code)),
            }
        )

    return {
        "job_id": detail.get("job_id", job_id),
        "watcher_id": detail.get("watcher_id"),
        "state": state,
        "state_token": get_status_token(config, _job_state_status_key(state)),
        "source": {
            "file_id": source.get("file_id"),
            "display_path": source.get("display_path"),
            "source_folder_id": source.get("source_folder_id"),
            "size_bytes": source.get("size_bytes"),
            "sha256": source.get("sha256"),
        },
        "destinations": destinations,
        "attempt_summary": {
            "validation_attempts": attempt_summary.get("validation_attempts", 0),
            "processing_attempts": attempt_summary.get("processing_attempts", 0),
            "delivery_attempts": attempt_summary.get("delivery_attempts", 0),
            "retry_attempts": attempt_summary.get("retry_attempts", 0),
            "last_attempt_at": attempt_summary.get("last_attempt_at"),
        },
        "latest_error": _latest_error_view(latest_error),
        "history": [
            {
                "from_state": row.get("from_state"),
                "to_state": row.get("to_state"),
                "actor_service": row.get("actor_service"),
                "reason_code": row.get("reason_code"),
                "occurred_at": row.get("occurred_at"),
                "event_id": row.get("event_id"),
            }
            for row in _items(history.get("history"))
        ],
        "correlation_id": detail.get("correlation_id") or history.get("correlation_id"),
    }


def build_retry_request_payload(*, requested_by: str, reason: str) -> JsonDict:
    """Build a manual retry command payload."""

    operator = str(requested_by or "").strip()
    retry_reason = str(reason or "").strip()
    if not operator:
        raise ValueError("Operator is required for manual retry.")
    if not retry_reason:
        raise ValueError("Reason is required for manual retry.")
    return {"requested_by": operator, "reason": retry_reason}


def submit_job_retry(
    client: Any,
    config: Mapping[str, Any] | Any,
    *,
    job_id: str,
    requested_by: str,
    reason: str,
    idempotency_key: str | None = None,
    sleep_fn: Any = None,
) -> JsonDict:
    """Submit a manual retry command through the API client."""

    try:
        payload = build_retry_request_payload(requested_by=requested_by, reason=reason)
    except ValueError as exc:
        return {
            "accepted": False,
            "status": "failed",
            "error_code": "DASHBOARD_RETRY_INPUT_INVALID",
            "message": str(exc),
        }

    def submit(payload_to_submit: Mapping[str, Any], *, idempotency_key: str | None = None) -> Mapping[str, Any]:
        return client.retry_job(job_id, payload_to_submit, idempotency_key=idempotency_key)

    return submit_and_track_command(
        submit_fn=submit,
        submit_payload=payload,
        client=client,
        config=config,
        idempotency_key=idempotency_key,
        sleep_fn=sleep_fn,
    )


def render_jobs_page(client: Any, config: Mapping[str, Any] | Any) -> None:
    """Render the jobs page when Streamlit runtime is available."""

    import streamlit as st

    view_model = build_jobs_view_model(client, config)
    st.header("Jobs")
    if view_model["rows"]:
        st.table(view_model["rows"])
        selected_job_id = st.selectbox(
            "Job",
            [str(row["job_id"]) for row in view_model["rows"] if row.get("job_id")],
            key="jobs_selected_job_id",
        )
        if selected_job_id:
            _render_job_detail(client, config, selected_job_id)
    else:
        st.info(view_model["empty_message"])


def _render_job_detail(client: Any, config: Mapping[str, Any] | Any, job_id: str) -> None:
    import streamlit as st

    detail = build_job_detail_view_model(client, config, job_id)
    st.subheader("Job detail")
    st.json(
        {
            "job_id": detail["job_id"],
            "watcher_id": detail["watcher_id"],
            "state": detail["state"],
            "source": detail["source"],
            "attempt_summary": detail["attempt_summary"],
            "latest_error": detail["latest_error"],
        }
    )
    st.subheader("Destinations")
    st.table(detail["destinations"])
    st.subheader("State history")
    st.table(detail["history"])
    if detail.get("state") in _RETRY_VISIBLE_STATES:
        _render_retry_control(client, config, job_id)


def _render_retry_control(client: Any, config: Mapping[str, Any] | Any, job_id: str) -> None:
    import streamlit as st

    st.subheader("Manual retry")
    requested_by = st.text_input("Operator", key=f"retry_operator_{job_id}")
    reason = st.text_input("Reason", key=f"retry_reason_{job_id}")
    if st.button("Retry", key=f"retry_submit_{job_id}"):
        idempotency_key = f"job-retry-{job_id}-{uuid4()}"
        st.session_state[f"retry_idempotency_key_{job_id}"] = idempotency_key
        st.session_state[f"retry_command_{job_id}"] = submit_job_retry(
            client,
            config,
            job_id=job_id,
            requested_by=requested_by,
            reason=reason,
            idempotency_key=idempotency_key,
        )
    command_card = st.session_state.get(f"retry_command_{job_id}")
    if command_card:
        st.json(build_command_status_display(command_card))


def _latest_error_view(latest_error: Mapping[str, Any] | None) -> JsonDict | None:
    if latest_error is None:
        return None
    return {
        "error_code": latest_error.get("error_code"),
        "message": latest_error.get("message"),
        "field": latest_error.get("field"),
        "resource_id": latest_error.get("resource_id"),
        "current_state": latest_error.get("current_state"),
        "correlation_id": latest_error.get("correlation_id"),
    }


def _job_state_status_key(value: Any) -> str:
    state = str(value or "").upper()
    if state in {"FAILED", "INVALID", "QUARANTINED", "COMPLETED_WITH_DELIVERY_ERRORS"}:
        return "failed"
    if state in {"COMPLETED", "DELIVERED"}:
        return "green"
    if state in {"DETECTED", "STABILIZING", "REGISTERED", "VALIDATING", "VALIDATED", "PROCESSING", "PROCESSED", "DELIVERING", "RETRY_PENDING"}:
        return "pending"
    return "unknown"


def _destination_status_key(value: Any) -> str:
    status = str(value or "").lower()
    if status == "delivered":
        return "green"
    if status == "failed":
        return "failed"
    if status in {"pending", "skipped"}:
        return "pending"
    return "unknown"


def _destination_token_key(status: Any, reason_code: Any) -> str:
    if str(status or "").lower() == "failed":
        return "failed"
    return str(reason_code) if reason_code else _destination_status_key(status)


def _items(value: Any) -> list[JsonDict]:
    if isinstance(value, list):
        return [dict(item) for item in value if isinstance(item, Mapping)]
    return []


def _dict_or_empty(value: Any) -> JsonDict:
    return dict(value) if isinstance(value, Mapping) else {}


def _dict_or_none(value: Any) -> JsonDict | None:
    return dict(value) if isinstance(value, Mapping) else None


def _string_list(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


__all__ = [
    "build_job_detail_view_model",
    "build_jobs_view_model",
    "build_retry_request_payload",
    "render_jobs_page",
    "submit_job_retry",
]
