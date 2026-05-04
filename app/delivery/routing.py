"""Pure delivery routing helpers for WP09-A."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence
from uuid import UUID

from app.watcher.routing import NO_MATCHING_DESTINATION, normalize_route_tags


@dataclass(frozen=True, slots=True)
class DeliveryTarget:
    destination_folder_id: UUID
    destination_container_locator: str
    destination_display_path: str
    destination_route_tags: tuple[str, ...]
    matched_route_tags: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DeliveryRouteResolution:
    targets: tuple[DeliveryTarget, ...]
    unmatched_reason: str | None


def resolve_delivery_targets(
    source_route_tags: Sequence[str],
    watcher_destinations: Sequence[Any],
) -> DeliveryRouteResolution:
    """Resolve every destination sharing at least one normalized route tag."""

    normalized_source_tags = normalize_route_tags(source_route_tags)
    targets: list[DeliveryTarget] = []

    for destination in watcher_destinations:
        destination_tags = normalize_route_tags(_required_value(destination, "route_tags"))
        destination_tag_set = set(destination_tags)
        matched_tags = tuple(tag for tag in normalized_source_tags if tag in destination_tag_set)
        if not matched_tags:
            continue

        targets.append(
            DeliveryTarget(
                destination_folder_id=UUID(
                    str(_required_value(destination, "id", "destination_folder_id"))
                ),
                destination_container_locator=str(
                    _required_value(
                        destination,
                        "path",
                        "destination_container_locator",
                        "normalized_path",
                    )
                ),
                destination_display_path=str(
                    _required_value(
                        destination,
                        "display_path",
                        "destination_display_path",
                    )
                ),
                destination_route_tags=destination_tags,
                matched_route_tags=matched_tags,
            )
        )

    if not targets:
        return DeliveryRouteResolution(
            targets=(),
            unmatched_reason=NO_MATCHING_DESTINATION,
        )

    return DeliveryRouteResolution(
        targets=tuple(targets),
        unmatched_reason=None,
    )


def _required_value(item: Any, *names: str) -> Any:
    for name in names:
        if isinstance(item, dict) and name in item:
            return item[name]
        if hasattr(item, name):
            return getattr(item, name)
    joined_names = ", ".join(names)
    raise ValueError(f"Destination is missing one of: {joined_names}")


__all__ = [
    "DeliveryRouteResolution",
    "DeliveryTarget",
    "resolve_delivery_targets",
]
