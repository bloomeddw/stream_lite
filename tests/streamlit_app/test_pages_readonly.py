from __future__ import annotations

import importlib
from pathlib import Path

from streamlit_app.main import build_navigation_sections
from streamlit_app.pages.config import build_config_view_model
from streamlit_app.pages.events import build_events_view_model
from streamlit_app.pages.health import build_health_view_model
from streamlit_app.pages.jobs import build_jobs_view_model
from streamlit_app.pages.logs import build_logs_view_model
from streamlit_app.pages.outputs import build_outputs_view_model
from streamlit_app.pages.quarantine import build_quarantine_view_model
from streamlit_app.pages.watchers import build_watcher_detail_view_model, build_watchers_view_model
from streamlit_app.theme import load_presentation_config


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []
        self.jobs_payload = {
            "items": [
                {
                    "job_id": "11111111-1111-4111-8111-111111111111",
                    "watcher_id": "22222222-2222-4222-8222-222222222222",
                    "state": "FAILED",
                    "source_display_path": "/stream-lite/source/orders.csv",
                    "created_at": "2026-05-06T12:00:00Z",
                    "updated_at": "2026-05-06T12:01:00Z",
                    "latest_error_code": "PROCESSING_INPUT_INVALID",
                }
            ],
            "limit": 50,
            "offset": 0,
            "total": 1,
            "correlation_id": "33333333-3333-4333-8333-333333333333",
        }
        self.events_payload = {
            "items": [
                {
                    "event_id": "44444444-4444-4444-8444-444444444444",
                    "event_type": "processing.failed",
                    "stream_name": "stream_lite.lifecycle",
                    "producer": "processor",
                    "job_id": "11111111-1111-4111-8111-111111111111",
                    "watcher_id": None,
                    "occurred_at": "2026-05-06T12:01:00Z",
                    "schema_version": "1.0.0",
                    "correlation_id": "33333333-3333-4333-8333-333333333333",
                }
            ],
            "limit": 50,
            "offset": 0,
            "total": 1,
            "correlation_id": "33333333-3333-4333-8333-333333333333",
        }
        self.logs_payload = {
            "items": [
                {
                    "timestamp": "2026-05-06T12:01:00Z",
                    "level": "ERROR",
                    "service": "processor",
                    "component": "processing.worker",
                    "event": "processing.failed",
                    "message": "Processing failed with operator-safe error.",
                    "correlation_id": "33333333-3333-4333-8333-333333333333",
                    "job_id": "11111111-1111-4111-8111-111111111111",
                    "file_id": None,
                    "error_code": "PROCESSING_INPUT_INVALID",
                    "duration_ms": 15,
                }
            ],
            "limit": 50,
            "offset": 0,
            "total": 1,
            "correlation_id": "33333333-3333-4333-8333-333333333333",
        }
        self.watchers_payload = {
            "items": [
                {
                    "watcher_id": "22222222-2222-4222-8222-222222222222",
                    "name": "orders",
                    "lifecycle_state": "CREATED",
                    "operational_status": "green",
                    "source_count": 1,
                    "destination_count": 1,
                    "updated_at": "2026-05-06T12:00:00Z",
                }
            ],
            "limit": 50,
            "offset": 0,
            "total": 1,
            "correlation_id": "33333333-3333-4333-8333-333333333333",
        }
        self.watcher_detail_payload = {
            "watcher_id": "22222222-2222-4222-8222-222222222222",
            "name": "orders",
            "lifecycle_state": "CREATED",
            "operational_status": "green",
            "sources": [
                {
                    "folder_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                    "display_path": "/stream-lite/source",
                    "route_tags": ["ORDERS"],
                    "route_tags_text": "ORDERS",
                    "health_status": "yellow",
                    "reason_code": "PENDING_CHECK",
                }
            ],
            "destinations": [
                {
                    "folder_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
                    "display_path": "/stream-lite/destination",
                    "route_tags": ["ORDERS"],
                    "route_tags_text": "ORDERS",
                    "health_status": "green",
                    "reason_code": None,
                }
            ],
            "route_policy": "tag_match_all_destinations",
            "route_preview": {
                "status": "green",
                "matched_destination_count": 1,
                "unmatched_source_count": 0,
                "unmatched_destination_count": 0,
                "generated_at": "2026-05-06T12:00:00Z",
            },
            "created_at": "2026-05-06T12:00:00Z",
            "updated_at": "2026-05-06T12:00:00Z",
            "correlation_id": "33333333-3333-4333-8333-333333333333",
        }
        self.job_detail_payload = {
            "job_id": "11111111-1111-4111-8111-111111111111",
            "watcher_id": "22222222-2222-4222-8222-222222222222",
            "state": "FAILED",
            "source": {
                "file_id": "44444444-4444-4444-8444-444444444444",
                "display_path": "/stream-lite/source/orders.csv",
                "source_folder_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                "size_bytes": 1024,
                "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            },
            "destinations": [
                {
                    "destination_folder_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
                    "display_path": "/stream-lite/destination",
                    "route_tags": ["ORDERS"],
                    "matched_tags": ["ORDERS"],
                    "status": "failed",
                    "reason_code": "DESTINATION_TEMPORARILY_UNAVAILABLE",
                }
            ],
            "attempt_summary": {
                "validation_attempts": 1,
                "processing_attempts": 1,
                "delivery_attempts": 2,
                "retry_attempts": 1,
                "last_attempt_at": "2026-05-06T12:02:00Z",
            },
            "latest_error": {
                "error_code": "DESTINATION_TEMPORARILY_UNAVAILABLE",
                "message": "Destination is temporarily unavailable.",
                "field": None,
                "resource_id": "11111111-1111-4111-8111-111111111111",
                "current_state": "FAILED",
                "correlation_id": "33333333-3333-4333-8333-333333333333",
            },
            "created_at": "2026-05-06T12:00:00Z",
            "updated_at": "2026-05-06T12:02:00Z",
            "correlation_id": "33333333-3333-4333-8333-333333333333",
        }
        self.job_history_payload = {
            "job_id": "11111111-1111-4111-8111-111111111111",
            "history": [
                {
                    "from_state": "DELIVERING",
                    "to_state": "FAILED",
                    "actor_service": "delivery",
                    "reason_code": "DESTINATION_TEMPORARILY_UNAVAILABLE",
                    "occurred_at": "2026-05-06T12:02:00Z",
                    "event_id": "55555555-5555-4555-8555-555555555555",
                }
            ],
            "correlation_id": "33333333-3333-4333-8333-333333333333",
        }

    def get_health(self):
        self.calls.append(("get_health", None))
        return {
            "status": "ready",
            "service": "stream_lite_api",
            "version": "0.1.0",
            "checked_at": "2026-05-06T12:00:00Z",
            "correlation_id": "33333333-3333-4333-8333-333333333333",
        }

    def get_dependency_health(self):
        self.calls.append(("get_dependency_health", None))
        return {
            "status": "not_ready",
            "dependencies": [
                {
                    "name": "postgres",
                    "status": "ready",
                    "checked_at": "2026-05-06T12:00:00Z",
                    "message": None,
                    "error_code": None,
                },
                {
                    "name": "redis_streams",
                    "status": "degraded",
                    "checked_at": "2026-05-06T12:00:00Z",
                    "message": "Broker lag is elevated.",
                    "error_code": "BROKER_UNAVAILABLE",
                },
            ],
            "checked_at": "2026-05-06T12:00:00Z",
            "correlation_id": "33333333-3333-4333-8333-333333333333",
        }

    def get_metrics_summary(self):
        self.calls.append(("get_metrics_summary", None))
        return {
            "job_counts": {"FAILED": 1},
            "stage_durations_seconds": {},
            "queue_lag": {},
            "retry_counts": {},
            "delivery_counts": {},
            "watcher_counts": {"active": 1},
            "correlation_id": "33333333-3333-4333-8333-333333333333",
        }

    def list_jobs(self, params=None):
        self.calls.append(("list_jobs", params))
        return self.jobs_payload

    def get_job(self, job_id):
        self.calls.append(("get_job", job_id))
        return self.job_detail_payload

    def get_job_history(self, job_id):
        self.calls.append(("get_job_history", job_id))
        return self.job_history_payload

    def list_watchers(self, params=None):
        self.calls.append(("list_watchers", params))
        return self.watchers_payload

    def get_watcher(self, watcher_id):
        self.calls.append(("get_watcher", watcher_id))
        return self.watcher_detail_payload

    def list_events(self, params=None):
        self.calls.append(("list_events", params))
        return self.events_payload

    def list_logs(self, params=None):
        self.calls.append(("list_logs", params))
        return self.logs_payload


def presentation_payload() -> dict[str, object]:
    return {
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
        "layout_sections": [
            {"section_id": "jobs", "page_name": "jobs", "visible": True, "order": 1},
            {"section_id": "health", "page_name": "health", "visible": True, "order": 2},
            {"section_id": "hidden", "page_name": "debug", "visible": False, "order": 3},
        ],
        "refresh_interval_seconds": 2,
        "correlation_id": "33333333-3333-4333-8333-333333333333",
    }


def test_page_modules_do_not_import_direct_persistence_or_worker_internals() -> None:
    forbidden = (
        "app.repositories",
        "app.db",
        "sqlalchemy",
        "redis",
        "app.processing",
        "app.delivery.service",
        "app.retry.scheduler",
    )
    for path in [Path("streamlit_app/main.py"), *Path("streamlit_app/pages").glob("*.py")]:
        text = path.read_text(encoding="utf-8")
        for forbidden_text in forbidden:
            assert forbidden_text not in text, f"{path} imports or references {forbidden_text}"


def test_page_imports_do_not_require_fastapi_or_database_session() -> None:
    modules = [
        "streamlit_app.main",
        "streamlit_app.pages.health",
        "streamlit_app.pages.watchers",
        "streamlit_app.pages.jobs",
        "streamlit_app.pages.events",
        "streamlit_app.pages.quarantine",
        "streamlit_app.pages.outputs",
        "streamlit_app.pages.logs",
        "streamlit_app.pages.config",
    ]
    for module in modules:
        assert importlib.import_module(module)


def test_main_navigation_includes_required_readonly_pages() -> None:
    navigation = build_navigation_sections(load_presentation_config(presentation_payload()))

    assert [item["page_id"] for item in navigation] == ["health", "watchers", "jobs", "events", "quarantine", "outputs", "logs", "config"]
    assert {item["label"] for item in navigation} == {"Health", "Watchers", "Jobs", "Events", "Quarantine", "Outputs", "Logs", "Config"}


def test_health_view_model_calls_health_dependencies_metrics_and_maps_tokens() -> None:
    client = FakeClient()
    config = load_presentation_config(presentation_payload())

    view_model = build_health_view_model(client, config)

    assert [name for name, _ in client.calls] == ["get_health", "get_dependency_health", "get_metrics_summary"]
    assert view_model["api"]["status"] == "ready"
    assert view_model["api"]["status_token"] == "stable-dot"
    assert view_model["dependencies"][0]["status_token"] == "stable-dot"
    assert view_model["dependencies"][1]["status_token"] == "faulty-dot"
    assert view_model["metrics"]["job_counts"] == {"FAILED": 1}
    assert view_model["refresh_interval_seconds"] == 2


def test_jobs_view_model_handles_populated_and_empty_lists() -> None:
    client = FakeClient()
    config = load_presentation_config(presentation_payload())

    populated = build_jobs_view_model(client, config, params={"state": "FAILED"})
    assert populated["rows"][0]["source_display_path"] == "/stream-lite/source/orders.csv"
    assert populated["rows"][0]["latest_error_code"] == "PROCESSING_INPUT_INVALID"
    assert populated["empty_message"] is None

    client.jobs_payload = {"items": [], "limit": 50, "offset": 0, "total": 0, "correlation_id": "33333333-3333-4333-8333-333333333333"}
    empty = build_jobs_view_model(client, config)
    assert empty["rows"] == []
    assert empty["empty_message"] == "No jobs found."


def test_watcher_view_models_map_status_tokens_and_preview_counts() -> None:
    client = FakeClient()
    config = load_presentation_config(presentation_payload())

    list_view = build_watchers_view_model(client, config)
    assert client.calls[-1] == ("list_watchers", None)
    assert list_view["rows"][0]["status_token"] == "stable-dot"
    assert list_view["empty_message"] is None

    detail = build_watcher_detail_view_model(client, config, "22222222-2222-4222-8222-222222222222")
    assert client.calls[-1] == ("get_watcher", "22222222-2222-4222-8222-222222222222")
    assert detail["sources"][0]["status_token"] == "warning-dot"
    assert detail["destinations"][0]["status_token"] == "stable-dot"
    assert detail["route_preview"]["matched_destination_count"] == 1
    assert detail["can_start_readonly"] is True


def test_job_detail_view_model_maps_attempts_destinations_error_and_history() -> None:
    client = FakeClient()
    config = load_presentation_config(presentation_payload())

    from streamlit_app.pages.jobs import build_job_detail_view_model

    detail = build_job_detail_view_model(client, config, "11111111-1111-4111-8111-111111111111")

    assert [name for name, _ in client.calls[-2:]] == ["get_job", "get_job_history"]
    assert detail["attempt_summary"]["delivery_attempts"] == 2
    assert detail["destinations"][0]["status_token"] == "faulty-dot"
    assert detail["latest_error"]["error_code"] == "DESTINATION_TEMPORARILY_UNAVAILABLE"
    assert detail["history"][0]["to_state"] == "FAILED"


def test_quarantine_view_model_combines_invalid_and_quarantined_rows() -> None:
    client = FakeClient()
    config = load_presentation_config(presentation_payload())

    view_model = build_quarantine_view_model(client, config)

    assert client.calls[-2:] == [("list_jobs", {"state": "INVALID"}), ("list_jobs", {"state": "QUARANTINED"})]
    assert view_model["rows"][0]["bucket"] == "validation_failure"

    client.jobs_payload = {"items": [], "limit": 50, "offset": 0, "total": 0, "correlation_id": "33333333-3333-4333-8333-333333333333"}
    empty = build_quarantine_view_model(client, config)
    assert empty["rows"] == []
    assert empty["empty_message"] == "No validation failures or quarantined jobs found."


def test_outputs_view_model_combines_delivered_output_rows() -> None:
    client = FakeClient()
    config = load_presentation_config(presentation_payload())

    view_model = build_outputs_view_model(client, config)

    assert client.calls[-3:] == [
        ("list_jobs", {"state": "DELIVERED"}),
        ("list_jobs", {"state": "COMPLETED"}),
        ("list_jobs", {"state": "COMPLETED_WITH_DELIVERY_ERRORS"}),
    ]
    assert view_model["rows"][0]["job_id"] == "11111111-1111-4111-8111-111111111111"

    client.jobs_payload = {"items": [], "limit": 50, "offset": 0, "total": 0, "correlation_id": "33333333-3333-4333-8333-333333333333"}
    empty = build_outputs_view_model(client, config)
    assert empty["rows"] == []
    assert empty["empty_message"] == "No delivered outputs found."


def test_events_view_model_handles_populated_and_empty_lists() -> None:
    client = FakeClient()
    config = load_presentation_config(presentation_payload())

    populated = build_events_view_model(client, config)
    assert populated["rows"][0]["event_type"] == "processing.failed"
    assert populated["rows"][0]["producer"] == "processor"
    assert populated["empty_message"] is None

    client.events_payload = {"items": [], "limit": 50, "offset": 0, "total": 0, "correlation_id": "33333333-3333-4333-8333-333333333333"}
    empty = build_events_view_model(client, config)
    assert empty["rows"] == []
    assert empty["empty_message"] == "No events found."


def test_logs_view_model_handles_populated_and_empty_lists() -> None:
    client = FakeClient()
    config = load_presentation_config(presentation_payload())

    populated = build_logs_view_model(client, config)
    assert populated["rows"][0]["event"] == "processing.failed"
    assert populated["rows"][0]["message"] == "Processing failed with operator-safe error."
    assert populated["empty_message"] is None

    client.logs_payload = {"items": [], "limit": 50, "offset": 0, "total": 0, "correlation_id": "33333333-3333-4333-8333-333333333333"}
    empty = build_logs_view_model(client, config)
    assert empty["rows"] == []
    assert empty["empty_message"] == "No operational logs found."


def test_config_view_model_exposes_active_presentation_values() -> None:
    config = load_presentation_config(presentation_payload())

    view_model = build_config_view_model(config)

    assert view_model["active_theme"] == "default_light"
    assert view_model["active_layout_profile"] == "operator_default"
    assert view_model["refresh_interval_seconds"] == 2
    assert view_model["status_dot_tokens"]["stable"] == "stable-dot"
    assert "jobs" in view_model["visible_sections_by_page"]

def test_main_navigation_respects_explicit_hidden_known_page() -> None:
    payload = presentation_payload()
    payload["layout_sections"] = [
        {"section_id": "logs", "page_name": "logs", "visible": False, "order": 1},
    ]

    navigation = build_navigation_sections(load_presentation_config(payload))

    assert "logs" not in {item["page_id"] for item in navigation}
    assert {"health", "watchers", "jobs", "events", "quarantine", "outputs", "config"}.issubset({item["page_id"] for item in navigation})
