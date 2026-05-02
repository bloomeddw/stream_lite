"""Pure watcher route-tag normalization and preview helpers for WP-06."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Sequence
from uuid import UUID

from app._schema_types import ROUTE_TAG_PATTERN

ROUTE_POLICY_TAG_MATCH_ALL_DESTINATIONS = "tag_match_all_destinations"
NO_MATCHING_DESTINATION = "NO_MATCHING_DESTINATION"
NO_MATCHING_SOURCE = "NO_MATCHING_SOURCE"


class RouteTagError(ValueError):
    """Raised when a route tag does not satisfy the documented syntax."""

    def __init__(self, tag: str) -> None:
        super().__init__("Route tags must match ^[A-Z0-9_-]{1,32}$.")
        self.tag = tag
        self.error_code = "TAG_INVALID"


@dataclass(frozen=True, slots=True)
class RoutePreviewPair:
    source_folder_id: UUID
    destination_folder_id: UUID | None
    matched_route_tags: tuple[str, ...]
    unmatched_reason_code: str | None = None


@dataclass(frozen=True, slots=True)
class RoutePreviewResult:
    route_policy: str
    matches: tuple[RoutePreviewPair, ...]
    unmatched_sources: tuple[UUID, ...]
    unmatched_destinations: tuple[UUID, ...]
    unmatched_destination_reason_codes: dict[UUID, str]
    status: str


def normalize_route_tags(tags: str | Sequence[str]) -> tuple[str, ...]:
    """Normalize route tags by trimming, uppercasing, validating, and deduplicating."""

    raw_tags: Iterable[str]
    if isinstance(tags, str):
        raw_tags = tags.split(";")
    else:
        raw_tags = tags

    normalized: list[str] = []
    seen: set[str] = set()
    for raw_tag in raw_tags:
        tag = str(raw_tag).strip().upper()
        if not tag or ROUTE_TAG_PATTERN.fullmatch(tag) is None:
            raise RouteTagError(tag)
        if tag in seen:
            continue
        seen.add(tag)
        normalized.append(tag)
    if not normalized:
        raise RouteTagError("")
    return tuple(normalized)


def match_source_to_destinations(source: Any, destinations: Sequence[Any]) -> list[Any]:
    """Return every enabled destination sharing at least one normalized tag with a source."""

    source_tags = set(normalize_route_tags(_route_tags(source)))
    matches: list[Any] = []
    for destination in destinations:
        if not _enabled(destination):
            continue
        destination_tags = set(normalize_route_tags(_route_tags(destination)))
        if source_tags & destination_tags:
            matches.append(destination)
    return matches


def build_route_preview(sources: Sequence[Any], destinations: Sequence[Any]) -> RoutePreviewResult:
    """Build a deterministic route preview without touching persistence or the filesystem."""

    enabled_sources = [source for source in sources if _enabled(source)]
    enabled_destinations = [destination for destination in destinations if _enabled(destination)]
    preview_pairs: list[RoutePreviewPair] = []
    matched_source_ids: set[UUID] = set()
    matched_destination_ids: set[UUID] = set()

    for source in sorted(enabled_sources, key=lambda item: str(_source_id(item))):
        source_tags = set(normalize_route_tags(_route_tags(source)))
        source_id = _source_id(source)
        matched_any = False
        for destination in sorted(enabled_destinations, key=lambda item: str(_destination_id(item))):
            destination_tags = set(normalize_route_tags(_route_tags(destination)))
            matched_tags = tuple(sorted(source_tags & destination_tags))
            if not matched_tags:
                continue
            matched_any = True
            destination_id = _destination_id(destination)
            matched_source_ids.add(source_id)
            matched_destination_ids.add(destination_id)
            preview_pairs.append(
                RoutePreviewPair(
                    source_folder_id=source_id,
                    destination_folder_id=destination_id,
                    matched_route_tags=matched_tags,
                    unmatched_reason_code=None,
                ),
            )
        if not matched_any:
            preview_pairs.append(
                RoutePreviewPair(
                    source_folder_id=source_id,
                    destination_folder_id=None,
                    matched_route_tags=(),
                    unmatched_reason_code=NO_MATCHING_DESTINATION,
                ),
            )

    unmatched_sources = tuple(
        sorted((_source_id(source) for source in enabled_sources if _source_id(source) not in matched_source_ids), key=str),
    )
    unmatched_destinations = tuple(
        sorted(
            (
                _destination_id(destination)
                for destination in enabled_destinations
                if _destination_id(destination) not in matched_destination_ids
            ),
            key=str,
        ),
    )
    unmatched_destination_reason_codes = {destination_id: NO_MATCHING_SOURCE for destination_id in unmatched_destinations}
    status = "red" if not matched_destination_ids else "yellow" if unmatched_sources or unmatched_destinations else "green"
    return RoutePreviewResult(
        route_policy=ROUTE_POLICY_TAG_MATCH_ALL_DESTINATIONS,
        matches=tuple(preview_pairs),
        unmatched_sources=unmatched_sources,
        unmatched_destinations=unmatched_destinations,
        unmatched_destination_reason_codes=unmatched_destination_reason_codes,
        status=status,
    )


def _enabled(item: Any) -> bool:
    return bool(_value(item, "enabled", True))


def _route_tags(item: Any) -> Sequence[str]:
    return _value(item, "route_tags", ())


def _source_id(item: Any) -> UUID:
    return UUID(str(_value(item, "source_folder_id")))


def _destination_id(item: Any) -> UUID:
    return UUID(str(_value(item, "destination_folder_id")))


def _value(item: Any, name: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(name, default)
    return getattr(item, name, default)


__all__ = [
    "NO_MATCHING_DESTINATION",
    "NO_MATCHING_SOURCE",
    "ROUTE_POLICY_TAG_MATCH_ALL_DESTINATIONS",
    "RoutePreviewPair",
    "RoutePreviewResult",
    "RouteTagError",
    "build_route_preview",
    "match_source_to_destinations",
    "normalize_route_tags",
]
