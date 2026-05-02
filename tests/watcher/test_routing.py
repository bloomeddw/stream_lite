from __future__ import annotations

from uuid import uuid4

import pytest

from app.watcher.routing import (
    NO_MATCHING_DESTINATION,
    NO_MATCHING_SOURCE,
    RouteTagError,
    build_route_preview,
    match_source_to_destinations,
    normalize_route_tags,
)


def folder(*, source: bool, tags: list[str], enabled: bool = True) -> dict[str, object]:
    field = "source_folder_id" if source else "destination_folder_id"
    return {field: uuid4(), "route_tags": tags, "enabled": enabled}


def test_normalize_route_tags_trims_uppercases_deduplicates_and_rejects_invalid() -> None:
    assert normalize_route_tags([" a ", "A", "client-001", "batch_2"]) == ("A", "CLIENT-001", "BATCH_2")
    assert normalize_route_tags("a; B") == ("A", "B")
    with pytest.raises(RouteTagError):
        normalize_route_tags(["bad tag"])
    with pytest.raises(RouteTagError):
        normalize_route_tags([])


def test_route_matching_supports_one_to_many_many_to_one_and_many_to_many() -> None:
    source_a = folder(source=True, tags=["A", "B"])
    source_b = folder(source=True, tags=["B", "C"])
    dest_a = folder(source=False, tags=["A"])
    dest_b = folder(source=False, tags=["B"])
    dest_c = folder(source=False, tags=["C"])

    assert match_source_to_destinations(source_a, [dest_a, dest_b, dest_c]) == [dest_a, dest_b]
    assert match_source_to_destinations(source_b, [dest_a, dest_b, dest_c]) == [dest_b, dest_c]

    preview = build_route_preview([source_a, source_b], [dest_a, dest_b, dest_c])
    assert preview.status == "green"
    assert len([match for match in preview.matches if match.destination_folder_id is not None]) == 4
    assert preview.unmatched_sources == ()
    assert preview.unmatched_destinations == ()


def test_route_preview_reports_unmatched_source_and_destination_reason_codes() -> None:
    source = folder(source=True, tags=["SOURCE"])
    destination = folder(source=False, tags=["DESTINATION"])

    preview = build_route_preview([source], [destination])

    assert preview.status == "red"
    assert preview.unmatched_sources == (source["source_folder_id"],)
    assert preview.unmatched_destinations == (destination["destination_folder_id"],)
    assert preview.matches[0].unmatched_reason_code == NO_MATCHING_DESTINATION
    assert preview.matches[0].matched_route_tags == ()
    assert preview.unmatched_destination_reason_codes[destination["destination_folder_id"]] == NO_MATCHING_SOURCE
