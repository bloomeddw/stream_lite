from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from app import generate_uuid
from app.db.models import DeliveryAttemptModel, EventOutboxModel, OutputManifestModel, ProcessingAttemptModel, StageOwnershipClaimModel
from app.processing import ProcessingAdapterResult, ProcessingWorker, SparkDemoAdapter
from app.repositories.delivery import DeliveryRepository
from app.repositories.events import EventOutboxRepository
from app.repositories.files import FileRepository
from app.repositories.jobs import JobRepository
from app.repositories.processing import ProcessingRepository
from app.repositories.stage_claims import StageClaimRepository
from app.repositories.validation import ValidationRepository
from app.repositories.watchers import WatcherRepository


@pytest.fixture()
def workspace_path(tmp_path: Path) -> Path:
    return tmp_path


def test_validated_job_processes_successfully_and_persists_attempt_manifest_and_events(db_session, workspace_path: Path) -> None:
    harness = _make_processing_harness(db_session, workspace_path)
    job_id, correlation_id = _register_job(harness, file_name="orders.csv", content="id,total\n1,10\n2,20\n")

    result = harness["worker"].process_one(job_id, correlation_id=correlation_id)

    job = harness["jobs"].get_job(job_id)
    attempts = db_session.query(ProcessingAttemptModel).all()
    manifests = db_session.query(OutputManifestModel).all()
    claims = db_session.query(StageOwnershipClaimModel).all()
    events = (
        db_session.query(EventOutboxModel)
        .order_by(EventOutboxModel.occurred_at.asc(), EventOutboxModel.event_type.asc())
        .all()
    )

    assert result.status == "processed"
    assert job is not None and job.state == "PROCESSED"
    assert [row.new_state for row in harness["jobs"].list_state_history(job_id)] == [
        "VALIDATED",
        "PROCESSING",
        "PROCESSED",
    ]
    assert len(attempts) == 1
    assert attempts[0].status == "processed"
    assert attempts[0].output_locator is not None
    assert attempts[0].summary_locator is not None
    assert len(manifests) == 1
    assert manifests[0].status == "processed"
    assert manifests[0].destination_outcomes == []
    assert db_session.query(DeliveryAttemptModel).count() == 0
    assert claims[0].claim_status == "released"
    assert [event.event_type for event in events] == ["processing.started", "processing.completed"]
    assert all(row.new_state != "DELIVERING" for row in harness["jobs"].list_state_history(job_id))


def test_claim_and_process_processes_validated_jobs(db_session, workspace_path: Path) -> None:
    harness = _make_processing_harness(db_session, workspace_path)
    job_id, correlation_id = _register_job(harness, file_name="single.txt", content="hello\nworld\n")

    summary = harness["worker"].claim_and_process(limit=1, correlation_id=correlation_id)

    assert summary.claimed == 1
    assert summary.processed == 1
    assert summary.failed == 0
    assert summary.skipped == 0
    assert harness["jobs"].get_job(job_id).state == "PROCESSED"


def test_retry_released_processing_job_is_processable(db_session, workspace_path: Path) -> None:
    harness = _make_processing_harness(db_session, workspace_path)
    job_id, correlation_id = _register_job(
        harness,
        file_name="retry.csv",
        content="id,total\n1,10\n",
        state="PROCESSING",
        attempt_number=2,
    )

    result = harness["worker"].process_one(job_id, correlation_id=correlation_id)

    job = harness["jobs"].get_job(job_id)
    attempt = db_session.query(ProcessingAttemptModel).one()
    history = harness["jobs"].list_state_history(job_id)
    assert result.status == "processed"
    assert result.attempt_number == 2
    assert job is not None and job.state == "PROCESSED"
    assert attempt.attempt_number == 2
    assert [row.new_state for row in history][-2:] == ["PROCESSING", "PROCESSED"]


def test_retryable_adapter_failure_transitions_to_retry_pending_and_releases_claim(db_session, workspace_path: Path) -> None:
    harness = _make_processing_harness(
        db_session,
        workspace_path,
        adapter=StubAdapter(
            status="failed",
            error_code="PROCESSING_INPUT_UNAVAILABLE",
            retryable=True,
            operator_message="Processing input is unavailable.",
            completed_at=datetime(2026, 5, 2, 12, 0, 1, tzinfo=timezone.utc),
        ),
    )
    job_id, correlation_id = _register_job(harness, file_name="orders.csv", content="id,total\n1,10\n")

    result = harness["worker"].process_one(job_id, correlation_id=correlation_id)

    job = harness["jobs"].get_job(job_id)
    attempt = db_session.query(ProcessingAttemptModel).one()
    claim = db_session.query(StageOwnershipClaimModel).one()
    events = db_session.query(EventOutboxModel).order_by(EventOutboxModel.occurred_at.asc()).all()

    assert result.status == "failed"
    assert job is not None and job.state == "RETRY_PENDING"
    assert attempt.status == "failed"
    assert attempt.error_code == "PROCESSING_INPUT_UNAVAILABLE"
    assert claim.claim_status == "released"
    assert [event.event_type for event in events] == ["processing.started", "processing.failed"]
    assert db_session.query(OutputManifestModel).count() == 0


def test_non_retryable_adapter_failure_transitions_to_failed(db_session, workspace_path: Path) -> None:
    harness = _make_processing_harness(
        db_session,
        workspace_path,
        adapter=StubAdapter(
            status="failed",
            error_code="PROCESSING_INPUT_INVALID",
            retryable=False,
            operator_message="Processing input is invalid.",
            completed_at=datetime(2026, 5, 2, 12, 0, 1, tzinfo=timezone.utc),
        ),
    )
    job_id, correlation_id = _register_job(harness, file_name="orders.json", content="[]")

    result = harness["worker"].process_one(job_id, correlation_id=correlation_id)

    job = harness["jobs"].get_job(job_id)
    claim = db_session.query(StageOwnershipClaimModel).one()

    assert result.status == "failed"
    assert job is not None and job.state == "FAILED"
    assert claim.claim_status == "released"


def test_non_validated_job_is_skipped_without_side_effects(db_session, workspace_path: Path) -> None:
    harness = _make_processing_harness(db_session, workspace_path)
    job_id, correlation_id = _register_job(
        harness,
        file_name="registered.txt",
        content="skip me\n",
        state="REGISTERED",
        attempt_number=0,
    )

    result = harness["worker"].process_one(job_id, correlation_id=correlation_id)

    job = harness["jobs"].get_job(job_id)
    assert result.status == "skipped"
    assert result.reason_code == "JOB_NOT_PROCESSABLE"
    assert job is not None and job.state == "REGISTERED"
    assert db_session.query(ProcessingAttemptModel).count() == 0
    assert db_session.query(StageOwnershipClaimModel).count() == 0
    assert db_session.query(EventOutboxModel).count() == 0


def test_validated_job_without_successful_validation_attempt_is_skipped_without_processing_side_effects(db_session, workspace_path: Path) -> None:
    adapter = StubAdapter(status="processed", completed_at=datetime(2026, 5, 2, 12, 0, 1, tzinfo=timezone.utc))
    harness = _make_processing_harness(db_session, workspace_path, adapter=adapter)
    job_id, correlation_id = _register_job(
        harness,
        file_name="missing-validation.csv",
        content="id\n1\n",
        validation_attempt_status=None,
    )

    result = harness["worker"].process_one(job_id, correlation_id=correlation_id)

    assert result.status == "skipped"
    assert result.reason_code == "PROCESSING_VALIDATION_NOT_CONFIRMED"
    assert result.error_code == "PROCESSING_VALIDATION_NOT_CONFIRMED"
    assert adapter.calls == 0
    assert harness["jobs"].get_job(job_id).state == "VALIDATED"
    assert db_session.query(ProcessingAttemptModel).count() == 0
    assert db_session.query(StageOwnershipClaimModel).count() == 0
    assert db_session.query(EventOutboxModel).count() == 0


def test_duplicate_claim_conflict_skips_without_adapter_execution_or_processing_side_effects(db_session, workspace_path: Path) -> None:
    adapter = StubAdapter(
        status="processed",
        completed_at=datetime(2026, 5, 2, 12, 0, 1, tzinfo=timezone.utc),
    )
    harness = _make_processing_harness(db_session, workspace_path, adapter=adapter)
    job_id, correlation_id = _register_job(harness, file_name="conflict.csv", content="id\n1\n")
    job = harness["jobs"].get_job(job_id)
    assert job is not None
    harness["stage_claims"].claim_stage(
        job_id=job.job_id,
        stage="processing",
        attempt_number=job.attempt_number,
        owner_service="processor",
        lease_expires_at=datetime(2026, 5, 2, 12, 5, 0, tzinfo=timezone.utc),
        correlation_id=correlation_id,
    )
    harness["stage_claims"]._now = lambda: datetime(2026, 5, 2, 12, 0, 0)  # type: ignore[method-assign]

    result = harness["worker"].process_one(job_id, correlation_id=correlation_id)

    assert result.status == "skipped"
    assert result.reason_code == "JOB_CLAIM_CONFLICT"
    assert adapter.calls == 0
    assert harness["jobs"].get_job(job_id).state == "VALIDATED"
    assert db_session.query(ProcessingAttemptModel).count() == 0
    assert db_session.query(EventOutboxModel).count() == 0
    assert [row.new_state for row in harness["jobs"].list_state_history(job_id)] == ["VALIDATED"]


@dataclass
class StubAdapter:
    status: str
    error_code: str | None = None
    retryable: bool = False
    operator_message: str = "Processed."
    completed_at: datetime = datetime(2026, 5, 2, 12, 0, 1, tzinfo=timezone.utc)

    def __post_init__(self) -> None:
        self.calls = 0
        self.engine = "spark"
        self.engine_version = "test"

    def run_demo_transform(self, adapter_input) -> ProcessingAdapterResult:  # type: ignore[no-untyped-def]
        self.calls += 1
        completed_at = self.completed_at
        if completed_at <= adapter_input.started_at:
            completed_at = adapter_input.started_at + timedelta(seconds=1)
        if self.status == "processed":
            return ProcessingAdapterResult(
                status="processed",
                engine=self.engine,
                engine_version=self.engine_version,
                input_locator=adapter_input.input_locator,
                output_locator="/stream-lite-test/processing/job_id=test/output/result.txt",
                summary_locator="/stream-lite-test/processing/job_id=test/processing_summary.json",
                manifest_locator="/stream-lite-test/processing/job_id=test/output_manifest.json",
                output_manifest_id=generate_uuid(),
                row_count=1,
                record_count=1,
                byte_count=1,
                bytes_written=1,
                started_at=adapter_input.started_at,
                completed_at=completed_at,
                duration_seconds=1,
                error_code=None,
                retryable=False,
                operator_message=self.operator_message,
            )
        return ProcessingAdapterResult(
            status="failed",
            engine=self.engine,
            engine_version=self.engine_version,
            input_locator=adapter_input.input_locator,
            output_locator=None,
            summary_locator=None,
            manifest_locator=None,
            output_manifest_id=None,
            row_count=None,
            record_count=None,
            byte_count=None,
            bytes_written=None,
            started_at=adapter_input.started_at,
            completed_at=completed_at,
            duration_seconds=1,
            error_code=self.error_code,
            retryable=self.retryable,
            operator_message=self.operator_message,
        )


def _make_processing_harness(db_session, tmp_path: Path, *, adapter=None):  # type: ignore[no-untyped-def]
    local_source_root = tmp_path / "source"
    local_processing_root = tmp_path / "processing"
    local_source_root.mkdir(parents=True, exist_ok=True)
    local_processing_root.mkdir(parents=True, exist_ok=True)

    container_source_root = "/stream-lite-test/source"
    container_processing_root = "/stream-lite-test/processing"

    def resolver(container_locator: str):
        if container_locator == container_source_root or container_locator.startswith(f"{container_source_root}/"):
            return local_source_root / container_locator.removeprefix(container_source_root).lstrip("/")
        if container_locator == container_processing_root or container_locator.startswith(f"{container_processing_root}/"):
            return local_processing_root / container_locator.removeprefix(container_processing_root).lstrip("/")
        return container_locator

    class Clock:
        def __init__(self) -> None:
            self.calls = 0

        def now(self) -> datetime:
            value = datetime(2026, 5, 2, 12, 0, 0, tzinfo=timezone.utc) + timedelta(seconds=self.calls)
            self.calls += 1
            return value

    clock = Clock()
    watcher_repository = WatcherRepository(db_session)
    watcher = watcher_repository.create_watcher(
        name="watcher-processing",
        lifecycle_state="ACTIVE",
        operational_status="green",
        route_policy="tag_match_all_destinations",
        enabled=True,
    )
    source = watcher_repository.replace_sources(
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

    file_repository = FileRepository(db_session)
    job_repository = JobRepository(db_session)
    processing_repository = ProcessingRepository(db_session)
    stage_claim_repository = StageClaimRepository(db_session)
    delivery_repository = DeliveryRepository(db_session)
    event_repository = EventOutboxRepository(db_session)
    validation_repository = ValidationRepository(db_session)
    worker = ProcessingWorker(
        processing_repository=processing_repository,
        stage_claim_repository=stage_claim_repository,
        job_repository=job_repository,
        delivery_repository=delivery_repository,
        event_repository=event_repository,
        validation_repository=validation_repository,
        adapter=adapter
        or SparkDemoAdapter(
            processing_root=container_processing_root,
            filesystem_resolver=resolver,
            clock=clock.now,
        ),
        clock=clock.now,
        filesystem_resolver=resolver,
        retry_max_attempts=3,
    )
    return {
        "clock": clock,
        "container_processing_root": container_processing_root,
        "container_source_root": container_source_root,
        "delivery": delivery_repository,
        "events": event_repository,
        "file_repository": file_repository,
        "jobs": job_repository,
        "local_processing_root": local_processing_root,
        "local_source_root": local_source_root,
        "processing": processing_repository,
        "source": source,
        "stage_claims": stage_claim_repository,
        "validation_repository": validation_repository,
        "watcher": watcher,
        "worker": worker,
    }


def _register_job(
    harness,
    *,
    file_name: str,
    content: str,
    state: str = "VALIDATED",
    attempt_number: int = 1,
    validation_attempt_status: str | None = "valid",
) -> tuple[UUID, str]:  # type: ignore[no-untyped-def]
    source_path = harness["local_source_root"] / file_name
    source_path.write_text(content, encoding="utf-8")
    correlation_id = str(uuid4())
    file_record = harness["file_repository"].create_file_record(
        file_id=generate_uuid(),
        watcher_id=harness["watcher"].watcher_id,
        source_folder_id=harness["source"].source_folder_id,
        source_display_path=f"/source-a/{file_name}",
        source_container_locator=f"{harness['container_source_root']}/{file_name}",
        file_name=file_name,
        file_extension=Path(file_name).suffix,
        size_bytes=source_path.stat().st_size,
        deduplication_key=f"{file_name}:dedupe",
        first_seen_at=harness["clock"].now(),
        stable_at=harness["clock"].now(),
        sha256="d" * 64,
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
        source_size_bytes=source_path.stat().st_size,
        source_sha256="d" * 64,
        detected_at=harness["clock"].now(),
        stable_at=harness["clock"].now(),
        correlation_id=correlation_id,
        state=state,
        attempt_number=attempt_number,
    )
    if state in {"VALIDATED", "PROCESSING"}:
        if validation_attempt_status is not None:
            harness["validation_repository"].create_validation_attempt(
                job_id=job.job_id,
                attempt_number=attempt_number,
                validation_status=validation_attempt_status,
                rules_applied=["PATH_ALLOWLISTED", "FILE_EXISTS", "FILE_READABLE", "FILE_SIZE_LIMIT", "EXTENSION_ALLOWED", "FILE_NON_EMPTY", "STRUCTURED_FORMAT"],
                reason_codes=[] if validation_attempt_status == "valid" else ["SCHEMA_INVALID"],
                started_at=harness["clock"].now(),
                completed_at=harness["clock"].now(),
                duration_seconds=1.0,
                correlation_id=correlation_id,
            )
        if state == "VALIDATED":
            harness["jobs"].append_state_history(
                job_id=job.job_id,
                previous_state="VALIDATING",
                new_state="VALIDATED",
                actor_service="validator",
                reason_code="VALIDATION_PASSED",
                correlation_id=correlation_id,
                transitioned_at=harness["clock"].now(),
            )
        else:
            harness["jobs"].append_state_history(
                job_id=job.job_id,
                previous_state="RETRY_PENDING",
                new_state="PROCESSING",
                actor_service="retry_scheduler",
                reason_code="RETRY_DUE",
                correlation_id=correlation_id,
                transitioned_at=harness["clock"].now(),
            )
    elif state == "REGISTERED":
        harness["jobs"].append_state_history(
            job_id=job.job_id,
            previous_state="STABILIZING",
            new_state="REGISTERED",
            actor_service="watcher",
            reason_code="JOB_REGISTERED",
            correlation_id=correlation_id,
            transitioned_at=harness["clock"].now(),
        )
    else:
        harness["jobs"].append_state_history(
            job_id=job.job_id,
            previous_state=None,
            new_state=state,
            actor_service="watcher",
            reason_code="STATE_SEEDED",
            correlation_id=correlation_id,
            transitioned_at=harness["clock"].now(),
        )
    return job.job_id, correlation_id
