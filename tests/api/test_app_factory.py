from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app import generate_uuid
from app.api.dependencies import DependencyProbeResult, FilesystemEntry, FilesystemReader
from app.api.main import create_app
from app.config.path_policy import PathPolicy
from app.config.settings import StreamLiteSettings
from app.db.models import JobModel
from app.events.outbox import LIFECYCLE_STREAM_NAME
from app.repositories.commands import CommandRepository
from app.repositories.events import EventOutboxRepository
from app.repositories.files import FileRepository
from app.repositories.jobs import JobRepository
from app.repositories.observability import OperationalLogRepository
from app.repositories.watchers import WatcherRepository


class FakeFilesystemReader(FilesystemReader):
    def __init__(self) -> None:
        self._directories: set[str] = set()
        self._readable: set[str] = set()
        self._writable: set[str] = set()
        self._children: dict[str, list[FilesystemEntry]] = {}

    def add_directory(self, path: str, *, readable: bool = True, writable: bool = True) -> None:
        normalized = _normalize_path(path)
        self._directories.add(normalized)
        if readable:
            self._readable.add(normalized)
        if writable:
            self._writable.add(normalized)
        self._children.setdefault(normalized, [])
        parent = _parent_path(normalized)
        if parent is not None:
            self._children.setdefault(parent, [])
            if normalized not in {entry.path for entry in self._children[parent]}:
                self._children[parent].append(
                    FilesystemEntry(
                        name=normalized.rstrip("/").split("/")[-1],
                        path=normalized,
                        is_directory=True,
                    ),
                )

    def exists(self, path: str) -> bool:
        return _normalize_path(path) in self._directories

    def is_directory(self, path: str) -> bool:
        return self.exists(path)

    def is_readable(self, path: str) -> bool:
        return _normalize_path(path) in self._readable

    def is_writable(self, path: str) -> bool:
        return _normalize_path(path) in self._writable

    def list_entries(self, path: str) -> list[FilesystemEntry]:
        return list(self._children.get(_normalize_path(path), []))


def make_test_settings() -> StreamLiteSettings:
    return StreamLiteSettings(
        api_port=8000,
        dashboard_port=8501,
        broker_profile="redis_streams",
        processing_engine="spark",
        watch_root="/data/sources",
        output_root="/data/outputs",
        quarantine_root="/data/quarantine",
        database_url="postgresql://stream_lite:stream_lite@postgres:5432/stream_lite",
        redis_url="redis://redis:6379/0",
        debug=False,
        file_stability_seconds=2,
        max_file_size_mb=100,
        retry_max_attempts=3,
        retry_initial_backoff_seconds=1,
        retry_backoff_multiplier=2.0,
        retry_max_backoff_seconds=30,
        retry_jitter_enabled=True,
        dashboard_presentation_file="/app/config/dashboard_presentation.yaml",
        log_level="INFO",
        reconciliation_interval_seconds=10,
    )


def build_test_app(
    sqlite_engine: object,
    *,
    settings: StreamLiteSettings | None = None,
    filesystem_reader: FakeFilesystemReader | None = None,
    redis_ready: bool = True,
    dashboard_presentation: dict[str, object] | None = None,
):
    app = create_app()
    active_settings = settings or make_test_settings()
    fs = filesystem_reader or FakeFilesystemReader()
    if filesystem_reader is None:
        for root in (
            active_settings.watch_root,
            active_settings.output_root,
            active_settings.quarantine_root,
        ):
            fs.add_directory(root)

    app.state.settings = active_settings
    app.state.connection = sqlite_engine.connect()
    app.state.session_factory = sessionmaker(
        bind=app.state.connection,
        class_=Session,
        expire_on_commit=False,
    )
    app.state.path_policy = PathPolicy(
        source_roots=(active_settings.watch_root,),
        destination_roots=(active_settings.output_root,),
        debug=active_settings.debug,
    )
    app.state.filesystem_reader = fs
    app.state.redis_probe = (
        lambda _settings: DependencyProbeResult(status="ready", message="ready")
        if redis_ready
        else DependencyProbeResult(
            status="unavailable",
            error_code="BROKER_UNAVAILABLE",
            message="Redis is unavailable.",
        )
    )
    if dashboard_presentation is not None:
        app.state.dashboard_presentation = dashboard_presentation
    return app


@contextmanager
def session_for_app(app) -> Iterator[Session]:
    session_factory = app.state.session_factory
    session = session_factory()
    try:
        yield session
        session.commit()
    finally:
        session.close()


def seed_watcher(
    session: Session,
    *,
    name: str = "watcher-a",
    lifecycle_state: str = "CREATED",
    operational_status: str = "green",
    route_policy: str = "tag_match_all_destinations",
    enabled: bool = False,
    source_display_path: str = "/source-a",
    source_normalized_path: str = "/data/sources/source-a",
    source_tags: list[str] | None = None,
    destination_display_path: str = "/destination-a",
    destination_normalized_path: str = "/data/outputs/destination-a",
    destination_tags: list[str] | None = None,
    include_match: bool = True,
) -> dict[str, object]:
    source_tags = source_tags or ["A"]
    destination_tags = destination_tags or ["A"]

    repository = WatcherRepository(session)
    watcher = repository.create_watcher(
        watcher_id=generate_uuid(),
        name=name,
        lifecycle_state=lifecycle_state,
        operational_status=operational_status,
        route_policy=route_policy,
        enabled=enabled,
        latest_route_preview_at=_ts(12),
    )
    source = repository.replace_sources(
        watcher.watcher_id,
        sources=[
            {
                "source_folder_id": generate_uuid(),
                "display_path": source_display_path,
                "normalized_path": source_normalized_path,
                "route_tags": source_tags,
                "route_tags_text": ";".join(source_tags),
                "health_status": operational_status,
                "reason_code": None,
            },
        ],
    )[0]
    destination = repository.replace_destinations(
        watcher.watcher_id,
        destinations=[
            {
                "destination_folder_id": generate_uuid(),
                "display_path": destination_display_path,
                "normalized_path": destination_normalized_path,
                "route_tags": destination_tags,
                "route_tags_text": ";".join(destination_tags),
                "health_status": operational_status,
                "reason_code": None,
            },
        ],
    )[0]
    route_matches = []
    if include_match and set(source_tags) & set(destination_tags):
        route_matches.append(
            {
                "route_match_id": generate_uuid(),
                "source_folder_id": source.source_folder_id,
                "destination_folder_id": destination.destination_folder_id,
                "route_policy": route_policy,
                "matched_route_tags": sorted(set(source_tags) & set(destination_tags)),
                "unmatched_reason_code": None,
            },
        )
    else:
        route_matches.append(
            {
                "route_match_id": generate_uuid(),
                "source_folder_id": source.source_folder_id,
                "destination_folder_id": None,
                "route_policy": route_policy,
                "matched_route_tags": [],
                "unmatched_reason_code": "NO_MATCHING_DESTINATION",
            },
        )
    repository.save_route_preview(
        watcher.watcher_id,
        route_matches=route_matches,
        previewed_at=_ts(12),
    )
    return {
        "watcher_id": watcher.watcher_id,
        "source_folder_id": source.source_folder_id,
        "destination_folder_id": destination.destination_folder_id,
    }


def seed_job(
    session: Session,
    *,
    watcher_id: UUID,
    source_folder_id: UUID,
    state: str = "FAILED",
    latest_error_code: str | None = "PROCESSOR_TIMEOUT",
    source_display_path: str = "/source-a/example.csv",
    source_container_locator: str = "/data/sources/source-a/example.csv",
    source_file_name: str = "example.csv",
    source_sha256: str = "a" * 64,
    created_at: datetime | None = None,
) -> JobModel:
    file_repository = FileRepository(session)
    file_record = file_repository.create_file_record(
        file_id=generate_uuid(),
        watcher_id=watcher_id,
        source_folder_id=source_folder_id,
        source_display_path=source_display_path,
        source_container_locator=source_container_locator,
        file_name=source_file_name,
        file_extension=".csv",
        size_bytes=128,
        deduplication_key=f"{watcher_id}:{source_file_name}:{source_sha256}",
        first_seen_at=_ts(8),
        stable_at=_ts(8),
        sha256=source_sha256,
    )
    repository = JobRepository(session)
    job = repository.create_job(
        job_id=generate_uuid(),
        file_id=file_record.file_id,
        watcher_id=watcher_id,
        source_folder_id=source_folder_id,
        source_display_path=source_display_path,
        source_container_locator=source_container_locator,
        source_file_name=source_file_name,
        source_extension=".csv",
        source_size_bytes=128,
        source_sha256=source_sha256,
        detected_at=_ts(8),
        stable_at=_ts(8),
        correlation_id=generate_uuid(),
        state=state,
        latest_error_code=latest_error_code,
    )
    if created_at is not None:
        job.created_at = created_at
        job.updated_at = created_at
        session.flush()
    return job


def seed_command(session: Session, *, target_resource_id: UUID, target_resource_type: str = "watcher"):
    repository = CommandRepository(session)
    return repository.create_command(
        command_id=generate_uuid(),
        command_type=f"{target_resource_type}.start",
        target_resource_type=target_resource_type,
        target_resource_id=target_resource_id,
        requested_by="tester",
        operator_reason="for test",
        idempotency_key="command-key",
        correlation_id=generate_uuid(),
    )


def seed_event(session: Session, *, watcher_id: UUID | None = None, job_id: UUID | None = None):
    repository = EventOutboxRepository(session)
    return repository.enqueue_event(
        event_id=generate_uuid(),
        schema_version="1.0.0",
        event_type="job.state_changed",
        stream_name=LIFECYCLE_STREAM_NAME,
        producer="api",
        correlation_id=generate_uuid(),
        idempotency_key="job.state_changed:test",
        occurred_at=_ts(9),
        payload_json={"new_state": "FAILED"},
        watcher_id=watcher_id,
        job_id=job_id,
    )


def seed_log(session: Session, *, message: str) -> None:
    repository = OperationalLogRepository(session)
    repository.write_summary(
        event_name="api.test",
        sanitized_message=message,
        correlation_id=generate_uuid(),
    )


def test_create_app_registers_expected_routes(sqlite_engine) -> None:
    app = build_test_app(sqlite_engine)
    paths = {route.path for route in app.routes}

    assert "/health" in paths
    assert "/health/dependencies" in paths
    assert "/watchers" in paths
    assert "/jobs/{job_id}/retry" in paths
    assert "/events" in paths
    assert "/metrics/summary" in paths
    assert "/logs" in paths
    assert "/files/browse" in paths
    assert "/config/dashboard-presentation" in paths
    assert "/commands/{command_id}" in paths


def test_openapi_uses_documented_schema_names(sqlite_engine) -> None:
    app = build_test_app(sqlite_engine)
    schemas = app.openapi()["components"]["schemas"]

    assert "HealthResponse" in schemas
    assert "WatcherDetailResponse" in schemas
    assert "CommandAcceptedResponse" in schemas
    assert "OperationalLogListResponse" in schemas


def _ts(hour: int) -> datetime:
    return datetime(2026, 5, 1, hour, 0, 0, tzinfo=timezone.utc)


def _normalize_path(path: str) -> str:
    parts = [part for part in path.split("/") if part]
    return "/" + "/".join(parts) if parts else "/"


def _parent_path(path: str) -> str | None:
    normalized = _normalize_path(path)
    if normalized == "/":
        return None
    segments = normalized.strip("/").split("/")
    if len(segments) == 1:
        return "/"
    return "/" + "/".join(segments[:-1])
