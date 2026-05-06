"""Centralized dashboard layout helpers for WP11-A."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

JsonDict = dict[str, Any]


@dataclass(frozen=True)
class DashboardLayout:
    """Resolved layout profile for dashboard sections."""

    name: str
    sections: list[JsonDict]
    density: str | None = None
    groups: dict[str, Any] = field(default_factory=dict)


def get_layout_profile(config: Mapping[str, Any] | Any, profile_name: str | None = None) -> DashboardLayout:
    """Return a layout profile from dashboard presentation config with safe fallback."""

    raw = getattr(config, "raw", None) if not isinstance(config, Mapping) else config
    raw = raw if isinstance(raw, Mapping) else {}
    active_name = str(getattr(config, "layout_profile", raw.get("layout_profile", "operator_default")))
    requested = profile_name or active_name
    profile_payload = _lookup_named_payload(raw.get("layout_profiles"), requested, active_name)
    if profile_payload is not None:
        return DashboardLayout(
            name=str(profile_payload.get("layout_profile") or profile_payload.get("name") or requested),
            sections=_normalize_sections(profile_payload.get("layout_sections") or profile_payload.get("sections")),
            density=None if profile_payload.get("density") is None else str(profile_payload.get("density")),
            groups=dict(profile_payload.get("groups", {})) if isinstance(profile_payload.get("groups"), Mapping) else {},
        )

    sections = getattr(config, "layout_sections", None)
    if sections is None:
        sections = raw.get("layout_sections")
    return DashboardLayout(name=active_name, sections=_normalize_sections(sections))


def visible_sections(layout: DashboardLayout, page_name: str) -> list[JsonDict]:
    """Return visible sections for a page; unknown pages return an empty list."""

    return [section for section in _sections_for_page(layout, page_name) if bool(section.get("visible", True))]


def ordered_sections(layout: DashboardLayout, page_name: str) -> list[JsonDict]:
    """Return visible sections for a page sorted by configured order."""

    return sorted(visible_sections(layout, page_name), key=lambda section: (int(section.get("order", 0)), str(section.get("section_id", ""))))


def _sections_for_page(layout: DashboardLayout, page_name: str) -> list[JsonDict]:
    requested = str(page_name)
    sections_with_page = [section for section in layout.sections if _section_page(section) is not None]
    if sections_with_page:
        return [section for section in sections_with_page if _section_page(section) == requested]
    if requested in {"", "default", "dashboard", "overview", layout.name}:
        return list(layout.sections)
    return []


def _section_page(section: Mapping[str, Any]) -> str | None:
    value = section.get("page_name", section.get("page"))
    return None if value is None else str(value)


def _normalize_sections(value: Any) -> list[JsonDict]:
    if not isinstance(value, list):
        return []
    sections: list[JsonDict] = []
    for item in value:
        if isinstance(item, Mapping):
            section = dict(item)
            section.setdefault("visible", True)
            section.setdefault("order", 0)
            sections.append(section)
    return sections


def _lookup_named_payload(value: Any, requested: str, fallback: str) -> Mapping[str, Any] | None:
    if isinstance(value, Mapping):
        selected = value.get(requested) or value.get(fallback)
        return selected if isinstance(selected, Mapping) else None
    if isinstance(value, list):
        by_name = {str(item.get("layout_profile") or item.get("name")): item for item in value if isinstance(item, Mapping)}
        selected = by_name.get(requested) or by_name.get(fallback)
        return selected if isinstance(selected, Mapping) else None
    return None


__all__ = ["DashboardLayout", "get_layout_profile", "ordered_sections", "visible_sections"]
