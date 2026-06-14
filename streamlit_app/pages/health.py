"""Read-only health overview page helpers."""

from __future__ import annotations

from typing import Any, Mapping

from streamlit_app.theme import get_status_token

JsonDict = dict[str, Any]


def build_health_view_model(client: Any, config: Mapping[str, Any] | Any) -> JsonDict:
    """Build an operator-safe health summary from API responses."""

    health = _dict_or_empty(client.get_health())
    dependency_health = _dict_or_empty(client.get_dependency_health())
    metrics = _dict_or_empty(client.get_metrics_summary())
    api_status = str(health.get("status", "unknown"))
    dependencies = []
    for item in _items(dependency_health.get("dependencies")):
        status = str(item.get("status", "unknown"))
        reason = item.get("error_code") or status
        dependencies.append(
            {
                "name": _string(item.get("name")),
                "status": status,
                "status_token": get_status_token(config, str(reason)),
                "message": item.get("message"),
                "error_code": item.get("error_code"),
                "checked_at": item.get("checked_at"),
            }
        )

    return {
        "api": {
            "status": api_status,
            "status_token": get_status_token(config, api_status),
            "service": health.get("service"),
            "version": health.get("version"),
            "checked_at": health.get("checked_at"),
        },
        "dependencies": dependencies,
        "metrics": {
            "job_counts": _dict_or_empty(metrics.get("job_counts")),
            "watcher_counts": _dict_or_empty(metrics.get("watcher_counts")),
            "delivery_counts": _dict_or_empty(metrics.get("delivery_counts")),
            "retry_counts": _dict_or_empty(metrics.get("retry_counts")),
            "queue_lag": _dict_or_empty(metrics.get("queue_lag")),
            "stage_durations_seconds": _dict_or_empty(metrics.get("stage_durations_seconds")),
        },
        "refresh_interval_seconds": int(getattr(config, "refresh_interval_seconds", 2)),
        "correlation_id": health.get("correlation_id") or dependency_health.get("correlation_id") or metrics.get("correlation_id"),
    }


def render_health_page(client: Any, config: Mapping[str, Any] | Any) -> None:
    """Render the health page when Streamlit runtime is available."""

    import streamlit as st

    view_model = build_health_view_model(client, config)
    st.header("Health")
    st.metric("API status", view_model["api"]["status"])
    if view_model["dependencies"]:
        st.subheader("Dependencies")
        st.table(view_model["dependencies"])
    st.subheader("Metrics summary")
    st.json(view_model["metrics"])


def _items(value: Any) -> list[JsonDict]:
    if isinstance(value, list):
        return [dict(item) for item in value if isinstance(item, Mapping)]
    return []


def _dict_or_empty(value: Any) -> JsonDict:
    return dict(value) if isinstance(value, Mapping) else {}


def _string(value: Any) -> str:
    return "" if value is None else str(value)


__all__ = ["build_health_view_model", "render_health_page"]
