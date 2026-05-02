from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from app import generate_uuid
from app.config.path_policy import PathPolicy
from app.config.settings import StreamLiteSettings
from app.db.models import EventOutboxModel, QuarantineRecordModel, ValidationAttemptModel
from app.repositories.events import EventOutboxRepository
from app.repositories.files import FileRepository
from app.repositories.jobs import JobRepository
from app.repositories.validation import ValidationRepository
from app.repositories.watchers import WatcherRepository
from app.validation import FileValidator, QuarantineService, ValidationService


class Clock:
    def __init__(self) -> None:
        self.offset = 0.0

    def monotonic(self) -> float:
        return self.offset

    def now(self) -> datetime:
        return datetime(2026, 5, 1, 12, 0, int(self.offset) % 60, tzinfo=timezone.utc)


def test_validation_service_valid_flow(db_session, tmp_path) -> None:
    harness = _make_validation_harness(db_session, tmp_path)
    source_path = harness["local_source_root"] / "valid.csv"
    source_path.write_text("a,b\n1,2\n", encoding="utf-8")
    job_id, correlation_id = _register_job(harness, file_name="valid.csv")

    result = harness["service"].validate_registered_job(job_id, correlation_id=correlation_id)

    job = harness["jobs"].get_job(job_id)
    attempts = db_session.query(ValidationAttemptModel).all()
    events = db_session.query(EventOutboxModel).order_by(EventOutboxModel.created_at.asc()).all()

    assert result.status == "validated"
    assert job is not None and job.state == "VALIDATED"
    assert [row.new_state for row in harness["jobs"].list_state_history(job_id)] == [
        "REGISTERED",
        "VALIDATING",
        "VALIDATED",
    ]
    assert len(attempts) == 1
    assert attempts[0].validation_status == "valid"
    assert attempts[0].reason_codes == []
    assert [event.event_type for event in events] == ["file.validated"]
    assert db_session.query(QuarantineRecordModel).count() == 0
    assert all(str(tmp_path) not in json.dumps(event.payload_json) for event in events)
    rendered_logs = "\n".join(json.dumps(record, sort_keys=True) for record in harness["service"].log_records)
    assert "validation.started" in rendered_logs
    assert "validation.validated" in rendered_logs
    assert "validation.completed" in rendered_logs
    assert str(tmp_path) not in rendered_logs


def test_validation_service_invalid_flow_persists_quarantine_before_event(db_session, tmp_path) -> None:
    harness = _make_validation_harness(db_session, tmp_path)
    source_path = harness["local_source_root"] / "broken.json"
    source_path.write_text("{", encoding="utf-8")
    job_id, correlation_id = _register_job(harness, file_name="broken.json")

    result = harness["service"].validate_registered_job(job_id, correlation_id=correlation_id)

    job = harness["jobs"].get_job(job_id)
    attempt = db_session.query(ValidationAttemptModel).one()
    quarantine_record = db_session.query(QuarantineRecordModel).one()
    event = (
        db_session.query(EventOutboxModel)
        .filter(EventOutboxModel.event_type == "file.quarantined")
        .one()
    )
    artifact_path = (
        harness["local_quarantine_root"]
        / f"watcher_id={job.watcher_id}"
        / "date=2026-05-01"
        / f"job_id={job.job_id}"
        / "quarantine_record.json"
    )
    artifact_payload = json.loads(artifact_path.read_text(encoding="utf-8"))

    assert result.status == "quarantined"
    assert job is not None and job.state == "QUARANTINED"
    assert [row.new_state for row in harness["jobs"].list_state_history(job_id)] == [
        "REGISTERED",
        "VALIDATING",
        "INVALID",
        "QUARANTINED",
    ]
    assert attempt.validation_status == "invalid"
    assert attempt.reason_codes == ["SCHEMA_INVALID"]
    assert quarantine_record.reason_code == "SCHEMA_INVALID"
    assert quarantine_record.copied_size_bytes == source_path.stat().st_size
    assert quarantine_record.created_at <= event.created_at
    assert event.payload_json["reason_codes"] == ["SCHEMA_INVALID"]
    assert artifact_payload["reason_code"] == "SCHEMA_INVALID"
    assert str(tmp_path) not in artifact_path.read_text(encoding="utf-8")
    assert str(tmp_path) not in json.dumps(event.payload_json)
    assert str(tmp_path) not in quarantine_record.quarantine_locator
    rendered_logs = "\n".join(json.dumps(record, sort_keys=True) for record in harness["service"].log_records)
    assert "quarantine.copy_started" in rendered_logs
    assert "quarantine.copy_completed" in rendered_logs
    assert str(tmp_path) not in rendered_logs


def test_reconcile_once_processes_registered_jobs_without_attempts(db_session, tmp_path) -> None:
    harness = _make_validation_harness(db_session, tmp_path)
    valid_source = harness["local_source_root"] / "ok.txt"
    valid_source.write_text("hello", encoding="utf-8")
    valid_job_id, correlation_id = _register_job(harness, file_name="ok.txt")

    skipped_source = harness["local_source_root"] / "skip.txt"
    skipped_source.write_text("skip", encoding="utf-8")
    skipped_job_id, skipped_correlation_id = _register_job(harness, file_name="skip.txt")
    harness["validation_repository"].create_validation_attempt(
        job_id=skipped_job_id,
        attempt_number=1,
        validation_status="valid",
        rules_applied=["PATH_ALLOWLISTED"],
        reason_codes=[],
        started_at=harness["clock"].now(),
        completed_at=harness["clock"].now(),
        duration_seconds=0.01,
        correlation_id=skipped_correlation_id,
    )

    result = harness["service"].reconcile_once(limit=100, correlation_id=correlation_id)

    assert result.processed_jobs == 1
    assert result.skipped_existing_attempts == 1
    assert harness["jobs"].get_job(valid_job_id).state == "VALIDATED"
    assert harness["jobs"].get_job(skipped_job_id).state == "REGISTERED"


def test_handle_job_registered_event_processes_only_valid_events(db_session, tmp_path) -> None:
    harness = _make_validation_harness(db_session, tmp_path)
    source_path = harness["local_source_root"] / "event.json"
    source_path.write_text("[]", encoding="utf-8")
    job_id, correlation_id = _register_job(harness, file_name="event.json")
    job = harness["jobs"].get_job(job_id)

    handled = harness["service"].handle_job_registered_event(
        {
            "schema_version": "1.0.0",
            "event_id": str(uuid4()),
            "idempotency_key": f"job.registered:{job_id}:0",
            "correlation_id": correlation_id,
            "occurred_at": "2026-05-01T12:00:00Z",
            "job_id": str(job_id),
            "watcher_id": str(job.watcher_id),
            "attempt_number": 0,
            "event_type": "job.registered",
            "producer": "watcher",
            "payload": {
                "file_id": str(job.file_id),
                "source_folder_id": str(job.source_folder_id),
                "initial_state": "REGISTERED",
                "route_policy": "tag_match_all_destinations",
                "candidate_destination_count": 1,
            },
        }
    )
    ignored = harness["service"].handle_job_registered_event({"event_type": "file.detected"})
    malformed = harness["service"].handle_job_registered_event({"event_type": "job.registered"})

    assert handled is not None and handled.status == "validated"
    assert ignored is None
    assert malformed is None
    assert db_session.query(ValidationAttemptModel).count() == 1


def _make_validation_harness(db_session, tmp_path):
    local_source_root = tmp_path / "sources" / "source-a"
    local_output_root = tmp_path / "outputs"
    local_quarantine_root = tmp_path / "quarantine"
    local_source_root.mkdir(parents=True, exist_ok=True)
    local_output_root.mkdir(parents=True, exist_ok=True)
    local_quarantine_root.mkdir(parents=True, exist_ok=True)

    container_base = f"/stream-lite-test/{tmp_path.name}"
    container_watch_root = f"{container_base}/sources"
    container_source_root = f"{container_watch_root}/source-a"
    container_output_root = f"{container_base}/outputs"
    container_quarantine_root = f"{container_base}/quarantine"

    settings = StreamLiteSettings(
        api_port=8000,
        dashboard_port=8501,
        broker_profile="redis_streams",
        processing_engine="spark",
        watch_root=container_watch_root,
        output_root=container_output_root,
        quarantine_root=container_quarantine_root,
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
    path_policy = PathPolicy(
        source_roots=(container_watch_root,),
        destination_roots=(container_output_root,),
        debug=False,
    )
    watchers = WatcherRepository(db_session)
    watcher = watchers.create_watcher(
        name="watcher-validation",
        lifecycle_state="ACTIVE",
        operational_status="green",
        route_policy="tag_match_all_destinations",
        enabled=True,
    )
    source = watchers.replace_sources(
        watcher.watcher_id,
        sources=[
            {
                "source_folder_id": uuid4(),
                "display_path": "/source-a",
                "normalized_path": container_source_root,
                "route_tags": ["A"],
                "route_tags_text": "A",
                "health_status": "green",
                "reason_code": None,
            },
        ],
    )[0]

    def filesystem_resolver(container_path: str):
        if container_path == container_watch_root or container_path.startswith(f"{container_watch_root}/"):
            return local_source_root.parent / container_path.removeprefix(container_watch_root).lstrip("/")
        if container_path == container_output_root or container_path.startswith(f"{container_output_root}/"):
            return local_output_root / container_path.removeprefix(container_output_root).lstrip("/")
        if container_path == container_quarantine_root or container_path.startswith(f"{container_quarantine_root}/"):
            return local_quarantine_root / container_path.removeprefix(container_quarantine_root).lstrip("/")
        return container_path

    clock = Clock()
    file_repository = FileRepository(db_session)
    job_repository = JobRepository(db_session)
    validation_repository = ValidationRepository(db_session)
    event_repository = EventOutboxRepository(db_session)
    validator = FileValidator(
        path_policy=path_policy,
        settings=settings,
        filesystem_resolver=filesystem_resolver,
        monotonic=clock.monotonic,
    )
    quarantine_service = QuarantineService(
        settings=settings,
        path_policy=path_policy,
        filesystem_resolver=filesystem_resolver,
        now=clock.now,
    )
    service = ValidationService(
        job_repository=job_repository,
        file_repository=file_repository,
        validation_repository=validation_repository,
        event_repository=event_repository,
        validator=validator,
        quarantine_service=quarantine_service,
        now=clock.now,
        monotonic=clock.monotonic,
    )
    return {
        "clock": clock,
        "container_source_root": container_source_root,
        "event_repository": event_repository,
        "jobs": job_repository,
        "local_quarantine_root": local_quarantine_root,
        "local_source_root": local_source_root,
        "service": service,
        "source": source,
        "validation_repository": validation_repository,
        "watcher": watcher,
        "file_repository": file_repository,
    }


def _register_job(harness, *, file_name: str) -> tuple[UUID, str]:  # type: ignore[no-untyped-def]
    correlation_id = str(uuid4())
    file_record = harness["file_repository"].create_file_record(
        file_id=generate_uuid(),
        watcher_id=harness["watcher"].watcher_id,
        source_folder_id=harness["source"].source_folder_id,
        source_display_path=f"/source-a/{file_name}",
        source_container_locator=f"{harness['container_source_root']}/{file_name}",
        file_name=file_name,
        file_extension=Path(file_name).suffix,
        size_bytes=(harness["local_source_root"] / file_name).stat().st_size,
        deduplication_key=f"{file_name}:dedupe",
        first_seen_at=harness["clock"].now(),
        stable_at=harness["clock"].now(),
        sha256="c" * 64,
    )
    job = harness["jobs"].create_job(
        job_id=generate_uuid(),
        file_id=file_record.file_id,
        watcher_id=harness["watcher"].watcher_id,
        source_folder_id=harness["source"].source_folder_id,
        source_display_path=f"/source-a/{file_name}",
        source_container_locator=f"{harness['container_source_root']}/{file_name}",
        source_file_name=file_name,
        source_extension=Path(file_name).suffix,
        source_size_bytes=(harness["local_source_root"] / file_name).stat().st_size,
        source_sha256="c" * 64,
        detected_at=harness["clock"].now(),
        stable_at=harness["clock"].now(),
        correlation_id=correlation_id,
        state="REGISTERED",
    )
    harness["jobs"].append_state_history(
        job_id=job.job_id,
        previous_state="STABILIZING",
        new_state="REGISTERED",
        actor_service="watcher",
        reason_code="JOB_REGISTERED",
        correlation_id=correlation_id,
        transitioned_at=harness["clock"].now(),
    )
    return job.job_id, correlation_id
