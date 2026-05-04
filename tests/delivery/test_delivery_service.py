from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

from app import generate_uuid
from app.artifacts import OutputManifest
from app.config.path_policy import PathPolicy
from app.db.models import (
    DeliveryAttemptModel,
    EventOutboxModel,
    OutputManifestModel,
    RetryScheduleModel,
    StageOwnershipClaimModel,
)
from app.delivery import DeliveryWorker, OutputManifestWriter
from app.repositories.delivery import DeliveryRepository
from app.repositories.events import EventOutboxRepository
from app.repositories.files import FileRepository
from app.repositories.jobs import JobRepository
from app.repositories.stage_claims import StageClaimRepository
from app.repositories.watchers import WatcherRepository

CONTAINER_SOURCE_ROOT = "/stream-lite-test/sources"
CONTAINER_PROCESSING_ROOT = "/stream-lite-test/processing"
CONTAINER_DESTINATION_ROOT = "/stream-lite-test/destinations"


def test_delivery_worker_completes_one_destination_and_persists_attempt_manifest_and_events(
    db_session,
    tmp_path: Path,
) -> None:
    harness = _make_delivery_harness(db_session, tmp_path)

    result = harness["worker"].deliver_one(harness["job_id"], correlation_id=harness["correlation_id"])

    job = harness["jobs"].get_job(harness["job_id"])
    attempts = db_session.query(DeliveryAttemptModel).all()
    manifests = (
        db_session.query(OutputManifestModel)
        .order_by(OutputManifestModel.finalized_at.asc(), OutputManifestModel.created_at.asc())
        .all()
    )
    claims = db_session.query(StageOwnershipClaimModel).all()
    events = _list_events(db_session)

    assert result.status == "delivered"
    assert result.final_state == "COMPLETED"
    assert job is not None and job.state == "COMPLETED"
    assert [row.new_state for row in harness["jobs"].list_state_history(harness["job_id"])] == [
        "PROCESSED",
        "DELIVERING",
        "DELIVERED",
        "COMPLETED",
    ]
    assert len(attempts) == 1
    assert attempts[0].status == "delivered"
    assert attempts[0].temporary_locator is not None
    assert attempts[0].finalized_locator is not None
    assert len(manifests) == 2
    assert manifests[0].status == "processed"
    assert manifests[1].status == "delivered"
    assert [event.event_type for event in events] == [
        "delivery.started",
        "delivery.completed",
        "job.completed",
    ]
    assert claims[0].claim_status == "released"
    assert events[0].payload_json["output_manifest_id"] == str(manifests[1].output_manifest_id)
    assert events[1].payload_json["output_manifest_id"] == str(manifests[1].output_manifest_id)
    assert events[2].payload_json["final_state"] == "COMPLETED"


def test_claim_and_deliver_creates_one_attempt_per_destination_for_multi_destination_success(
    db_session,
    tmp_path: Path,
) -> None:
    harness = _make_delivery_harness(
        db_session,
        tmp_path,
        destinations=(
            {"name": "orders", "tags": ("ORDERS",), "exists": True},
            {"name": "archive", "tags": ("ORDERS", "ARCHIVE"), "exists": True},
        ),
    )

    summary = harness["worker"].claim_and_deliver(limit=1, correlation_id=harness["correlation_id"])

    attempts = (
        db_session.query(DeliveryAttemptModel)
        .order_by(DeliveryAttemptModel.created_at.asc(), DeliveryAttemptModel.destination_folder_id.asc())
        .all()
    )

    assert summary.claimed == 1
    assert summary.delivered == 1
    assert summary.failed == 0
    assert summary.skipped == 0
    assert len(attempts) == 2
    assert {attempt.status for attempt in attempts} == {"delivered"}


def test_partial_delivery_failure_transitions_to_completed_with_delivery_errors(
    db_session,
    tmp_path: Path,
) -> None:
    harness = _make_delivery_harness(
        db_session,
        tmp_path,
        destinations=(
            {"name": "orders", "tags": ("ORDERS",), "exists": True},
            {"name": "archive", "tags": ("ORDERS",), "exists": False},
        ),
    )

    result = harness["worker"].deliver_one(harness["job_id"], correlation_id=harness["correlation_id"])

    job = harness["jobs"].get_job(harness["job_id"])
    attempts = (
        db_session.query(DeliveryAttemptModel)
        .order_by(DeliveryAttemptModel.created_at.asc(), DeliveryAttemptModel.destination_folder_id.asc())
        .all()
    )
    manifests = (
        db_session.query(OutputManifestModel)
        .order_by(OutputManifestModel.finalized_at.asc(), OutputManifestModel.created_at.asc())
        .all()
    )
    events = _list_events(db_session)

    assert result.status == "delivered"
    assert result.final_state == "COMPLETED_WITH_DELIVERY_ERRORS"
    assert job is not None and job.state == "COMPLETED_WITH_DELIVERY_ERRORS"
    assert [attempt.status for attempt in attempts] == ["delivered", "failed"]
    assert manifests[-1].status == "completed_with_delivery_errors"
    failed_destination = next(row for row in harness["watchers"].list_destinations(harness["watcher"].watcher_id) if row.display_path == "/archive")
    assert failed_destination.health_status == "red"
    assert failed_destination.reason_code == "DESTINATION_NOT_FOUND"
    assert [event.event_type for event in events] == [
        "delivery.started",
        "delivery.completed",
        "delivery.started",
        "delivery.failed",
        "job.completed",
    ]
    assert events[-1].payload_json["final_state"] == "COMPLETED_WITH_DELIVERY_ERRORS"


def test_all_retryable_delivery_failures_transition_to_retry_pending_without_scheduling_retry(
    db_session,
    tmp_path: Path,
) -> None:
    harness = _make_delivery_harness(
        db_session,
        tmp_path,
        destinations=(
            {"name": "orders", "tags": ("ORDERS",), "exists": False},
            {"name": "archive", "tags": ("ORDERS",), "exists": False},
        ),
    )

    result = harness["worker"].deliver_one(harness["job_id"], correlation_id=harness["correlation_id"])

    job = harness["jobs"].get_job(harness["job_id"])
    claims = db_session.query(StageOwnershipClaimModel).all()
    events = _list_events(db_session)

    assert result.status == "failed"
    assert result.final_state == "RETRY_PENDING"
    assert job is not None and job.state == "RETRY_PENDING"
    assert claims[0].claim_status == "released"
    assert "COMPLETED" not in [row.new_state for row in harness["jobs"].list_state_history(harness["job_id"])]
    assert [event.event_type for event in events] == [
        "delivery.started",
        "delivery.failed",
        "delivery.started",
        "delivery.failed",
    ]
    assert db_session.query(RetryScheduleModel).count() == 0



def test_retry_released_delivery_job_is_deliverable(
    db_session,
    tmp_path: Path,
) -> None:
    harness = _make_delivery_harness(
        db_session,
        tmp_path,
        job_state="DELIVERING",
        attempt_number=2,
    )

    result = harness["worker"].deliver_one(harness["job_id"], correlation_id=harness["correlation_id"])

    job = harness["jobs"].get_job(harness["job_id"])
    attempt = db_session.query(DeliveryAttemptModel).one()
    history = harness["jobs"].list_state_history(harness["job_id"])
    assert result.status == "delivered"
    assert result.attempt_number == 2
    assert job is not None and job.state == "COMPLETED"
    assert attempt.attempt_number == 2
    assert [row.new_state for row in history][-3:] == ["DELIVERING", "DELIVERED", "COMPLETED"]



def test_source_transfer_failure_marks_source_health_red(
    db_session,
    tmp_path: Path,
) -> None:
    harness = _make_delivery_harness(
        db_session,
        tmp_path,
        source_output_exists=False,
    )

    result = harness["worker"].deliver_one(harness["job_id"], correlation_id=harness["correlation_id"])

    source = harness["watchers"].list_sources(harness["watcher"].watcher_id)[0]
    assert result.status == "failed"
    assert result.final_state == "RETRY_PENDING"
    assert source.health_status == "red"
    assert source.reason_code == "SOURCE_TRANSFER_FAILED"


def test_delivery_manifest_uses_current_correlation_id(
    db_session,
    tmp_path: Path,
) -> None:
    harness = _make_delivery_harness(db_session, tmp_path)
    override_correlation_id = str(uuid4())

    result = harness["worker"].deliver_one(harness["job_id"], correlation_id=override_correlation_id)

    final_manifest_row = db_session.get(OutputManifestModel, result.output_manifest_id)
    assert final_manifest_row is not None
    assert str(final_manifest_row.correlation_id) == override_correlation_id
    manifest_payload = json.loads(Path(harness["resolver"](final_manifest_row.manifest_locator)).read_text(encoding="utf-8"))
    assert manifest_payload["correlation_id"] == override_correlation_id
    assert {str(event.correlation_id) for event in _list_events(db_session)} == {override_correlation_id}

def test_non_processed_job_is_skipped_without_delivery_side_effects(
    db_session,
    tmp_path: Path,
) -> None:
    harness = _make_delivery_harness(
        db_session,
        tmp_path,
        job_state="REGISTERED",
    )

    result = harness["worker"].deliver_one(harness["job_id"], correlation_id=harness["correlation_id"])

    job = harness["jobs"].get_job(harness["job_id"])

    assert result.status == "skipped"
    assert result.reason_code == "JOB_NOT_DELIVERABLE"
    assert job is not None and job.state == "REGISTERED"
    assert db_session.query(DeliveryAttemptModel).count() == 0
    assert db_session.query(StageOwnershipClaimModel).count() == 0
    assert db_session.query(EventOutboxModel).count() == 0


def test_claim_conflict_prevents_copy_events_and_state_changes(
    db_session,
    tmp_path: Path,
) -> None:
    harness = _make_delivery_harness(db_session, tmp_path)
    job = harness["jobs"].get_job(harness["job_id"])
    assert job is not None
    harness["stage_claims"].claim_stage(
        job_id=job.job_id,
        stage="delivery",
        attempt_number=job.attempt_number,
        owner_service="delivery",
        lease_expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
        correlation_id=harness["correlation_id"],
    )
    harness["stage_claims"]._now = lambda: datetime(2026, 5, 2, 15, 0, 0)  # type: ignore[method-assign]

    result = harness["worker"].deliver_one(harness["job_id"], correlation_id=harness["correlation_id"])

    assert result.status == "skipped"
    assert result.reason_code == "JOB_CLAIM_CONFLICT"
    assert harness["jobs"].get_job(harness["job_id"]).state == "PROCESSED"
    assert db_session.query(DeliveryAttemptModel).count() == 0
    assert db_session.query(EventOutboxModel).count() == 0
    assert [row.new_state for row in harness["jobs"].list_state_history(harness["job_id"])] == ["PROCESSED"]


def test_processed_job_without_matching_destination_transitions_to_failed_without_claim_or_events(
    db_session,
    tmp_path: Path,
) -> None:
    harness = _make_delivery_harness(
        db_session,
        tmp_path,
        source_tags=("ORDERS",),
        destinations=(
            {"name": "archive", "tags": ("ARCHIVE",), "exists": True},
        ),
    )

    result = harness["worker"].deliver_one(harness["job_id"], correlation_id=harness["correlation_id"])

    job = harness["jobs"].get_job(harness["job_id"])
    manifests = (
        db_session.query(OutputManifestModel)
        .order_by(OutputManifestModel.finalized_at.asc(), OutputManifestModel.created_at.asc())
        .all()
    )

    assert result.status == "failed"
    assert result.reason_code == "NO_MATCHING_DESTINATION"
    assert job is not None and job.state == "FAILED"
    assert job.latest_error_code == "NO_MATCHING_DESTINATION"
    assert db_session.query(StageOwnershipClaimModel).count() == 0
    assert db_session.query(DeliveryAttemptModel).count() == 0
    assert db_session.query(EventOutboxModel).count() == 0
    assert [row.new_state for row in harness["jobs"].list_state_history(harness["job_id"])] == [
        "PROCESSED",
        "FAILED",
    ]
    assert manifests[-1].status == "failed"


def test_delivery_worker_persists_only_container_locators_and_safe_display_paths(
    db_session,
    tmp_path: Path,
) -> None:
    harness = _make_delivery_harness(db_session, tmp_path)

    harness["worker"].deliver_one(harness["job_id"], correlation_id=harness["correlation_id"])

    attempt = db_session.query(DeliveryAttemptModel).one()
    final_manifest_row = (
        db_session.query(OutputManifestModel)
        .order_by(OutputManifestModel.finalized_at.desc(), OutputManifestModel.created_at.desc())
        .first()
    )
    assert final_manifest_row is not None
    events = _list_events(db_session)
    manifest_text = Path(harness["resolver"](final_manifest_row.manifest_locator)).read_text(encoding="utf-8")
    manifest_payload = OutputManifest.model_validate(json.loads(manifest_text)).model_dump(mode="json")

    _assert_no_host_paths(
        [
            attempt.temporary_locator,
            attempt.finalized_locator,
            attempt.manifest_locator,
            final_manifest_row.manifest_locator,
            final_manifest_row.processing_summary_locator,
            list(final_manifest_row.produced_output_locators),
            final_manifest_row.destination_outcomes,
            manifest_payload,
            [event.payload_json for event in events],
            harness["worker"].log_records,
        ],
        tmp_path,
    )


def _make_delivery_harness(
    db_session,
    tmp_path: Path,
    *,
    source_tags: tuple[str, ...] = ("ORDERS",),
    destinations: tuple[dict[str, object], ...] = (
        {"name": "orders", "tags": ("ORDERS",), "exists": True},
    ),
    job_state: str = "PROCESSED",
    attempt_number: int = 1,
    source_output_exists: bool = True,
):  # type: ignore[no-untyped-def]
    local_sources_root = tmp_path / "sources"
    local_processing_root = tmp_path / "processing"
    local_destinations_root = tmp_path / "destinations"
    local_sources_root.mkdir(parents=True, exist_ok=True)
    local_processing_root.mkdir(parents=True, exist_ok=True)
    local_destinations_root.mkdir(parents=True, exist_ok=True)

    def resolver(container_locator: str):
        if container_locator == CONTAINER_SOURCE_ROOT or container_locator.startswith(f"{CONTAINER_SOURCE_ROOT}/"):
            suffix = container_locator.removeprefix(CONTAINER_SOURCE_ROOT).lstrip("/")
            return local_sources_root / suffix
        if container_locator == CONTAINER_PROCESSING_ROOT or container_locator.startswith(f"{CONTAINER_PROCESSING_ROOT}/"):
            suffix = container_locator.removeprefix(CONTAINER_PROCESSING_ROOT).lstrip("/")
            return local_processing_root / suffix
        if container_locator == CONTAINER_DESTINATION_ROOT or container_locator.startswith(f"{CONTAINER_DESTINATION_ROOT}/"):
            suffix = container_locator.removeprefix(CONTAINER_DESTINATION_ROOT).lstrip("/")
            return local_destinations_root / suffix
        return tmp_path / "unmapped" / container_locator.strip("/").replace("/", "_")

    class Clock:
        def __init__(self) -> None:
            self.calls = 0

        def now(self) -> datetime:
            value = datetime(2026, 5, 2, 15, 0, 0, tzinfo=timezone.utc) + timedelta(seconds=self.calls)
            self.calls += 1
            return value

    clock = Clock()
    watchers = WatcherRepository(db_session)
    watcher = watchers.create_watcher(
        watcher_id=generate_uuid(),
        name="watcher-delivery",
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
                "display_path": "/sources/orders",
                "normalized_path": f"{CONTAINER_SOURCE_ROOT}/orders",
                "route_tags": list(source_tags),
                "route_tags_text": ";".join(source_tags),
                "health_status": "green",
                "reason_code": None,
                "enabled": True,
            },
        ],
    )[0]

    destination_rows = watchers.replace_destinations(
        watcher.watcher_id,
        destinations=[
            {
                "destination_folder_id": uuid4(),
                "display_path": f"/{spec['name']}",
                "normalized_path": f"{CONTAINER_DESTINATION_ROOT}/{spec['name']}",
                "route_tags": list(spec["tags"]),
                "route_tags_text": ";".join(str(tag) for tag in spec["tags"]),
                "health_status": "green",
                "reason_code": None,
                "enabled": True,
            }
            for spec in destinations
        ],
    )

    for spec in destinations:
        if bool(spec["exists"]):
            resolver(f"{CONTAINER_DESTINATION_ROOT}/{spec['name']}").mkdir(parents=True, exist_ok=True)

    file_name = "orders.csv"
    source_path = resolver(f"{CONTAINER_SOURCE_ROOT}/orders/{file_name}")
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text("id,total\n1,10\n", encoding="utf-8")

    file_repository = FileRepository(db_session)
    job_repository = JobRepository(db_session)
    delivery_repository = DeliveryRepository(db_session)
    stage_claim_repository = StageClaimRepository(db_session)
    event_repository = EventOutboxRepository(db_session)
    correlation_id = str(uuid4())

    file_record = file_repository.create_file_record(
        file_id=generate_uuid(),
        watcher_id=watcher.watcher_id,
        source_folder_id=source.source_folder_id,
        source_display_path=f"/sources/orders/{file_name}",
        source_container_locator=f"{CONTAINER_SOURCE_ROOT}/orders/{file_name}",
        file_name=file_name,
        file_extension=".csv",
        size_bytes=source_path.stat().st_size,
        deduplication_key=f"{file_name}:dedupe",
        first_seen_at=clock.now(),
        stable_at=clock.now(),
        sha256="a" * 64,
    )
    job = job_repository.create_job(
        job_id=generate_uuid(),
        file_id=file_record.file_id,
        watcher_id=watcher.watcher_id,
        source_folder_id=source.source_folder_id,
        source_display_path=f"/sources/orders/{file_name}",
        source_container_locator=f"{CONTAINER_SOURCE_ROOT}/orders/{file_name}",
        source_file_name=file_name,
        source_extension=".csv",
        source_size_bytes=source_path.stat().st_size,
        source_sha256="a" * 64,
        detected_at=clock.now(),
        stable_at=clock.now(),
        correlation_id=correlation_id,
        state=job_state,
        attempt_number=attempt_number,
    )

    _seed_state_history(job_repository, job.job_id, job_state, correlation_id, clock.now())

    source_output_locator = f"{CONTAINER_PROCESSING_ROOT}/job_id={job.job_id}/output/{file_name}"
    manifest_locator = f"{CONTAINER_PROCESSING_ROOT}/job_id={job.job_id}/output_manifest.json"
    summary_locator = f"{CONTAINER_PROCESSING_ROOT}/job_id={job.job_id}/processing_summary.json"
    source_output_path = resolver(source_output_locator)
    source_output_path.parent.mkdir(parents=True, exist_ok=True)
    if source_output_exists:
        source_output_path.write_text("id,total\n1,10\n", encoding="utf-8")
    resolver(summary_locator).parent.mkdir(parents=True, exist_ok=True)
    resolver(summary_locator).write_text("{\"status\": \"processed\"}\n", encoding="utf-8")

    processed_manifest_id = None
    if job_state in {"PROCESSED", "DELIVERING"}:
        processed_manifest_id = generate_uuid()
        processed_manifest_payload = {
            "schema_version": "1.0.0",
            "job_id": str(job.job_id),
            "watcher_id": str(watcher.watcher_id),
            "source_sha256": "a" * 64,
            "processor_version": "unknown",
            "processing_summary_locator": summary_locator,
            "produced_output_locators": [source_output_locator],
            "started_at": "2026-05-02T15:00:00Z",
            "completed_at": "2026-05-02T15:00:02Z",
            "duration_seconds": 2,
            "destination_outcomes": [],
            "status": "processed",
            "created_at": "2026-05-02T15:00:02Z",
            "correlation_id": correlation_id,
        }
        OutputManifestWriter(filesystem_resolver=resolver).write_manifest(
            manifest_locator=manifest_locator,
            manifest=processed_manifest_payload,
        )
        delivery_repository.create_output_manifest(
            output_manifest_id=processed_manifest_id,
            job_id=job.job_id,
            watcher_id=watcher.watcher_id,
            schema_version="1.0.0",
            manifest_locator=manifest_locator,
            processing_summary_locator=summary_locator,
            produced_output_locators=[source_output_locator],
            source_sha256="a" * 64,
            destination_outcomes=[],
            finalized_at=clock.now(),
            status="processed",
            correlation_id=correlation_id,
        )

    path_policy = PathPolicy(
        source_roots=(CONTAINER_SOURCE_ROOT, CONTAINER_PROCESSING_ROOT),
        destination_roots=(CONTAINER_DESTINATION_ROOT,),
    )
    worker = DeliveryWorker(
        delivery_repository=delivery_repository,
        job_repository=job_repository,
        stage_claim_repository=stage_claim_repository,
        watcher_repository=watchers,
        event_repository=event_repository,
        path_policy=path_policy,
        clock=clock.now,
        filesystem_resolver=resolver,
        retry_max_attempts=3,
    )
    return {
        "clock": clock,
        "correlation_id": correlation_id,
        "delivery": delivery_repository,
        "destinations": destination_rows,
        "events": event_repository,
        "job_id": job.job_id,
        "jobs": job_repository,
        "processed_manifest_id": processed_manifest_id,
        "resolver": resolver,
        "source": source,
        "stage_claims": stage_claim_repository,
        "watcher": watcher,
        "watchers": watchers,
        "worker": worker,
    }


def _seed_state_history(
    job_repository: JobRepository,
    job_id: UUID,
    state: str,
    correlation_id: str,
    transitioned_at: datetime,
) -> None:
    previous_state = None
    reason_code = "STATE_SEEDED"
    actor_service = "watcher"
    if state == "PROCESSED":
        previous_state = "PROCESSING"
        reason_code = "PROCESSING_COMPLETED"
        actor_service = "processor"
    elif state == "DELIVERING":
        previous_state = "RETRY_PENDING"
        reason_code = "RETRY_DUE"
        actor_service = "retry_scheduler"
    elif state == "REGISTERED":
        previous_state = "STABILIZING"
        reason_code = "JOB_REGISTERED"
    job_repository.append_state_history(
        job_id=job_id,
        previous_state=previous_state,
        new_state=state,
        actor_service=actor_service,
        reason_code=reason_code,
        correlation_id=correlation_id,
        transitioned_at=transitioned_at,
    )


def _list_events(db_session) -> list[EventOutboxModel]:
    return (
        db_session.query(EventOutboxModel)
        .order_by(EventOutboxModel.occurred_at.asc(), EventOutboxModel.event_type.asc())
        .all()
    )


def _assert_no_host_paths(payloads: list[object], tmp_path: Path) -> None:
    tmp_path_text = str(tmp_path)
    tmp_path_posix = tmp_path.as_posix()
    for text in _iter_strings(payloads):
        assert tmp_path_text not in text
        assert tmp_path_posix not in text
        assert not text.startswith("C:\\")
        assert not text.startswith("C:/")
        assert "\\" not in text


def _iter_strings(value: object):  # type: ignore[no-untyped-def]
    if isinstance(value, str):
        yield value
        return
    if isinstance(value, dict):
        for nested in value.values():
            yield from _iter_strings(nested)
        return
    if isinstance(value, (list, tuple, set)):
        for nested in value:
            yield from _iter_strings(nested)
