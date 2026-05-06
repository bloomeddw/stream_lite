from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app import generate_uuid
from app.db.models import RetryScheduleModel
from app.repositories.jobs import JobRepository
from app.repositories.processing import ProcessingRepository
from tests.api.test_app_factory import build_test_app, seed_job, seed_watcher, session_for_app


def test_list_jobs_filters_and_orders(sqlite_engine) -> None:
    app = build_test_app(sqlite_engine)
    with session_for_app(app) as session:
        first = seed_watcher(session, name="watcher-one")
        second = seed_watcher(session, name="watcher-two")
        seed_job(
            session,
            watcher_id=first["watcher_id"],
            source_folder_id=first["source_folder_id"],
            state="FAILED",
            created_at=datetime(2026, 5, 1, 8, 0, 0, tzinfo=timezone.utc),
        )
        seed_job(
            session,
            watcher_id=second["watcher_id"],
            source_folder_id=second["source_folder_id"],
            state="FAILED",
            created_at=datetime(2026, 5, 1, 9, 0, 0, tzinfo=timezone.utc),
        )

    client = TestClient(app)
    response = client.get("/jobs", params={"state": "FAILED"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert payload["items"][0]["created_at"] > payload["items"][1]["created_at"]


def test_get_job_detail_composes_summary(sqlite_engine) -> None:
    app = build_test_app(sqlite_engine)
    with session_for_app(app) as session:
        watcher_ids = seed_watcher(session)
        job = seed_job(
            session,
            watcher_id=watcher_ids["watcher_id"],
            source_folder_id=watcher_ids["source_folder_id"],
            state="FAILED",
        )
        ProcessingRepository(session).create_processing_attempt(
            job_id=job.job_id,
            attempt_number=1,
            engine="spark",
            engine_version="3.5.0",
            input_locator=job.source_container_locator,
            started_at=datetime(2026, 5, 1, 10, 0, 0, tzinfo=timezone.utc),
            correlation_id=job.correlation_id,
            status="failed",
        )

    client = TestClient(app)
    response = client.get(f"/jobs/{job.job_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"] == str(job.job_id)
    assert payload["attempt_summary"]["processing_attempts"] == 1
    assert payload["latest_error"]["error_code"] == "PROCESSOR_TIMEOUT"


def test_get_job_history_returns_entries(sqlite_engine) -> None:
    app = build_test_app(sqlite_engine)
    with session_for_app(app) as session:
        watcher_ids = seed_watcher(session)
        job = seed_job(session, watcher_id=watcher_ids["watcher_id"], source_folder_id=watcher_ids["source_folder_id"], state="REGISTERED", latest_error_code=None)
        repository = JobRepository(session)
        repository.append_state_history(
            job_id=job.job_id,
            previous_state="REGISTERED",
            new_state="VALIDATING",
            actor_service="validator",
            reason_code="VALIDATION_STARTED",
            correlation_id=job.correlation_id,
            transitioned_at=datetime(2026, 5, 1, 11, 0, 0, tzinfo=timezone.utc),
            event_id=generate_uuid(),
        )

    client = TestClient(app)
    response = client.get(f"/jobs/{job.job_id}/history")

    assert response.status_code == 200
    assert response.json()["history"][0]["to_state"] == "VALIDATING"


def test_retry_persists_command(sqlite_engine) -> None:
    app = build_test_app(sqlite_engine)
    with session_for_app(app) as session:
        watcher_ids = seed_watcher(session)
        job = seed_job(session, watcher_id=watcher_ids["watcher_id"], source_folder_id=watcher_ids["source_folder_id"], state="FAILED")
        ProcessingRepository(session).create_processing_attempt(
            job_id=job.job_id,
            attempt_number=1,
            engine="spark",
            engine_version="3.5.0",
            input_locator=job.source_container_locator,
            started_at=datetime(2026, 5, 1, 10, 0, 0, tzinfo=timezone.utc),
            correlation_id=job.correlation_id,
            status="failed",
        )

    client = TestClient(app)
    response = client.post(
        f"/jobs/{job.job_id}/retry",
        json={"requested_by": "tester", "reason": "manual retry"},
    )

    assert response.status_code == 202
    assert response.json()["target_resource_type"] == "job"
    with session_for_app(app) as session:
        refreshed_job = JobRepository(session).get_job(job.job_id)
        schedules = (
            session.query(RetryScheduleModel)
            .filter(RetryScheduleModel.job_id == job.job_id)
            .order_by(RetryScheduleModel.created_at.asc())
            .all()
        )

    assert refreshed_job is not None and refreshed_job.state == "RETRY_PENDING"
    assert refreshed_job.attempt_number == 2
    assert len(schedules) == 1
    assert schedules[0].failed_stage == "processing"
    assert schedules[0].next_stage == "processing"
    assert schedules[0].attempt_number == 2


def test_retry_rejects_non_retryable_job(sqlite_engine) -> None:
    app = build_test_app(sqlite_engine)
    with session_for_app(app) as session:
        watcher_ids = seed_watcher(session)
        job = seed_job(
            session,
            watcher_id=watcher_ids["watcher_id"],
            source_folder_id=watcher_ids["source_folder_id"],
            state="QUARANTINED",
            latest_error_code="SCHEMA_INVALID",
        )

    client = TestClient(app)
    response = client.post(
        f"/jobs/{job.job_id}/retry",
        json={"requested_by": "tester", "reason": "manual retry"},
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "JOB_NOT_RETRYABLE"


def test_retry_reuses_idempotency_for_identical_payload(sqlite_engine) -> None:
    app = build_test_app(sqlite_engine)
    with session_for_app(app) as session:
        watcher_ids = seed_watcher(session)
        job = seed_job(session, watcher_id=watcher_ids["watcher_id"], source_folder_id=watcher_ids["source_folder_id"], state="FAILED")
        ProcessingRepository(session).create_processing_attempt(
            job_id=job.job_id,
            attempt_number=1,
            engine="spark",
            engine_version="3.5.0",
            input_locator=job.source_container_locator,
            started_at=datetime(2026, 5, 1, 10, 0, 0, tzinfo=timezone.utc),
            correlation_id=job.correlation_id,
            status="failed",
        )

    client = TestClient(app)
    headers = {"Idempotency-Key": "job-retry-key"}
    body = {"requested_by": "tester", "reason": "manual retry"}
    first = client.post(f"/jobs/{job.job_id}/retry", json=body, headers=headers)
    second = client.post(f"/jobs/{job.job_id}/retry", json=body, headers=headers)

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["command_id"] == second.json()["command_id"]


def test_retry_rejects_idempotency_key_payload_conflict(sqlite_engine) -> None:
    app = build_test_app(sqlite_engine)
    with session_for_app(app) as session:
        watcher_ids = seed_watcher(session)
        job = seed_job(session, watcher_id=watcher_ids["watcher_id"], source_folder_id=watcher_ids["source_folder_id"], state="FAILED")
        ProcessingRepository(session).create_processing_attempt(
            job_id=job.job_id,
            attempt_number=1,
            engine="spark",
            engine_version="3.5.0",
            input_locator=job.source_container_locator,
            started_at=datetime(2026, 5, 1, 10, 0, 0, tzinfo=timezone.utc),
            correlation_id=job.correlation_id,
            status="failed",
        )

    client = TestClient(app)
    headers = {"Idempotency-Key": "job-retry-conflict-key"}
    first = client.post(
        f"/jobs/{job.job_id}/retry",
        json={"requested_by": "tester", "reason": "manual retry"},
        headers=headers,
    )
    second = client.post(
        f"/jobs/{job.job_id}/retry",
        json={"requested_by": "tester", "reason": "different retry reason"},
        headers=headers,
    )

    assert first.status_code == 202
    assert second.status_code == 409
    assert second.json()["error_code"] == "IDEMPOTENCY_KEY_CONFLICT"
