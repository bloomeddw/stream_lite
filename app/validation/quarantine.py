"""Copy-only quarantine handling for invalid WP-07 files."""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from uuid import UUID

from app.artifacts import QuarantineRecord
from app.config.path_policy import PathPolicy
from app.config.settings import StreamLiteSettings
from app.observability.logging import configure_structured_logging, emit_structured_log

FilesystemResolver = Callable[[str], str | Path]


@dataclass(frozen=True, slots=True)
class QuarantineResult:
    quarantine_locator: str
    quarantine_display_path: str
    artifact_locator: str
    copy_status: str
    checksum_sha256: str | None
    copied_size_bytes: int | None
    created_at: datetime
    primary_reason_code: str
    artifact_payload: dict[str, object]


class QuarantineService:
    """Copy invalid files into the quarantine root without mutating the source."""

    def __init__(
        self,
        *,
        settings: StreamLiteSettings,
        path_policy: PathPolicy,
        filesystem_resolver: FilesystemResolver | None = None,
        now: Callable[[], datetime] | None = None,
        logger: logging.Logger | None = None,
        log_records: list[dict[str, object]] | None = None,
    ) -> None:
        self.settings = settings
        self.path_policy = path_policy
        self.filesystem_resolver = filesystem_resolver or (lambda container_path: container_path)
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.logger = logger or configure_structured_logging("validator", logger_name="stream_lite.validator")
        self.log_records = log_records if log_records is not None else []

    def quarantine_file(
        self,
        *,
        job_id: UUID | str,
        watcher_id: UUID | str,
        source_container_locator: str,
        source_display_path: str,
        source_file_name: str,
        source_sha256: str,
        reason_codes: list[str] | tuple[str, ...],
        operator_message: str,
        correlation_id: str,
        schema_version: str = "1.0.0",
    ) -> QuarantineResult:
        if not reason_codes:
            raise ValueError("reason_codes must not be empty")

        created_at = self.now()
        date_text = created_at.date().isoformat()
        job_id_text = str(job_id)
        watcher_id_text = str(watcher_id)
        directory_locator = (
            f"{self.settings.quarantine_root.rstrip('/')}/"
            f"watcher_id={watcher_id_text}/date={date_text}/job_id={job_id_text}"
        )
        quarantine_locator = f"{directory_locator}/{source_file_name}"
        artifact_locator = f"{directory_locator}/quarantine_record.json"
        quarantine_display_path = f"/watcher_id={watcher_id_text}/date={date_text}/job_id={job_id_text}/{source_file_name}"
        primary_reason_code = str(reason_codes[0])

        local_directory = Path(self.filesystem_resolver(directory_locator))
        local_artifact_path = Path(self.filesystem_resolver(artifact_locator))
        local_target_path = Path(self.filesystem_resolver(quarantine_locator))
        copied_size_bytes: int | None = None
        checksum_sha256: str | None = None
        copy_status = "copied"

        try:
            local_directory.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise RuntimeError("quarantine directory could not be created") from exc

        source_path_result = self.path_policy.validate_path(
            "source",
            source_container_locator,
            correlation_id=correlation_id,
        )
        if source_path_result.status != "green":
            copy_status = "not_copied_security_block"
            self._log(
                "quarantine.copy_failed",
                "Quarantine copy blocked by source path policy.",
                correlation_id=correlation_id,
                watcher_id=watcher_id_text,
                error_code="PATH_POLICY_VIOLATION",
                job_id=job_id_text,
                source_display_path=source_display_path,
                quarantine_locator=quarantine_locator,
            )
        else:
            local_source_path = Path(self.filesystem_resolver(source_path_result.normalized_path))
            self._log(
                "quarantine.copy_started",
                "Quarantine copy started.",
                correlation_id=correlation_id,
                watcher_id=watcher_id_text,
                job_id=job_id_text,
                source_display_path=source_display_path,
                quarantine_locator=quarantine_locator,
            )
            try:
                shutil.copyfile(local_source_path, local_target_path)
                copied_size_bytes = local_target_path.stat().st_size
                checksum_sha256 = _sha256_file(local_target_path)
                self._log(
                    "quarantine.copy_completed",
                    "Quarantine copy completed.",
                    correlation_id=correlation_id,
                    watcher_id=watcher_id_text,
                    job_id=job_id_text,
                    source_display_path=source_display_path,
                    quarantine_locator=quarantine_locator,
                )
            except OSError:
                copy_status = "copy_failed"
                self._log(
                    "quarantine.copy_failed",
                    "Quarantine copy failed.",
                    correlation_id=correlation_id,
                    watcher_id=watcher_id_text,
                    job_id=job_id_text,
                    source_display_path=source_display_path,
                    quarantine_locator=quarantine_locator,
                    error_code=primary_reason_code,
                )

        artifact_payload = QuarantineRecord.model_validate(
            {
                "schema_version": schema_version,
                "job_id": job_id_text,
                "watcher_id": watcher_id_text,
                "source_display_path": source_display_path,
                "source_sha256": source_sha256,
                "reason_code": primary_reason_code,
                "operator_message": operator_message,
                "quarantine_locator": quarantine_locator,
                "quarantine_display_path": quarantine_display_path,
                "copy_status": copy_status,
                "created_at": _format_rfc3339(created_at),
                "correlation_id": correlation_id,
            }
        ).model_dump(mode="json")
        local_artifact_path.write_text(json.dumps(artifact_payload, indent=2), encoding="utf-8")

        return QuarantineResult(
            quarantine_locator=quarantine_locator,
            quarantine_display_path=quarantine_display_path,
            artifact_locator=artifact_locator,
            copy_status=copy_status,
            checksum_sha256=checksum_sha256,
            copied_size_bytes=copied_size_bytes,
            created_at=created_at,
            primary_reason_code=primary_reason_code,
            artifact_payload=artifact_payload,
        )

    def _log(self, event: str, message: str, *, correlation_id: str, **fields: object) -> None:
        record = emit_structured_log(
            self.logger,
            service="validator",
            component="quarantine",
            event=event,
            message=message,
            correlation_id=correlation_id,
            allowed_container_roots=(
                self.settings.watch_root,
                self.settings.output_root,
                self.settings.quarantine_root,
            ),
            **fields,
        )
        self.log_records.append(record)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(8192)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _format_rfc3339(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


__all__ = ["QuarantineResult", "QuarantineService"]
