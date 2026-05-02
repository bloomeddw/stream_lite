"""Poll-once watcher orchestration for WP-06."""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from uuid import UUID

from app import generate_uuid, ensure_uuid_str
from app.config.path_policy import PathPolicy
from app.config.settings import StreamLiteSettings
from app.events.outbox import LIFECYCLE_STREAM_NAME, enqueue_event
from app.observability.logging import configure_structured_logging, emit_structured_log
from app.repositories.events import EventOutboxRepository
from app.repositories.files import FileRepository
from app.repositories.jobs import JobRepository
from app.repositories.watchers import WatcherRepository
from app.watcher.deduplication import (
    check_duplicate,
    compute_deduplication_key,
    record_duplicate_observation,
)
from app.watcher.routing import build_route_preview, match_source_to_destinations
from app.watcher.stability import FileSnapshot, capture_file_snapshot, is_file_stable, sha256_file

FilesystemResolver = Callable[[str], str | Path]


@dataclass(frozen=True, slots=True)
class PollOnceResult:
    watcher_id: UUID
    scanned_sources: int = 0
    observed_files: int = 0
    stabilized_files: int = 0
    jobs_registered: int = 0
    duplicates_suppressed: int = 0
    skipped_sources: int = 0
    skipped_reason: str | None = None


class WatcherService:
    """Coordinate one watcher polling pass without running a long-lived daemon."""

    def __init__(
        self,
        *,
        watcher_repository: WatcherRepository,
        file_repository: FileRepository,
        job_repository: JobRepository,
        event_repository: EventOutboxRepository,
        path_policy: PathPolicy,
        settings: StreamLiteSettings,
        monotonic: Callable[[], float] | None = None,
        now: Callable[[], datetime] | None = None,
        logger: logging.Logger | None = None,
        filesystem_resolver: FilesystemResolver | None = None,
    ) -> None:
        self.watcher_repository = watcher_repository
        self.file_repository = file_repository
        self.job_repository = job_repository
        self.event_repository = event_repository
        self.path_policy = path_policy
        self.settings = settings
        self.monotonic = monotonic or time.monotonic
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.logger = logger or configure_structured_logging("watcher", logger_name="stream_lite.watcher")
        self.filesystem_resolver = filesystem_resolver or (lambda container_path: container_path)
        self._snapshots: dict[tuple[str, str], FileSnapshot] = {}
        self.log_records: list[dict[str, object]] = []

    def poll_once(self, watcher_id: UUID | str, correlation_id: UUID | str | None = None) -> PollOnceResult:
        """Scan one active watcher once and enqueue registration events for stable files."""

        resolved_watcher_id = UUID(str(watcher_id))
        resolved_correlation_id = ensure_uuid_str(correlation_id, field_name="correlation_id")
        started = self.monotonic()
        watcher = self.watcher_repository.get_watcher(resolved_watcher_id)
        if watcher is None:
            raise ValueError("watcher not found")

        self._log(
            "watcher.poll_started",
            "Watcher poll started.",
            correlation_id=resolved_correlation_id,
            watcher_id=str(resolved_watcher_id),
        )

        if not watcher.enabled or watcher.lifecycle_state != "ACTIVE":
            result = PollOnceResult(
                watcher_id=resolved_watcher_id,
                skipped_reason="WATCHER_NOT_ACTIVE",
            )
            self._log(
                "watcher.poll_completed",
                "Watcher poll skipped because watcher is not active.",
                correlation_id=resolved_correlation_id,
                watcher_id=str(resolved_watcher_id),
                duration_ms=self._duration_ms(started),
                state_to=watcher.lifecycle_state,
            )
            return result

        sources = [source for source in self.watcher_repository.list_sources(resolved_watcher_id) if source.enabled]
        destinations = [
            destination
            for destination in self.watcher_repository.list_destinations(resolved_watcher_id)
            if destination.enabled
        ]
        scanned_sources = 0
        observed_files = 0
        stabilized_files = 0
        jobs_registered = 0
        duplicates_suppressed = 0
        skipped_sources = 0

        for source in sources:
            source_validation = self.path_policy.validate_path(
                "source",
                source.normalized_path,
                correlation_id=resolved_correlation_id,
            )
            if source_validation.status != "green":
                skipped_sources += 1
                self._log(
                    "watcher.source_skipped",
                    "Source folder skipped by path policy.",
                    level="WARNING",
                    correlation_id=resolved_correlation_id,
                    watcher_id=str(resolved_watcher_id),
                    source_display_path=source_validation.display_path,
                    error_code=source_validation.reason_code,
                    folder_role="source",
                    folder_status="red",
                )
                continue

            matched_destinations = match_source_to_destinations(source, destinations)
            if not matched_destinations:
                skipped_sources += 1
                self._log(
                    "watcher.source_skipped",
                    "Source folder skipped because no destination route matched.",
                    level="WARNING",
                    correlation_id=resolved_correlation_id,
                    watcher_id=str(resolved_watcher_id),
                    source_display_path=source.display_path,
                    error_code="NO_MATCHING_DESTINATION",
                    route_policy=watcher.route_policy,
                    route_tags=list(source.route_tags),
                )
                continue

            scanned_sources += 1
            source_filesystem_path = self.filesystem_resolver(source.normalized_path)
            for child in _iter_direct_file_children(source_filesystem_path):
                observed_files += 1
                source_container_locator = _source_container_locator(source.normalized_path, child.name)
                current_snapshot = capture_file_snapshot(child, observed_at_monotonic=self.monotonic())
                snapshot_key = (str(source.source_folder_id), source_container_locator)
                previous_snapshot = self._snapshots.get(snapshot_key)
                if not is_file_stable(
                    previous_snapshot,
                    current_snapshot,
                    now_monotonic=self.monotonic(),
                    stability_seconds=self.settings.file_stability_seconds,
                ):
                    self._snapshots[snapshot_key] = current_snapshot
                    self._log(
                        "watcher.file_detected",
                        "Candidate file observed but not yet stable.",
                        correlation_id=resolved_correlation_id,
                        watcher_id=str(resolved_watcher_id),
                        source_display_path=_source_display_path(source.display_path, child.name),
                    )
                    continue

                file_sha256 = sha256_file(child)
                source_display_path = _source_display_path(source.display_path, child.name)
                deduplication_key = compute_deduplication_key(
                    resolved_watcher_id,
                    source.source_folder_id,
                    source_display_path,
                    current_snapshot.size_bytes,
                    file_sha256,
                )
                duplicate = check_duplicate(
                    self.file_repository,
                    self.job_repository,
                    deduplication_key=deduplication_key,
                )
                if duplicate.is_duplicate:
                    duplicates_suppressed += 1
                    if duplicate.existing_job_id is not None:
                        record_duplicate_observation(
                            self.file_repository,
                            existing_job_id=duplicate.existing_job_id,
                            watcher_id=resolved_watcher_id,
                            source_folder_id=source.source_folder_id,
                            source_display_path=source_display_path,
                            byte_size=current_snapshot.size_bytes,
                            content_hash=file_sha256,
                            observed_at=self.now(),
                        )
                    self._log(
                        "watcher.duplicate_suppressed",
                        "Duplicate source file suppressed before job registration.",
                        correlation_id=resolved_correlation_id,
                        watcher_id=str(resolved_watcher_id),
                        job_id=None if duplicate.existing_job_id is None else str(duplicate.existing_job_id),
                        source_display_path=source_display_path,
                        error_code="DUPLICATE_SUPPRESSED",
                    )
                    self._snapshots.pop(snapshot_key, None)
                    continue

                observed_at = self.now()
                file_record = self.file_repository.create_file_record(
                    file_id=generate_uuid(),
                    watcher_id=resolved_watcher_id,
                    source_folder_id=source.source_folder_id,
                    source_display_path=source_display_path,
                    source_container_locator=source_container_locator,
                    file_name=child.name,
                    file_extension=child.suffix,
                    size_bytes=current_snapshot.size_bytes,
                    deduplication_key=deduplication_key,
                    first_seen_at=observed_at,
                    stable_at=observed_at,
                    sha256=file_sha256,
                )
                job = self.job_repository.create_job(
                    job_id=generate_uuid(),
                    file_id=file_record.file_id,
                    watcher_id=resolved_watcher_id,
                    source_folder_id=source.source_folder_id,
                    source_display_path=source_display_path,
                    source_container_locator=source_container_locator,
                    source_file_name=child.name,
                    source_extension=child.suffix,
                    source_size_bytes=current_snapshot.size_bytes,
                    source_sha256=file_sha256,
                    detected_at=observed_at,
                    stable_at=observed_at,
                    correlation_id=resolved_correlation_id,
                    state="DETECTED",
                )
                self.job_repository.append_state_history(
                    job_id=job.job_id,
                    previous_state=None,
                    new_state="DETECTED",
                    actor_service="watcher",
                    reason_code="FILE_DETECTED",
                    correlation_id=resolved_correlation_id,
                    transitioned_at=observed_at,
                )
                self.job_repository.update_state(job.job_id, new_state="STABILIZING")
                self.job_repository.append_state_history(
                    job_id=job.job_id,
                    previous_state="DETECTED",
                    new_state="STABILIZING",
                    actor_service="watcher",
                    reason_code="FILE_STABLE",
                    correlation_id=resolved_correlation_id,
                    transitioned_at=observed_at,
                )
                self.job_repository.update_state(job.job_id, new_state="REGISTERED")
                self.job_repository.append_state_history(
                    job_id=job.job_id,
                    previous_state="STABILIZING",
                    new_state="REGISTERED",
                    actor_service="watcher",
                    reason_code="JOB_REGISTERED",
                    correlation_id=resolved_correlation_id,
                    transitioned_at=observed_at,
                )
                self._enqueue_registration_events(
                    job_id=job.job_id,
                    watcher_id=resolved_watcher_id,
                    file_id=file_record.file_id,
                    source_folder_id=source.source_folder_id,
                    source_display_path=source_display_path,
                    size_bytes=current_snapshot.size_bytes,
                    sha256=file_sha256,
                    deduplication_key=deduplication_key,
                    candidate_destination_count=len(matched_destinations),
                    correlation_id=resolved_correlation_id,
                    occurred_at=observed_at,
                )
                stabilized_files += 1
                jobs_registered += 1
                self._snapshots.pop(snapshot_key, None)
                self._log(
                    "watcher.job_registered",
                    "Stable source file registered as a job.",
                    correlation_id=resolved_correlation_id,
                    watcher_id=str(resolved_watcher_id),
                    job_id=str(job.job_id),
                    source_display_path=source_display_path,
                    route_policy=watcher.route_policy,
                    matched_route_tags=list(_matched_tags(source, matched_destinations)),
                )

        _ = build_route_preview(sources, destinations)
        result = PollOnceResult(
            watcher_id=resolved_watcher_id,
            scanned_sources=scanned_sources,
            observed_files=observed_files,
            stabilized_files=stabilized_files,
            jobs_registered=jobs_registered,
            duplicates_suppressed=duplicates_suppressed,
            skipped_sources=skipped_sources,
        )
        self._log(
            "watcher.poll_completed",
            "Watcher poll completed.",
            correlation_id=resolved_correlation_id,
            watcher_id=str(resolved_watcher_id),
            duration_ms=self._duration_ms(started),
        )
        return result

    def _enqueue_registration_events(
        self,
        *,
        job_id: UUID,
        watcher_id: UUID,
        file_id: UUID,
        source_folder_id: UUID,
        source_display_path: str,
        size_bytes: int,
        sha256: str,
        deduplication_key: str,
        candidate_destination_count: int,
        correlation_id: str,
        occurred_at: datetime,
    ) -> None:
        occurred_at_text = _format_rfc3339(occurred_at)
        common = {
            "schema_version": "1.0.0",
            "correlation_id": correlation_id,
            "job_id": job_id,
            "watcher_id": watcher_id,
            "attempt_number": 0,
            "occurred_at": occurred_at_text,
            "producer": "watcher",
        }
        enqueue_event(
            self.event_repository,
            stream_name=LIFECYCLE_STREAM_NAME,
            event_payload={
                **common,
                "event_type": "file.detected",
                "payload": {
                    "file_id": file_id,
                    "source_folder_id": source_folder_id,
                    "source_display_path": source_display_path,
                    "size_bytes": size_bytes,
                    "observed_at": occurred_at_text,
                    "deduplication_key": deduplication_key,
                },
            },
        )
        enqueue_event(
            self.event_repository,
            stream_name=LIFECYCLE_STREAM_NAME,
            event_payload={
                **common,
                "event_type": "file.stable",
                "payload": {
                    "file_id": file_id,
                    "source_display_path": source_display_path,
                    "size_bytes": size_bytes,
                    "sha256": sha256,
                    "stable_after_seconds": float(self.settings.file_stability_seconds),
                },
            },
        )
        enqueue_event(
            self.event_repository,
            stream_name=LIFECYCLE_STREAM_NAME,
            event_payload={
                **common,
                "event_type": "job.registered",
                "payload": {
                    "file_id": file_id,
                    "source_folder_id": source_folder_id,
                    "initial_state": "REGISTERED",
                    "route_policy": "tag_match_all_destinations",
                    "candidate_destination_count": candidate_destination_count,
                },
            },
        )

    def _duration_ms(self, started: float) -> int:
        return max(0, int((self.monotonic() - started) * 1000))

    def _log(self, event: str, message: str, *, correlation_id: str, **fields: object) -> None:
        record = emit_structured_log(
            self.logger,
            service="watcher",
            component="poll_once",
            event=event,
            message=message,
            correlation_id=correlation_id,
            allowed_container_roots=(*self.path_policy.source_roots, *self.path_policy.destination_roots),
            **fields,
        )
        self.log_records.append(record)


def _iter_direct_file_children(source_path: str | Path) -> list[Path]:
    path = Path(source_path)
    if not path.exists() or not path.is_dir():
        return []
    children: list[Path] = []
    with os.scandir(path) as entries:
        for entry in entries:
            if not entry.is_file(follow_symlinks=False):
                continue
            children.append(Path(entry.path))
    return sorted(children, key=lambda item: item.name)


def _source_display_path(source_display_path: str, file_name: str) -> str:
    return f"{source_display_path.rstrip('/')}/{file_name}"


def _source_container_locator(source_container_path: str, file_name: str) -> str:
    return f"{source_container_path.rstrip('/')}/{file_name}"


def _matched_tags(source: object, destinations: list[object]) -> tuple[str, ...]:
    source_tags = set(getattr(source, "route_tags", ()))
    matched: set[str] = set()
    for destination in destinations:
        matched.update(source_tags & set(getattr(destination, "route_tags", ())))
    return tuple(sorted(matched))


def _format_rfc3339(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


__all__ = ["PollOnceResult", "WatcherService"]
