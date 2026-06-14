"""Validation failure and quarantine visibility helpers."""

from __future__ import annotations

from typing import Any, Mapping

from streamlit_app.commands import build_command_status_display
from streamlit_app.pages.jobs import submit_job_retry
from streamlit_app.theme import get_status_token

JsonDict = dict[str, Any]


def build_quarantine_view_model(client: Any, config: Mapping[str, Any] | Any) -> JsonDict:
    """Build validation-failure and quarantine rows from job filters."""

    invalid_payload = _dict_or_empty(client.list_jobs(params={"state": "INVALID"}))
    quarantined_payload = _dict_or_empty(client.list_jobs(params={"state": "QUARANTINED"}))
    rows = [
        *_job_rows(config, invalid_payload, bucket="validation_failure"),
        *_job_rows(config, quarantined_payload, bucket="quarantine"),
    ]
    rows = _sort_updated_desc(rows)
    return {
        "rows": rows,
        "total": len(rows),
        "empty_message": "No validation failures or quarantined jobs found." if not rows else None,
        "refresh_interval_seconds": int(getattr(config, "refresh_interval_seconds", 2)),
        "correlation_id": invalid_payload.get("correlation_id") or quarantined_payload.get("correlation_id"),
    }


def render_quarantine_page(client: Any, config: Mapping[str, Any] | Any) -> None:
    """Render quarantine visibility when Streamlit runtime is available."""

    import streamlit as st

    view_model = build_quarantine_view_model(client, config)
    st.header("Quarantine")
    if view_model["rows"]:
        st.table(view_model["rows"])
        job_id = st.selectbox(
            "Job",
            [str(row["job_id"]) for row in view_model["rows"] if row.get("job_id")],
            key="quarantine_selected_job_id",
        )
        requested_by = st.text_input("Operator", key=f"quarantine_retry_operator_{job_id}")
        reason = st.text_input("Reason", key=f"quarantine_retry_reason_{job_id}")
        if st.button("Retry", key=f"quarantine_retry_{job_id}"):
            st.session_state[f"quarantine_retry_command_{job_id}"] = submit_job_retry(
                client,
                config,
                job_id=job_id,
                requested_by=requested_by,
                reason=reason,
                idempotency_key=f"quarantine-retry-{job_id}",
            )
        command_card = st.session_state.get(f"quarantine_retry_command_{job_id}")
        if command_card:
            st.json(build_command_status_display(command_card))
    else:
        st.info(view_model["empty_message"])


def _job_rows(config: Mapping[str, Any] | Any, payload: Mapping[str, Any], *, bucket: str) -> list[JsonDict]:
    rows = []
    for item in _items(payload.get("items")):
        state = item.get("state")
        rows.append(
            {
                "bucket": bucket,
                "job_id": item.get("job_id"),
                "watcher_id": item.get("watcher_id"),
                "state": state,
                "source_display_path": item.get("source_display_path"),
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at"),
                "latest_error_code": item.get("latest_error_code"),
                "state_token": get_status_token(config, "failed"),
            }
        )
    return rows


def _sort_updated_desc(rows: list[JsonDict]) -> list[JsonDict]:
    with_timestamp = [row for row in rows if row.get("updated_at")]
    without_timestamp = [row for row in rows if not row.get("updated_at")]
    return sorted(with_timestamp, key=lambda row: str(row.get("updated_at")), reverse=True) + without_timestamp


def _items(value: Any) -> list[JsonDict]:
    if isinstance(value, list):
        return [dict(item) for item in value if isinstance(item, Mapping)]
    return []


def _dict_or_empty(value: Any) -> JsonDict:
    return dict(value) if isinstance(value, Mapping) else {}


__all__ = ["build_quarantine_view_model", "render_quarantine_page"]
