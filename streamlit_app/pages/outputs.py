"""Output and delivery visibility helpers."""

from __future__ import annotations

from typing import Any, Mapping

from streamlit_app.pages.jobs import build_job_detail_view_model
from streamlit_app.theme import get_status_token

JsonDict = dict[str, Any]
_OUTPUT_STATES = ("DELIVERED", "COMPLETED", "COMPLETED_WITH_DELIVERY_ERRORS")


def build_outputs_view_model(client: Any, config: Mapping[str, Any] | Any) -> JsonDict:
    """Build delivered-output rows from job state filters."""

    payloads = [(state, _dict_or_empty(client.list_jobs(params={"state": state}))) for state in _OUTPUT_STATES]
    rows = []
    for _, payload in payloads:
        rows.extend(_job_rows(config, payload))
    rows = _sort_updated_desc(rows)
    return {
        "rows": rows,
        "total": len(rows),
        "empty_message": "No delivered outputs found." if not rows else None,
        "refresh_interval_seconds": int(getattr(config, "refresh_interval_seconds", 2)),
        "correlation_id": next((payload.get("correlation_id") for _, payload in payloads if payload.get("correlation_id")), None),
    }


def build_output_detail_view_model(client: Any, config: Mapping[str, Any] | Any, job_id: str) -> JsonDict:
    """Reuse job detail to display output destinations and attempts."""

    return build_job_detail_view_model(client, config, job_id)


def render_outputs_page(client: Any, config: Mapping[str, Any] | Any) -> None:
    """Render output visibility when Streamlit runtime is available."""

    import streamlit as st

    view_model = build_outputs_view_model(client, config)
    st.header("Outputs")
    if view_model["rows"]:
        st.table(view_model["rows"])
        job_id = st.selectbox(
            "Job",
            [str(row["job_id"]) for row in view_model["rows"] if row.get("job_id")],
            key="outputs_selected_job_id",
        )
        if job_id:
            detail = build_output_detail_view_model(client, config, job_id)
            st.subheader("Output detail")
            st.table(detail["destinations"])
            st.json(detail["attempt_summary"])
    else:
        st.info(view_model["empty_message"])


def _job_rows(config: Mapping[str, Any] | Any, payload: Mapping[str, Any]) -> list[JsonDict]:
    rows = []
    for item in _items(payload.get("items")):
        state = item.get("state")
        rows.append(
            {
                "job_id": item.get("job_id"),
                "watcher_id": item.get("watcher_id"),
                "state": state,
                "source_display_path": item.get("source_display_path"),
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at"),
                "latest_error_code": item.get("latest_error_code"),
                "state_token": get_status_token(config, _state_status_key(state)),
            }
        )
    return rows


def _state_status_key(state: Any) -> str:
    if str(state or "").upper() == "COMPLETED_WITH_DELIVERY_ERRORS":
        return "failed"
    return "green"


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


__all__ = ["build_output_detail_view_model", "build_outputs_view_model", "render_outputs_page"]
