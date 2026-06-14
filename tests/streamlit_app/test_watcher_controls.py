from __future__ import annotations

from pathlib import Path

import pytest

from streamlit_app.api_client import StreamLiteApiError
from streamlit_app.pages.watchers import (
    build_folder_browse_view_model,
    build_route_preview_view_model,
    build_route_tagged_folder_spec,
    normalize_route_tags_text,
    submit_watcher_lifecycle_command,
    validate_folder_input,
)
from streamlit_app.theme import load_presentation_config


def _config():
    return load_presentation_config(
        {
            "schema_version": "1.0.0",
            "theme_name": "default_light",
            "color_tokens": {
                "stable": "stable-token",
                "warning": "warning-token",
                "faulty": "faulty-token",
                "neutral": "neutral-token",
                "background": "background-token",
                "text": "text-token",
                "accent": "accent-token",
                "disabled": "disabled-token",
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
            "layout_profile": "operator_default",
            "layout_sections": [],
            "refresh_interval_seconds": 1,
            "correlation_id": "33333333-3333-4333-8333-333333333333",
        }
    )


class _WatcherClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []
        self.validation_status = "green"
        self.raise_validation = False
        self.raise_browse = False
        self.command_statuses = ["succeeded"]

    def validate_path(self, payload):
        self.calls.append(("validate_path", payload))
        if self.raise_validation:
            raise StreamLiteApiError(
                status_code=422,
                error_code="PATH_NOT_ALLOWLISTED",
                message="Path is outside the allowlist.",
                payload={"correlation_id": "33333333-3333-4333-8333-333333333333"},
            )
        return {
            "purpose": payload["purpose"],
            "path": payload["path"],
            "normalized_path": payload["path"],
            "display_path": "/stream-lite/source",
            "status": self.validation_status,
            "reason_code": "PENDING_CHECK" if self.validation_status == "yellow" else "OK",
            "message": "Validated.",
            "correlation_id": "33333333-3333-4333-8333-333333333333",
        }

    def browse_files(self, params):
        self.calls.append(("browse_files", params))
        if self.raise_browse:
            raise StreamLiteApiError(
                status_code=503,
                error_code="PATH_ROOT_UNAVAILABLE",
                message="Root is unavailable.",
                payload={"correlation_id": "33333333-3333-4333-8333-333333333333"},
            )
        return {
            "purpose": params["purpose"],
            "root": params.get("root") or "/stream-lite/source",
            "items": [
                {
                    "name": "orders",
                    "display_path": "/stream-lite/source/orders",
                    "is_directory": True,
                    "is_selectable": True,
                    "reason_code": None,
                }
            ],
            "correlation_id": "33333333-3333-4333-8333-333333333333",
        }

    def preview_routes(self, watcher_id, payload):
        self.calls.append(("preview_routes", (watcher_id, payload)))
        return {
            "route_policy": "tag_match_all_destinations",
            "source_matches": [
                {
                    "source_folder_id": "11111111-1111-4111-8111-111111111111",
                    "matched_destination_ids": ["22222222-2222-4222-8222-222222222222"],
                }
            ],
            "unmatched_sources": ["33333333-3333-4333-8333-333333333333"],
            "unmatched_destinations": ["44444444-4444-4444-8444-444444444444"],
            "status": "yellow",
            "correlation_id": "33333333-3333-4333-8333-333333333333",
        }

    def watcher_command(self, watcher_id, action, payload, *, idempotency_key=None):
        self.calls.append(("watcher_command", (watcher_id, action, payload, idempotency_key)))
        return {
            "status": "accepted",
            "command_id": "55555555-5555-4555-8555-555555555555",
            "target_resource_type": "watcher",
            "target_resource_id": watcher_id,
            "accepted_at": "2026-05-06T12:00:00Z",
            "correlation_id": "33333333-3333-4333-8333-333333333333",
        }

    def get_command_status(self, command_id):
        status = self.command_statuses.pop(0)
        return {
            "command_id": command_id,
            "status": status,
            "target_resource_type": "watcher",
            "target_resource_id": "11111111-1111-4111-8111-111111111111",
            "result": {"locator": "/stream-lite/watchers/11111111-1111-4111-8111-111111111111"} if status == "succeeded" else None,
            "error": None,
            "correlation_id": "33333333-3333-4333-8333-333333333333",
        }


def test_normalize_route_tags_text_deduplicates_and_rejects_invalid_values() -> None:
    assert normalize_route_tags_text("orders; finance ;ORDERS") == ["ORDERS", "FINANCE"]

    with pytest.raises(ValueError, match="must not be empty"):
        normalize_route_tags_text("orders; ;finance")
    with pytest.raises(ValueError, match="must match"):
        normalize_route_tags_text("orders;bad tag")


def test_build_route_tagged_folder_spec_matches_api_shape() -> None:
    spec = build_route_tagged_folder_spec(
        folder_id="11111111-1111-4111-8111-111111111111",
        display_path="/stream-lite/source",
        route_tags_text="orders;finance",
        health_status="green",
        reason_code=None,
    )

    assert spec == {
        "folder_id": "11111111-1111-4111-8111-111111111111",
        "display_path": "/stream-lite/source",
        "route_tags": ["ORDERS", "FINANCE"],
        "route_tags_text": "orders;finance",
        "health_status": "green",
        "reason_code": None,
    }


def test_validate_folder_input_maps_status_tokens_and_api_errors() -> None:
    client = _WatcherClient()
    config = _config()

    green = validate_folder_input(client, config, purpose="source", path="/mnt/source")
    assert green["status_token"] == "stable-dot"

    client.validation_status = "yellow"
    yellow = validate_folder_input(client, config, purpose="source", path="/mnt/source")
    assert yellow["status_token"] == "warning-dot"

    client.validation_status = "red"
    red = validate_folder_input(client, config, purpose="source", path="/mnt/source")
    assert red["status_token"] == "faulty-dot"

    client.raise_validation = True
    error = validate_folder_input(client, config, purpose="source", path="/mnt/source")
    assert error["status"] == "red"
    assert error["reason_code"] == "PATH_NOT_ALLOWLISTED"
    assert error["status_token"] == "faulty-dot"


def test_folder_browse_omits_root_when_absent_and_maps_display_paths() -> None:
    client = _WatcherClient()
    config = _config()

    rootless = build_folder_browse_view_model(client, config, purpose="source")
    assert client.calls[-1] == ("browse_files", {"purpose": "source"})
    assert rootless["items"][0]["display_path"] == "/stream-lite/source/orders"

    build_folder_browse_view_model(client, config, purpose="source", root="/stream-lite/source")
    assert client.calls[-1] == ("browse_files", {"purpose": "source", "root": "/stream-lite/source"})

    client.raise_browse = True
    error = build_folder_browse_view_model(client, config, purpose="source")
    assert error["items"] == []
    assert error["error_code"] == "PATH_ROOT_UNAVAILABLE"
    assert error["status_token"] == "faulty-dot"


def test_route_preview_maps_ids_to_source_destination_rows() -> None:
    client = _WatcherClient()
    config = _config()
    sources = [
        {
            "folder_id": "11111111-1111-4111-8111-111111111111",
            "display_path": "/stream-lite/source/a",
            "route_tags": ["ORDERS", "FINANCE"],
            "route_tags_text": "ORDERS;FINANCE",
            "health_status": "green",
            "reason_code": None,
        },
        {
            "folder_id": "33333333-3333-4333-8333-333333333333",
            "display_path": "/stream-lite/source/b",
            "route_tags": ["HR"],
            "route_tags_text": "HR",
            "health_status": "green",
            "reason_code": None,
        },
    ]
    destinations = [
        {
            "folder_id": "22222222-2222-4222-8222-222222222222",
            "display_path": "/stream-lite/destination/a",
            "route_tags": ["ORDERS"],
            "route_tags_text": "ORDERS",
            "health_status": "green",
            "reason_code": None,
        },
        {
            "folder_id": "44444444-4444-4444-8444-444444444444",
            "display_path": "/stream-lite/destination/b",
            "route_tags": ["LEGAL"],
            "route_tags_text": "LEGAL",
            "health_status": "green",
            "reason_code": None,
        },
    ]

    preview = build_route_preview_view_model(
        client,
        config,
        watcher_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        sources=sources,
        destinations=destinations,
    )

    assert preview["status"] == "yellow"
    assert preview["can_enable"] is False
    assert preview["source_rows"][0]["matched_destinations"][0]["display_path"] == "/stream-lite/destination/a"
    assert preview["source_rows"][0]["matched_destinations"][0]["matched_route_tags"] == ["ORDERS"]
    assert preview["source_rows"][1]["reason_code"] == "NO_MATCHING_DESTINATION"
    assert preview["unmatched_destinations"][0]["reason_code"] == "NO_MATCHING_SOURCE"


def test_submit_watcher_lifecycle_command_uses_action_and_payload() -> None:
    client = _WatcherClient()
    card = submit_watcher_lifecycle_command(
        client,
        _config(),
        watcher_id="11111111-1111-4111-8111-111111111111",
        action="start",
        requested_by=" operator ",
        reason=" route checked ",
        idempotency_key="watcher-key",
        sleep_fn=lambda _: None,
    )

    assert client.calls[0] == (
        "watcher_command",
        (
            "11111111-1111-4111-8111-111111111111",
            "start",
            {"requested_by": "operator", "reason": "route checked"},
            "watcher-key",
        ),
    )
    assert card["accepted"] is True
    assert card["terminal_status"] == "succeeded"


def test_streamlit_files_remain_api_only() -> None:
    forbidden = (
        "app.repositories",
        "app.db",
        "sqlalchemy",
        "redis",
        "app.processing",
        "app.delivery.service",
        "app.retry.scheduler",
    )
    for path in Path("streamlit_app").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for forbidden_text in forbidden:
            assert forbidden_text not in text, f"{path} imports or references {forbidden_text}"
