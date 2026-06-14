"""Read-only event stream page helpers."""

from __future__ import annotations

from typing import Any, Mapping

JsonDict = dict[str, Any]


def build_events_view_model(client: Any, config: Mapping[str, Any] | Any, params: Mapping[str, Any] | None = None) -> JsonDict:
    """Build event rows from the FastAPI event list endpoint."""

    payload = _dict_or_empty(client.list_events(params=params))
    rows: list[JsonDict] = []
    for item in _items(payload.get("items")):
        rows.append(
            {
                "event_id": item.get("event_id"),
                "event_type": item.get("event_type"),
                "stream_name": item.get("stream_name"),
                "producer": item.get("producer"),
                "job_id": item.get("job_id"),
                "watcher_id": item.get("watcher_id"),
                "occurred_at": item.get("occurred_at"),
                "created_at": item.get("created_at"),
                "published_at": item.get("published_at"),
            }
        )
    return {
        "rows": rows,
        "total": int(payload.get("total", len(rows)) or 0),
        "limit": payload.get("limit"),
        "offset": payload.get("offset"),
        "empty_message": "No events found." if not rows else None,
        "refresh_interval_seconds": int(getattr(config, "refresh_interval_seconds", 2)),
        "correlation_id": payload.get("correlation_id"),
    }


def render_events_page(client: Any, config: Mapping[str, Any] | Any) -> None:
    """Render the events page when Streamlit runtime is available."""

    import streamlit as st

    view_model = build_events_view_model(client, config)
    st.header("Events")
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


__all__ = ["build_events_view_model", "render_events_page"]
