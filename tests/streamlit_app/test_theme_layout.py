from __future__ import annotations

from streamlit_app.layout import get_layout_profile, ordered_sections, visible_sections
from streamlit_app.theme import get_status_token, get_theme, load_presentation_config


def _presentation_payload() -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "theme_name": "default_light",
        "color_tokens": {
            "stable": "#008000",
            "warning": "#ffcc00",
            "faulty": "#cc0000",
            "neutral": "#666666",
            "background": "#ffffff",
            "text": "#111111",
            "accent": "#3366ff",
            "disabled": "#999999",
        },
        "status_dot_tokens": {
            "stable": "stable-dot",
            "warning": "warning-dot",
            "faulty": "faulty-dot",
            "neutral": "neutral-dot",
            "background": "background-dot",
            "text": "text-dot",
            "accent": "accent-dot",
            "disabled": "disabled-dot",
        },
        "themes": {
            "high_contrast": {
                "theme_name": "high_contrast",
                "color_tokens": {
                    "stable": "hc-stable",
                    "warning": "hc-warning",
                    "faulty": "hc-faulty",
                    "neutral": "hc-neutral",
                    "background": "hc-bg",
                    "text": "hc-text",
                    "accent": "hc-accent",
                    "disabled": "hc-disabled",
                },
                "status_dot_tokens": {
                    "stable": "hc-stable-dot",
                    "warning": "hc-warning-dot",
                    "faulty": "hc-faulty-dot",
                    "neutral": "hc-neutral-dot",
                    "background": "hc-bg-dot",
                    "text": "hc-text-dot",
                    "accent": "hc-accent-dot",
                    "disabled": "hc-disabled-dot",
                },
            }
        },
        "layout_profile": "operator_default",
        "layout_sections": [
            {"section_id": "health", "page_name": "overview", "visible": True, "order": 2},
            {"section_id": "jobs", "page_name": "overview", "visible": True, "order": 1},
            {"section_id": "debug", "page_name": "overview", "visible": False, "order": 3},
        ],
        "layout_profiles": {
            "reviewer_demo": {
                "layout_profile": "reviewer_demo",
                "density": "compact",
                "layout_sections": [
                    {"section_id": "demo", "page_name": "overview", "visible": True, "order": 1},
                    {"section_id": "hidden", "page_name": "overview", "visible": False, "order": 2},
                ],
            }
        },
        "refresh_interval_seconds": 2,
        "correlation_id": "22222222-2222-4222-8222-222222222222",
    }


def test_loads_dashboard_presentation_payload_and_status_tokens_map_semantically() -> None:
    config = load_presentation_config(_presentation_payload())

    assert config.refresh_interval_seconds == 2
    assert get_status_token(config, "green") == "stable-dot"
    assert get_status_token(config, "PENDING_CHECK") == "warning-dot"
    assert get_status_token(config, "NO_MATCHING_SOURCE") == "warning-dot"
    assert get_status_token(config, "NO_MATCHING_DESTINATION") == "warning-dot"
    assert get_status_token(config, "EMPTY_SOURCE_IDLE") == "warning-dot"
    assert get_status_token(config, "PARTIAL_ROUTE_PREVIEW") == "warning-dot"
    assert get_status_token(config, "yellow") == "warning-dot"
    assert get_status_token(config, "DESTINATION_NOT_WRITABLE") == "faulty-dot"
    assert get_status_token(config, "SOURCE_TRANSFER_FAILED") == "faulty-dot"
    assert get_status_token(config, "red") == "faulty-dot"


def test_missing_theme_falls_back_to_active_theme() -> None:
    config = load_presentation_config(_presentation_payload())

    assert get_theme(config, "missing_theme").name == "default_light"
    assert get_theme(config, "high_contrast").status_dot_tokens["stable"] == "hc-stable-dot"


def test_missing_layout_profile_falls_back_and_sections_respect_visibility_and_order() -> None:
    config = load_presentation_config(_presentation_payload())

    layout = get_layout_profile(config, "missing_profile")
    assert layout.name == "operator_default"
    assert [section["section_id"] for section in visible_sections(layout, "overview")] == ["health", "jobs"]
    assert [section["section_id"] for section in ordered_sections(layout, "overview")] == ["jobs", "health"]


def test_requested_layout_profile_and_unknown_page() -> None:
    config = load_presentation_config(_presentation_payload())

    layout = get_layout_profile(config, "reviewer_demo")
    assert layout.name == "reviewer_demo"
    assert layout.density == "compact"
    assert [section["section_id"] for section in ordered_sections(layout, "overview")] == ["demo"]
    assert ordered_sections(layout, "unknown") == []
