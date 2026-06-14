"""Read-only dashboard configuration page helpers."""

from __future__ import annotations

from typing import Any, Mapping

from streamlit_app.layout import get_layout_profile, ordered_sections
from streamlit_app.theme import PresentationConfig, get_theme, load_presentation_config

JsonDict = dict[str, Any]
_FALLBACK_PAGES = ("health", "jobs", "events", "logs", "config")


def build_config_view_model(config: PresentationConfig | Mapping[str, Any]) -> JsonDict:
    """Build a read-only view of dashboard presentation configuration."""

    resolved = config if isinstance(config, PresentationConfig) else load_presentation_config(config)
    theme = get_theme(resolved)
    layout = get_layout_profile(resolved)
    expected_fields = ("schema_version", "theme_name", "layout_profile", "refresh_interval_seconds")
    missing_fields = [field for field in expected_fields if getattr(resolved, field, None) in (None, "")]
    visible_by_page = {page: ordered_sections(layout, page) for page in _FALLBACK_PAGES}
    return {
        "schema_version": resolved.schema_version,
        "active_theme": theme.name,
        "active_layout_profile": layout.name,
        "refresh_interval_seconds": resolved.refresh_interval_seconds,
        "color_tokens": dict(theme.color_tokens),
        "status_dot_tokens": dict(theme.status_dot_tokens),
        "layout_sections": list(layout.sections),
        "visible_sections_by_page": visible_by_page,
        "warnings": [f"Missing expected presentation field: {field}" for field in missing_fields],
        "correlation_id": resolved.correlation_id,
    }


def render_config_page(client: Any, config: PresentationConfig | Mapping[str, Any]) -> None:
    """Render the config page when Streamlit runtime is available."""

    import streamlit as st

    view_model = build_config_view_model(config)
    st.header("Configuration")
    for warning in view_model["warnings"]:
        st.warning(warning)
    st.write("Active theme", view_model["active_theme"])
    st.write("Active layout", view_model["active_layout_profile"])
    st.write("Refresh interval", view_model["refresh_interval_seconds"])
    st.subheader("Color tokens")
    st.json(view_model["color_tokens"])
    st.subheader("Visible sections")
    st.json(view_model["visible_sections_by_page"])


__all__ = ["build_config_view_model", "render_config_page"]
