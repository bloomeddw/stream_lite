from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.delivery import resolve_delivery_targets
from app.watcher.routing import NO_MATCHING_DESTINATION


@dataclass(frozen=True, slots=True)
class Destination:
    id: UUID
    path: str
    display_path: str
    route_tags: tuple[str, ...]


def test_resolve_delivery_targets_routes_one_source_to_one_destination() -> None:
    resolution = resolve_delivery_targets(
        source_route_tags=("orders", "vip"),
        watcher_destinations=[
            {
                "destination_folder_id": UUID("22222222-2222-4222-8222-222222222222"),
                "destination_container_locator": "/stream-lite-test/destinations/orders",
                "destination_display_path": "/orders",
                "route_tags": ("ORDERS",),
            },
            {
                "destination_folder_id": UUID("33333333-3333-4333-8333-333333333333"),
                "destination_container_locator": "/stream-lite-test/destinations/invoices",
                "destination_display_path": "/invoices",
                "route_tags": ("INVOICES",),
            },
        ],
    )

    assert resolution.unmatched_reason is None
    assert len(resolution.targets) == 1
    assert resolution.targets[0].destination_folder_id == UUID(
        "22222222-2222-4222-8222-222222222222"
    )
    assert (
        resolution.targets[0].destination_container_locator
        == "/stream-lite-test/destinations/orders"
    )
    assert resolution.targets[0].destination_display_path == "/orders"
    assert resolution.targets[0].destination_route_tags == ("ORDERS",)
    assert resolution.targets[0].matched_route_tags == ("ORDERS",)


def test_resolve_delivery_targets_routes_one_source_to_multiple_destinations_in_input_order() -> None:
    resolution = resolve_delivery_targets(
        source_route_tags=("vip", "archive", "orders"),
        watcher_destinations=[
            Destination(
                id=UUID("44444444-4444-4444-8444-444444444444"),
                path="/stream-lite-test/destinations/vip",
                display_path="/vip",
                route_tags=("VIP",),
            ),
            Destination(
                id=UUID("55555555-5555-4555-8555-555555555555"),
                path="/stream-lite-test/destinations/archive",
                display_path="/archive",
                route_tags=("ARCHIVE", "ORDERS"),
            ),
        ],
    )

    assert resolution.unmatched_reason is None
    assert [target.destination_display_path for target in resolution.targets] == [
        "/vip",
        "/archive",
    ]
    assert resolution.targets[0].matched_route_tags == ("VIP",)
    assert resolution.targets[1].matched_route_tags == ("ARCHIVE", "ORDERS")


def test_resolve_delivery_targets_returns_no_matching_destination_when_no_tags_intersect() -> None:
    resolution = resolve_delivery_targets(
        source_route_tags=("orders",),
        watcher_destinations=[
            Destination(
                id=UUID("66666666-6666-4666-8666-666666666666"),
                path="/stream-lite-test/destinations/invoices",
                display_path="/invoices",
                route_tags=("INVOICES",),
            )
        ],
    )

    assert resolution.targets == ()
    assert resolution.unmatched_reason == NO_MATCHING_DESTINATION
