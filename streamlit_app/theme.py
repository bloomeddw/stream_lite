"""Dashboard presentation theme helpers for WP11-A."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

JsonDict = dict[str, Any]

_REQUIRED_COLOR_TOKENS = {
    "stable": "#2e7d32",
    "warning": "#f9a825",
    "faulty": "#c62828",
    "neutral": "#607d8b",
    "background": "#ffffff",
    "text": "#111827",
    "accent": "#2563eb",
    "disabled": "#9ca3af",
}
_STATUS_ALIASES = {
    "green": "stable",
    "healthy": "stable",
    "ok": "stable",
    "ready": "stable",
    "stable": "stable",
    "yellow": "warning",
    "idle": "warning",
    "pending": "warning",
    "pending_check": "warning",
    "empty_source_idle": "warning",
    "no_matching_source": "warning",
    "no_matching_destination": "warning",
    "partial_route_preview": "warning",
    "warning": "warning",
    "red": "faulty",
    "error": "faulty",
    "failed": "faulty",
    "faulty": "faulty",
    "not_found": "faulty",
    "not_readable": "faulty",
    "not_writable": "faulty",
    "not_allowlisted": "faulty",
    "path_not_allowlisted": "faulty",
    "path_policy_violation": "faulty",
    "source_transfer_failed": "faulty",
    "destination_not_found": "faulty",
    "destination_not_writable": "faulty",
    "destination_not_allowlisted": "faulty",
    "neutral": "neutral",
    "unknown": "neutral",
    "disabled": "disabled",
}


@dataclass(frozen=True)
class DashboardTheme:
    """Resolved semantic theme tokens for the dashboard."""

    name: str
    color_tokens: dict[str, str]
    status_dot_tokens: dict[str, str]


@dataclass(frozen=True)
class PresentationConfig:
    """Normalized dashboard presentation configuration."""

    schema_version: str
    theme_name: str
    color_tokens: dict[str, str]
    status_dot_tokens: dict[str, str]
    layout_profile: str
    layout_sections: list[JsonDict]
    refresh_interval_seconds: int
    correlation_id: str | None
    raw: JsonDict = field(default_factory=dict)


def load_presentation_config(payload: Mapping[str, Any]) -> PresentationConfig:
    """Normalize the API dashboard-presentation payload for Streamlit helpers."""

    raw = dict(payload)
    color_tokens = _merge_required_tokens(_string_dict(raw.get("color_tokens")))
    status_tokens = _merge_required_tokens(_string_dict(raw.get("status_dot_tokens")))
    if not raw.get("status_dot_tokens"):
        status_tokens = dict(color_tokens)

    refresh_interval = raw.get("refresh_interval_seconds", 2)
    try:
        refresh_interval_seconds = int(refresh_interval)
    except (TypeError, ValueError):
        refresh_interval_seconds = 2
    refresh_interval_seconds = min(60, max(1, refresh_interval_seconds))

    sections = raw.get("layout_sections")
    layout_sections = [dict(section) for section in sections] if isinstance(sections, list) else []

    return PresentationConfig(
        schema_version=str(raw.get("schema_version", "1.0.0")),
        theme_name=str(raw.get("theme_name", "default_light")),
        color_tokens=color_tokens,
        status_dot_tokens=status_tokens,
        layout_profile=str(raw.get("layout_profile", "operator_default")),
        layout_sections=layout_sections,
        refresh_interval_seconds=refresh_interval_seconds,
        correlation_id=None if raw.get("correlation_id") is None else str(raw.get("correlation_id")),
        raw=raw,
    )


def get_theme(config: PresentationConfig | Mapping[str, Any], theme_name: str | None = None) -> DashboardTheme:
    """Return the requested theme, falling back to the active/default API theme."""

    resolved = config if isinstance(config, PresentationConfig) else load_presentation_config(config)
    requested = theme_name or resolved.theme_name
    theme_payload = _lookup_named_payload(resolved.raw.get("themes"), requested, resolved.theme_name)
    if theme_payload is not None:
        color_tokens = _merge_required_tokens(_string_dict(theme_payload.get("color_tokens")))
        status_tokens = _merge_required_tokens(_string_dict(theme_payload.get("status_dot_tokens")))
        if not theme_payload.get("status_dot_tokens"):
            status_tokens = dict(color_tokens)
        return DashboardTheme(name=str(theme_payload.get("theme_name", requested)), color_tokens=color_tokens, status_dot_tokens=status_tokens)

    return DashboardTheme(
        name=resolved.theme_name,
        color_tokens=dict(resolved.color_tokens),
        status_dot_tokens=dict(resolved.status_dot_tokens),
    )


def get_status_token(config: PresentationConfig | DashboardTheme | Mapping[str, Any], health_status: str) -> str:
    """Return the semantic status color token without changing health meaning."""

    if isinstance(config, DashboardTheme):
        theme = config
    else:
        theme = get_theme(config)
    semantic = _STATUS_ALIASES.get(str(health_status).strip().lower(), "neutral")
    return theme.status_dot_tokens.get(semantic) or theme.color_tokens.get(semantic) or _REQUIRED_COLOR_TOKENS[semantic]


def _merge_required_tokens(tokens: Mapping[str, str]) -> dict[str, str]:
    merged = dict(_REQUIRED_COLOR_TOKENS)
    merged.update({key: str(value) for key, value in tokens.items() if value is not None})
    return merged


def _string_dict(value: Any) -> dict[str, str]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): str(item) for key, item in value.items() if item is not None}


def _lookup_named_payload(value: Any, requested: str, fallback: str) -> Mapping[str, Any] | None:
    if isinstance(value, Mapping):
        selected = value.get(requested) or value.get(fallback)
        return selected if isinstance(selected, Mapping) else None
    if isinstance(value, list):
        by_name = {str(item.get("theme_name") or item.get("name")): item for item in value if isinstance(item, Mapping)}
        selected = by_name.get(requested) or by_name.get(fallback)
        return selected if isinstance(selected, Mapping) else None
    return None


__all__ = ["DashboardTheme", "PresentationConfig", "get_status_token", "get_theme", "load_presentation_config"]
