"""Read-only Streamlit app shell for WP11-B1."""

from __future__ import annotations

from typing import Any, Mapping

from streamlit_app.api_client import StreamLiteApiClient
from streamlit_app.layout import get_layout_profile
from streamlit_app.theme import PresentationConfig, load_presentation_config

_FALLBACK_NAVIGATION = [
    {"page_id": "health", "label": "Health", "order": 10, "visible": True},
    {"page_id": "watchers", "label": "Watchers", "order": 20, "visible": True},
    {"page_id": "jobs", "label": "Jobs", "order": 30, "visible": True},
    {"page_id": "events", "label": "Events", "order": 40, "visible": True},
    {"page_id": "quarantine", "label": "Quarantine", "order": 50, "visible": True},
    {"page_id": "outputs", "label": "Outputs", "order": 60, "visible": True},
    {"page_id": "logs", "label": "Logs", "order": 70, "visible": True},
    {"page_id": "config", "label": "Config", "order": 80, "visible": True},
]
_LABELS = {item["page_id"]: item["label"] for item in _FALLBACK_NAVIGATION}


def build_navigation_sections(config: PresentationConfig | Mapping[str, Any]) -> list[dict[str, Any]]:
    """Build read-only navigation from layout configuration with safe fallbacks."""

    resolved = config if isinstance(config, PresentationConfig) else load_presentation_config(config)
    layout = get_layout_profile(resolved)
    explicitly_hidden: set[str] = set()
    labels = dict(_LABELS)
    for section in layout.sections:
        page_id = str(section.get("page_name") or section.get("page") or section.get("section_id", "")).strip().lower()
        if page_id not in _LABELS:
            continue
        if not bool(section.get("visible", True)):
            explicitly_hidden.add(page_id)
            continue
        if section.get("label"):
            labels[page_id] = str(section["label"])
    return [
        {**fallback, "label": labels[str(fallback["page_id"])]}
        for fallback in _FALLBACK_NAVIGATION
        if str(fallback["page_id"]) not in explicitly_hidden
    ]


def render_app(client: StreamLiteApiClient | None = None) -> None:
    """Render the read-only app shell when Streamlit runtime is available."""

    import streamlit as st

    from streamlit_app.pages.config import render_config_page
    from streamlit_app.pages.events import render_events_page
    from streamlit_app.pages.health import render_health_page
    from streamlit_app.pages.jobs import render_jobs_page
    from streamlit_app.pages.logs import render_logs_page
    from streamlit_app.pages.outputs import render_outputs_page
    from streamlit_app.pages.quarantine import render_quarantine_page
    from streamlit_app.pages.watchers import render_watchers_page

    resolved_client = client or StreamLiteApiClient("http://localhost:8000")
    config = load_presentation_config(resolved_client.get_dashboard_presentation())
    st.set_page_config(page_title="Stream Lite", layout="wide")
    st.title("Stream Lite Command Center")
    navigation = build_navigation_sections(config)
    page_id = st.sidebar.radio("View", [item["page_id"] for item in navigation], format_func=lambda value: _LABELS.get(value, value.title()))
    if page_id == "health":
        render_health_page(resolved_client, config)
    elif page_id == "watchers":
        render_watchers_page(resolved_client, config)
    elif page_id == "jobs":
        render_jobs_page(resolved_client, config)
    elif page_id == "events":
        render_events_page(resolved_client, config)
    elif page_id == "quarantine":
        render_quarantine_page(resolved_client, config)
    elif page_id == "outputs":
        render_outputs_page(resolved_client, config)
    elif page_id == "logs":
        render_logs_page(resolved_client, config)
    else:
        render_config_page(resolved_client, config)


def _fallback_order(page_id: str) -> int:
    for item in _FALLBACK_NAVIGATION:
        if item["page_id"] == page_id:
            return int(item["order"])
    return 1000


__all__ = ["build_navigation_sections", "render_app"]
