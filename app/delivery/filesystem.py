"""Filesystem delivery helpers for WP09-A."""

from __future__ import annotations

import errno
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Callable, Literal, Mapping, Sequence
from uuid import UUID

from app import ensure_uuid_str
from app.artifacts import OutputManifest
from app.config.path_policy import PathPolicy

DESTINATION_NOT_ALLOWLISTED = "DESTINATION_NOT_ALLOWLISTED"
DESTINATION_NOT_FOUND = "DESTINATION_NOT_FOUND"
DESTINATION_NOT_WRITABLE = "DESTINATION_NOT_WRITABLE"
FINALIZE_FAILED = "FINALIZE_FAILED"
FINALIZE_UNSUPPORTED = "FINALIZE_UNSUPPORTED"
SOURCE_TRANSFER_FAILED = "SOURCE_TRANSFER_FAILED"

_WINDOWS_DRIVE_PATTERN = re.compile(r"^[A-Za-z]:[\\/]")


@dataclass(frozen=True, slots=True)
class DeliveryCopyResult:
    status: Literal["delivered", "failed"]
    finalized_locator: str | None
    finalized_display_path: str | None
    checksum_sha256: str | None
    bytes_written: int
    reason_code: str | None
    retryable: bool
    operator_message: str


def copy_output_to_destination(
    *,
    source_output_locator: str,
    destination_root_locator: str,
    watcher_id: UUID,
    job_id: UUID,
    as_of_date: date,
    filesystem_resolver: Callable[[str], Path] = Path,
    path_policy: PathPolicy | None = None,
) -> DeliveryCopyResult:
    """Copy one processed output into a job-scoped destination path."""

    normalized_source_locator = _normalize_container_locator(source_output_locator)
    normalized_destination_root = _normalize_container_locator(destination_root_locator)
    destination_display_root = normalized_destination_root

    if path_policy is not None:
        source_validation = path_policy.validate_path("source", normalized_source_locator)
        if source_validation.status != "green":
            return DeliveryCopyResult(
                status="failed",
                finalized_locator=None,
                finalized_display_path=None,
                checksum_sha256=None,
                bytes_written=0,
                reason_code=SOURCE_TRANSFER_FAILED,
                retryable=True,
                operator_message=source_validation.message,
            )
        normalized_source_locator = _normalize_container_locator(source_validation.normalized_path)

        validation = path_policy.validate_path("destination", normalized_destination_root)
        if validation.status != "green":
            return DeliveryCopyResult(
                status="failed",
                finalized_locator=None,
                finalized_display_path=None,
                checksum_sha256=None,
                bytes_written=0,
                reason_code=DESTINATION_NOT_ALLOWLISTED,
                retryable=False,
                operator_message=validation.message,
            )
        normalized_destination_root = _normalize_container_locator(validation.normalized_path)
        destination_display_root = validation.display_path

    source_path = Path(filesystem_resolver(normalized_source_locator))
    destination_root_path = Path(filesystem_resolver(normalized_destination_root))

    if not source_path.is_file():
        return DeliveryCopyResult(
            status="failed",
            finalized_locator=None,
            finalized_display_path=None,
            checksum_sha256=None,
            bytes_written=0,
            reason_code=SOURCE_TRANSFER_FAILED,
            retryable=True,
            operator_message="Source output could not be read for delivery.",
        )

    if not destination_root_path.is_dir():
        return DeliveryCopyResult(
            status="failed",
            finalized_locator=None,
            finalized_display_path=None,
            checksum_sha256=None,
            bytes_written=0,
            reason_code=DESTINATION_NOT_FOUND,
            retryable=True,
            operator_message=f"Destination root {destination_display_root} was not found.",
        )

    finalized_locator = _build_finalized_locator(
        destination_root_locator=normalized_destination_root,
        watcher_id=watcher_id,
        job_id=job_id,
        as_of_date=as_of_date,
        source_output_locator=normalized_source_locator,
    )
    finalized_display_path = _build_display_path(
        destination_display_root,
        watcher_id=watcher_id,
        job_id=job_id,
        as_of_date=as_of_date,
        source_output_locator=normalized_source_locator,
    )

    finalized_path = Path(filesystem_resolver(finalized_locator))
    temporary_path = finalized_path.with_name(f".{finalized_path.name}.tmp")

    try:
        finalized_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return _failed_copy(
            reason_code=DESTINATION_NOT_WRITABLE,
            retryable=True,
            operator_message=f"Destination path {finalized_display_path} is not writable.",
        )

    bytes_written = 0
    copied_digest = hashlib.sha256()

    try:
        source_handle = source_path.open("rb")
    except OSError:
        return _failed_copy(
            reason_code=SOURCE_TRANSFER_FAILED,
            retryable=True,
            operator_message="Source output could not be read for delivery.",
            bytes_written=bytes_written,
        )

    try:
        temporary_handle = temporary_path.open("wb")
    except OSError:
        source_handle.close()
        return _failed_copy(
            reason_code=DESTINATION_NOT_WRITABLE,
            retryable=True,
            operator_message=f"Destination path {finalized_display_path} is not writable.",
            bytes_written=bytes_written,
        )

    with source_handle, temporary_handle:
        while True:
            try:
                chunk = source_handle.read(1024 * 1024)
            except OSError:
                return _failed_copy(
                    reason_code=SOURCE_TRANSFER_FAILED,
                    retryable=True,
                    operator_message="Source output could not be read for delivery.",
                    bytes_written=bytes_written,
                )
            if not chunk:
                break
            try:
                temporary_handle.write(chunk)
            except OSError:
                return _failed_copy(
                    reason_code=DESTINATION_NOT_WRITABLE,
                    retryable=True,
                    operator_message=f"Destination path {finalized_display_path} is not writable.",
                    bytes_written=bytes_written,
                )
            copied_digest.update(chunk)
            bytes_written += len(chunk)

    try:
        verified_digest, verified_bytes = _compute_sha256_and_size(temporary_path)
    except OSError:
        return _failed_copy(
            reason_code=SOURCE_TRANSFER_FAILED,
            retryable=True,
            operator_message="Staged output could not be verified after copy.",
            bytes_written=bytes_written,
        )

    if verified_bytes != bytes_written or verified_digest != copied_digest.hexdigest():
        return _failed_copy(
            reason_code=FINALIZE_FAILED,
            retryable=True,
            operator_message=f"Failed to verify staged output for {finalized_display_path}.",
            bytes_written=verified_bytes,
        )

    try:
        temporary_path.replace(finalized_path)
    except OSError as exc:
        if getattr(exc, "errno", None) == errno.EXDEV:
            return _failed_copy(
                reason_code=FINALIZE_UNSUPPORTED,
                retryable=False,
                operator_message=f"Atomic finalize is unsupported for {finalized_display_path}.",
                bytes_written=verified_bytes,
            )
        return _failed_copy(
            reason_code=FINALIZE_FAILED,
            retryable=True,
            operator_message=f"Atomic finalize failed for {finalized_display_path}.",
            bytes_written=verified_bytes,
        )

    return DeliveryCopyResult(
        status="delivered",
        finalized_locator=finalized_locator,
        finalized_display_path=finalized_display_path,
        checksum_sha256=verified_digest,
        bytes_written=verified_bytes,
        reason_code=None,
        retryable=False,
        operator_message=f"Delivered output to {finalized_display_path}.",
    )


def build_destination_outcome(
    *,
    destination_folder_id: UUID | str,
    destination_display_path: str,
    matched_route_tags: Sequence[str],
    status: Literal["delivered", "failed", "skipped"],
    finalized_locator: str | None = None,
    checksum_sha256: str | None = None,
    bytes_written: int | None = None,
    reason_code: str | None = None,
    retryable: bool | None = None,
) -> dict[str, object]:
    """Build a WP09-A destination outcome payload."""

    if status in {"failed", "skipped"} and (reason_code is None or retryable is None):
        raise ValueError("Failed and skipped outcomes require reason_code and retryable.")

    return {
        "destination_folder_id": ensure_uuid_str(
            destination_folder_id,
            field_name="destination_folder_id",
        ),
        "destination_display_path": destination_display_path,
        "matched_route_tags": list(matched_route_tags),
        "status": status,
        "finalized_locator": finalized_locator,
        "checksum_sha256": checksum_sha256,
        "bytes_written": bytes_written,
        "reason_code": reason_code,
        "retryable": retryable,
    }


def build_output_manifest(
    *,
    existing_manifest: OutputManifest | Mapping[str, object],
    destination_outcomes: Sequence[Mapping[str, object]],
    status: Literal["processed", "delivered", "completed_with_delivery_errors", "failed"],
    completed_at: str | None = None,
    created_at: str | None = None,
    correlation_id: str | UUID | None = None,
    duration_seconds: int | None = None,
) -> OutputManifest:
    """Update a processed manifest with delivery outcomes and terminal status."""

    if isinstance(existing_manifest, OutputManifest):
        payload = existing_manifest.model_dump(mode="json")
    else:
        payload = dict(existing_manifest)

    payload["destination_outcomes"] = [dict(outcome) for outcome in destination_outcomes]
    payload["status"] = status
    if completed_at is not None:
        payload["completed_at"] = completed_at
    if created_at is not None:
        payload["created_at"] = created_at
    if correlation_id is not None:
        payload["correlation_id"] = str(correlation_id)
    if duration_seconds is not None:
        payload["duration_seconds"] = int(duration_seconds)
    return OutputManifest.model_validate(payload)


class OutputManifestWriter:
    """Write an output manifest through a container-locator resolver."""

    def __init__(self, *, filesystem_resolver: Callable[[str], Path] = Path) -> None:
        self._filesystem_resolver = filesystem_resolver

    def write_manifest(
        self,
        *,
        manifest_locator: str,
        manifest: OutputManifest | Mapping[str, object],
    ) -> OutputManifest:
        manifest_model = (
            manifest
            if isinstance(manifest, OutputManifest)
            else OutputManifest.model_validate(manifest)
        )
        normalized_manifest_locator = _normalize_container_locator(manifest_locator)
        local_path = Path(self._filesystem_resolver(normalized_manifest_locator))
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_text(
            json.dumps(manifest_model.model_dump(mode="json"), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return manifest_model


def _failed_copy(
    *,
    reason_code: str,
    retryable: bool,
    operator_message: str,
    bytes_written: int = 0,
) -> DeliveryCopyResult:
    return DeliveryCopyResult(
        status="failed",
        finalized_locator=None,
        finalized_display_path=None,
        checksum_sha256=None,
        bytes_written=bytes_written,
        reason_code=reason_code,
        retryable=retryable,
        operator_message=operator_message,
    )


def _build_finalized_locator(
    *,
    destination_root_locator: str,
    watcher_id: UUID,
    job_id: UUID,
    as_of_date: date,
    source_output_locator: str,
) -> str:
    file_name = _output_file_name(source_output_locator)
    parts = (
        f"watcher_id={watcher_id}",
        f"date={as_of_date.isoformat()}",
        f"job_id={job_id}",
        file_name,
    )
    return _join_locator(destination_root_locator, *parts)


def _build_display_path(
    destination_display_root: str,
    *,
    watcher_id: UUID,
    job_id: UUID,
    as_of_date: date,
    source_output_locator: str,
) -> str:
    file_name = _output_file_name(source_output_locator)
    parts = (
        f"watcher_id={watcher_id}",
        f"date={as_of_date.isoformat()}",
        f"job_id={job_id}",
        file_name,
    )
    return _join_locator(destination_display_root, *parts)


def _output_file_name(source_output_locator: str) -> str:
    suffix = PurePosixPath(source_output_locator).suffix
    if not suffix:
        return "output"
    return f"output{suffix}"


def _join_locator(root: str, *parts: str) -> str:
    normalized_root = root.rstrip("/")
    remainder = "/".join(part.strip("/") for part in parts)
    return f"{normalized_root}/{remainder}" if normalized_root else f"/{remainder}"


def _normalize_container_locator(locator: str) -> str:
    value = str(locator).strip()
    if not value:
        raise ValueError("Container locators must not be empty.")
    if value.lower().startswith("file://") or "\\" in value or _WINDOWS_DRIVE_PATTERN.match(value):
        raise ValueError("Container locators must use absolute POSIX paths.")
    if not value.startswith("/"):
        raise ValueError("Container locators must use absolute POSIX paths.")

    normalized_parts: list[str] = []
    for part in value.split("/"):
        if part in {"", "."}:
            continue
        if part == "..":
            raise ValueError("Container locators must not contain traversal segments.")
        normalized_parts.append(part)
    return "/" + "/".join(normalized_parts) if normalized_parts else "/"


def _compute_sha256_and_size(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


__all__ = [
    "DESTINATION_NOT_ALLOWLISTED",
    "DESTINATION_NOT_FOUND",
    "DESTINATION_NOT_WRITABLE",
    "DeliveryCopyResult",
    "FINALIZE_FAILED",
    "FINALIZE_UNSUPPORTED",
    "OutputManifestWriter",
    "SOURCE_TRANSFER_FAILED",
    "build_destination_outcome",
    "build_output_manifest",
    "copy_output_to_destination",
]
