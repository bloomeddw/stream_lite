"""Duplicate suppression helpers for WP-06 watcher orchestration."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.repositories.files import FileRepository
from app.repositories.jobs import JobRepository

DUPLICATE_SUPPRESSED = "DUPLICATE_SUPPRESSED"


@dataclass(frozen=True, slots=True)
class DuplicateCheckResult:
    is_duplicate: bool
    existing_job_id: UUID | None = None
    existing_file_id: UUID | None = None


def compute_deduplication_key(
    watcher_id: UUID | str,
    source_folder_id: UUID | str,
    source_display_path: str,
    size_bytes: int,
    sha256: str,
) -> str:
    """Build a deterministic bounded duplicate key from the documented WP-06 fields."""

    raw_key = "|".join(
        (
            str(watcher_id),
            str(source_folder_id),
            source_display_path,
            str(int(size_bytes)),
            sha256.lower(),
        ),
    )
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def check_duplicate(
    file_repository: FileRepository,
    job_repository: JobRepository,
    *,
    deduplication_key: str,
) -> DuplicateCheckResult:
    """Return the existing job for a duplicate deduplication key when present."""

    existing_file = file_repository.find_by_deduplication_key(deduplication_key)
    if existing_file is None:
        return DuplicateCheckResult(is_duplicate=False)
    jobs = job_repository.list_jobs(file_name=existing_file.file_name, watcher_id=existing_file.watcher_id)
    existing_job_id = None
    for job in jobs:
        if job.file_id == existing_file.file_id:
            existing_job_id = job.job_id
            break
    return DuplicateCheckResult(
        is_duplicate=True,
        existing_job_id=existing_job_id,
        existing_file_id=existing_file.file_id,
    )


def record_duplicate_observation(
    file_repository: FileRepository,
    *,
    existing_job_id: UUID | str,
    watcher_id: UUID | str,
    source_folder_id: UUID | str,
    source_display_path: str,
    byte_size: int,
    content_hash: str,
    observed_at: datetime,
):
    """Persist a duplicate suppression observation with the documented reason code."""

    return file_repository.record_duplicate_observation(
        existing_job_id=existing_job_id,
        watcher_id=watcher_id,
        source_folder_id=source_folder_id,
        source_display_path=source_display_path,
        byte_size=byte_size,
        content_hash=content_hash,
        observed_at=observed_at,
        reason_code=DUPLICATE_SUPPRESSED,
    )


__all__ = [
    "DUPLICATE_SUPPRESSED",
    "DuplicateCheckResult",
    "check_duplicate",
    "compute_deduplication_key",
    "record_duplicate_observation",
]
