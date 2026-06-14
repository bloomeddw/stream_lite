"""Streamlit dashboard foundation helpers.

The dashboard package is intentionally API-only: helpers in this package use
FastAPI HTTP endpoints and pure presentation data. They must not import
repository, database, broker, or worker internals.
"""

from .api_client import CommandPollResult, StreamLiteApiClient, StreamLiteApiError, poll_command_until_terminal
from .commands import build_command_status_display, submit_and_track_command
from .main import build_navigation_sections, render_app
from .layout import DashboardLayout, get_layout_profile, ordered_sections, visible_sections
from .theme import DashboardTheme, PresentationConfig, get_status_token, get_theme, load_presentation_config

__all__ = [
    "CommandPollResult",
    "DashboardLayout",
    "DashboardTheme",
    "PresentationConfig",
    "StreamLiteApiClient",
    "StreamLiteApiError",
    "build_command_status_display",
    "build_navigation_sections",
    "get_layout_profile",
    "get_status_token",
    "get_theme",
    "load_presentation_config",
    "ordered_sections",
    "render_app",
    "poll_command_until_terminal",
    "submit_and_track_command",
    "visible_sections",
]
