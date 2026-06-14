"""Read-only operational log page helpers."""

from __future__ import annotations

from typing import Any, Mapping

JsonDict = dict[str, Any]


def build_logs_view_model(client: Any, config: Mapping[str, Any] | Any, params: Mapping[str, Any] | None = None) -> JsonDict:
    """Build operator-safe log rows from the FastAPI log endpoint."""

    payload = _dict_or_empty(client.list_logs(params=params))
    rows: list[JsonDict] = []
    for item in _items(payload.get("items")):
        rows.append(
            {
                "timestamp": item.get("timestamp"),
                "level": item.get("level"),
                "service": item.get("service"),
                "event": item.get("event"),
                "message": item.get("message"),
                "correlation_id": item.get("correlation_id"),
                "job_id": item.get("job_id"),
                "error_code": item.get("error_code"),
                "duration_ms": item.get("duration_ms"),
            }
        )
    return {
        "rows": rows,
        "total": int(payload.get("total", len(rows)) or 0),
        "limit": payload.get("limit"),
        "offset": payload.get("offset"),
        "empty_message": "No operational logs found." if not rows else None,
        "refresh_interval_seconds": int(getattr(config, "refresh_interval_seconds", 2)),
        "correlation_id": payload.get("correlation_id"),
    }


def render_logs_page(client: Any, config: Mapping[str, Any] | Any) -> None:
    """Render the logs page when Streamlit runtime is available."""

    import streamlit as st

    view_model = build_logs_view_model(client, config)
    st.header("Logs")
    if view_model["rows"]:
        st.table(view_model["rows"])
    else:
        st.info(view_model["empty_message"])


def _items(value: Any) -> list[JsonDict]:
    if isinstance(value, list):
        return [dict(item) for item in value if isinstance(item, Mapping)]
    return []


def _dict_or_empty(value: Any) -> JsonDict:
    return dict(value) if isinstance(value, Mapping) else {}


__all__ = ["build_logs_view_model", "render_logs_page"]
