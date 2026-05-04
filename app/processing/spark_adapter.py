"""Deterministic Spark-profile processing adapter for WP-08."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Literal
from uuid import UUID

from pydantic import ValidationError

from app import ensure_uuid_str, generate_uuid
from app.artifacts import OutputManifest, ProcessingSummary

FilesystemResolver = Callable[[str], str | Path]

STATUS_PROCESSED = "processed"
STATUS_FAILED = "failed"

ERROR_INPUT_UNAVAILABLE = "PROCESSING_INPUT_UNAVAILABLE"
ERROR_INPUT_INVALID = "PROCESSING_INPUT_INVALID"
ERROR_UNSUPPORTED_EXTENSION = "UNSUPPORTED_EXTENSION_REACHED_PROCESSING"
ERROR_OUTPUT_UNAVAILABLE = "PROCESSING_OUTPUT_UNAVAILABLE"
ERROR_ARTIFACT_INVALID = "PROCESSING_ARTIFACT_INVALID"


@dataclass(frozen=True, slots=True)
class ProcessingAdapterInput:
    job_id: UUID | str
    watcher_id: UUID | str
    correlation_id: UUID | str
    input_locator: str
    source_file_name: str
    source_extension: str
    source_sha256: str
    started_at: datetime
    source_display_path: str | None = None


@dataclass(frozen=True, slots=True)
class ProcessingAdapterResult:
    status: Literal["processed", "failed"]
    engine: str
    engine_version: str
    input_locator: str
    output_locator: str | None
    summary_locator: str | None
    manifest_locator: str | None
    output_manifest_id: UUID | None
    row_count: int | None
    record_count: int | None
    byte_count: int | None
    bytes_written: int | None
    started_at: datetime
    completed_at: datetime
    duration_seconds: int
    error_code: str | None
    retryable: bool
    operator_message: str


class SparkDemoAdapter:
    """Run a deterministic local transformation while presenting a Spark profile."""

    engine = "spark"

    def __init__(
        self,
        *,
        processing_root: str = "/stream-lite/processing",
        filesystem_resolver: FilesystemResolver | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.processing_root = _normalize_container_root(processing_root)
        self.filesystem_resolver = filesystem_resolver or (lambda locator: locator)
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.engine_version = _detect_engine_version()

    def run_demo_transform(self, adapter_input: ProcessingAdapterInput) -> ProcessingAdapterResult:
        job_id_text = str(adapter_input.job_id)
        correlation_id_text = ensure_uuid_str(adapter_input.correlation_id, field_name="correlation_id")
        started_at = _as_utc(adapter_input.started_at)
        display_name = adapter_input.source_display_path or adapter_input.source_file_name or adapter_input.input_locator

        job_root_locator = f"{self.processing_root.rstrip('/')}/job_id={job_id_text}"
        output_locator = f"{job_root_locator}/output/{adapter_input.source_file_name}"
        summary_locator = f"{job_root_locator}/processing_summary.json"
        manifest_locator = f"{job_root_locator}/output_manifest.json"
        output_manifest_id = generate_uuid()

        input_path = Path(self.filesystem_resolver(adapter_input.input_locator))
        output_path = Path(self.filesystem_resolver(output_locator))
        summary_path = Path(self.filesystem_resolver(summary_locator))
        manifest_path = Path(self.filesystem_resolver(manifest_locator))

        try:
            byte_count = _source_byte_count(input_path)
        except OSError:
            return self._failure_result(
                input_locator=adapter_input.input_locator,
                output_locator=output_locator,
                summary_locator=summary_locator,
                manifest_locator=manifest_locator,
                started_at=started_at,
                completed_at=self.clock(),
                error_code=ERROR_INPUT_UNAVAILABLE,
                retryable=True,
                operator_message=f"Processing input {display_name} is unavailable.",
            )

        extension = (adapter_input.source_extension or Path(adapter_input.source_file_name).suffix).lower()
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            summary_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            return self._failure_result(
                input_locator=adapter_input.input_locator,
                output_locator=output_locator,
                summary_locator=summary_locator,
                manifest_locator=manifest_locator,
                started_at=started_at,
                completed_at=self.clock(),
                error_code=ERROR_OUTPUT_UNAVAILABLE,
                retryable=True,
                operator_message=f"Processing staging for {display_name} is unavailable.",
            )

        try:
            if extension == ".csv":
                row_count, record_count = self._process_csv(input_path, output_path)
            elif extension == ".json":
                row_count, record_count = self._process_json(input_path, output_path)
            elif extension == ".txt":
                row_count, record_count = self._process_text(input_path, output_path)
            else:
                return self._failure_result(
                    input_locator=adapter_input.input_locator,
                    output_locator=output_locator,
                    summary_locator=summary_locator,
                    manifest_locator=manifest_locator,
                    started_at=started_at,
                    completed_at=self.clock(),
                    error_code=ERROR_UNSUPPORTED_EXTENSION,
                    retryable=False,
                    operator_message=f"Processing does not support {adapter_input.source_file_name} for WP-08.",
                )
        except OSError:
            return self._failure_result(
                input_locator=adapter_input.input_locator,
                output_locator=output_locator,
                summary_locator=summary_locator,
                manifest_locator=manifest_locator,
                started_at=started_at,
                completed_at=self.clock(),
                error_code=ERROR_INPUT_UNAVAILABLE,
                retryable=True,
                operator_message=f"Processing input {display_name} is unavailable.",
            )
        except (UnicodeDecodeError, ValueError, csv.Error, json.JSONDecodeError):
            return self._failure_result(
                input_locator=adapter_input.input_locator,
                output_locator=output_locator,
                summary_locator=summary_locator,
                manifest_locator=manifest_locator,
                started_at=started_at,
                completed_at=self.clock(),
                error_code=ERROR_INPUT_INVALID,
                retryable=False,
                operator_message=f"Processing input {display_name} is invalid.",
            )

        completed_at = self.clock()
        duration_seconds = _duration_seconds(started_at, completed_at)

        try:
            bytes_written = output_path.stat().st_size
        except OSError:
            return self._failure_result(
                input_locator=adapter_input.input_locator,
                output_locator=output_locator,
                summary_locator=summary_locator,
                manifest_locator=manifest_locator,
                started_at=started_at,
                completed_at=completed_at,
                error_code=ERROR_OUTPUT_UNAVAILABLE,
                retryable=True,
                operator_message=f"Processing output for {display_name} is unavailable.",
            )

        try:
            summary_payload = ProcessingSummary.model_validate(
                {
                    "schema_version": "1.0.0",
                    "job_id": job_id_text,
                    "engine": self.engine,
                    "engine_version": self.engine_version,
                    "input_locator": adapter_input.input_locator,
                    "output_locator": output_locator,
                    "source_sha256": adapter_input.source_sha256,
                    "processor_version": self.engine_version,
                    "row_count": row_count,
                    "record_count": record_count,
                    "byte_count": byte_count,
                    "started_at": _format_rfc3339(started_at),
                    "completed_at": _format_rfc3339(completed_at),
                    "duration_seconds": duration_seconds,
                    "status": STATUS_PROCESSED,
                    "correlation_id": correlation_id_text,
                }
            ).model_dump(mode="json")
            manifest_payload = OutputManifest.model_validate(
                {
                    "schema_version": "1.0.0",
                    "job_id": job_id_text,
                    "watcher_id": str(adapter_input.watcher_id),
                    "source_sha256": adapter_input.source_sha256,
                    "processor_version": self.engine_version,
                    "processing_summary_locator": summary_locator,
                    "produced_output_locators": [output_locator],
                    "started_at": _format_rfc3339(started_at),
                    "completed_at": _format_rfc3339(completed_at),
                    "duration_seconds": duration_seconds,
                    "destination_outcomes": [],
                    "status": STATUS_PROCESSED,
                    "created_at": _format_rfc3339(completed_at),
                    "correlation_id": correlation_id_text,
                }
            ).model_dump(mode="json")
        except ValidationError:
            return self._failure_result(
                input_locator=adapter_input.input_locator,
                output_locator=output_locator,
                summary_locator=summary_locator,
                manifest_locator=manifest_locator,
                started_at=started_at,
                completed_at=completed_at,
                error_code=ERROR_ARTIFACT_INVALID,
                retryable=False,
                operator_message=f"Processing artifacts for {display_name} did not match the WP-08 contract.",
            )

        try:
            summary_path.write_text(json.dumps(summary_payload, indent=2, sort_keys=True), encoding="utf-8")
            manifest_path.write_text(json.dumps(manifest_payload, indent=2, sort_keys=True), encoding="utf-8")
        except OSError:
            return self._failure_result(
                input_locator=adapter_input.input_locator,
                output_locator=output_locator,
                summary_locator=summary_locator,
                manifest_locator=manifest_locator,
                started_at=started_at,
                completed_at=completed_at,
                error_code=ERROR_OUTPUT_UNAVAILABLE,
                retryable=True,
                operator_message=f"Processing output for {display_name} could not be persisted.",
            )

        return ProcessingAdapterResult(
            status=STATUS_PROCESSED,
            engine=self.engine,
            engine_version=self.engine_version,
            input_locator=adapter_input.input_locator,
            output_locator=output_locator,
            summary_locator=summary_locator,
            manifest_locator=manifest_locator,
            output_manifest_id=output_manifest_id,
            row_count=row_count,
            record_count=record_count,
            byte_count=byte_count,
            bytes_written=bytes_written,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration_seconds,
            error_code=None,
            retryable=False,
            operator_message=f"Processing completed for {display_name}.",
        )

    process = run_demo_transform

    def _process_csv(self, input_path: Path, output_path: Path) -> tuple[int, int]:
        with input_path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.reader(handle, delimiter=",", strict=True))
        with output_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, lineterminator="\n")
            writer.writerows(rows)
        row_count = max(len(rows) - 1, 0)
        return row_count, row_count

    def _process_json(self, input_path: Path, output_path: Path) -> tuple[int | None, int]:
        with input_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, (dict, list)):
            raise ValueError("json payload must be an object or array")
        rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        output_path.write_text(rendered, encoding="utf-8")
        record_count = len(payload) if isinstance(payload, list) else 1
        return None, record_count

    def _process_text(self, input_path: Path, output_path: Path) -> tuple[int, int]:
        text = input_path.read_text(encoding="utf-8")
        output_path.write_text(text, encoding="utf-8")
        row_count = len(text.splitlines()) if text else 0
        return row_count, row_count

    def _failure_result(
        self,
        *,
        input_locator: str,
        output_locator: str,
        summary_locator: str,
        manifest_locator: str,
        started_at: datetime,
        completed_at: datetime,
        error_code: str,
        retryable: bool,
        operator_message: str,
    ) -> ProcessingAdapterResult:
        return ProcessingAdapterResult(
            status=STATUS_FAILED,
            engine=self.engine,
            engine_version=self.engine_version,
            input_locator=input_locator,
            output_locator=output_locator,
            summary_locator=summary_locator,
            manifest_locator=manifest_locator,
            output_manifest_id=None,
            row_count=None,
            record_count=None,
            byte_count=None,
            bytes_written=None,
            started_at=_as_utc(started_at),
            completed_at=_as_utc(completed_at),
            duration_seconds=_duration_seconds(started_at, completed_at),
            error_code=error_code,
            retryable=retryable,
            operator_message=operator_message,
        )


def _source_byte_count(path: Path) -> int:
    stat_result = path.stat()
    if not path.is_file():
        raise OSError("input path is not a file")
    return int(stat_result.st_size)


def _normalize_container_root(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("processing_root must not be empty")
    if normalized.lower().startswith("file://"):
        raise ValueError("processing_root must not use file://")
    if "\\" in normalized or ":" in normalized.split("/", 1)[0]:
        raise ValueError("processing_root must use an absolute container path")
    if not normalized.startswith("/"):
        raise ValueError("processing_root must use an absolute container path")
    if any(segment == ".." for segment in normalized.split("/")):
        raise ValueError("processing_root must not contain traversal segments")
    parts = [segment for segment in normalized.split("/") if segment not in {"", "."}]
    return "/" + "/".join(parts) if parts else "/"


def _detect_engine_version() -> str:
    try:
        import pyspark  # type: ignore
    except Exception:
        return "unknown"
    version = getattr(pyspark, "__version__", "")
    return version if isinstance(version, str) and version else "unknown"


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _format_rfc3339(value: datetime) -> str:
    return _as_utc(value).isoformat().replace("+00:00", "Z")


def _duration_seconds(started_at: datetime, completed_at: datetime) -> int:
    delta = (_as_utc(completed_at) - _as_utc(started_at)).total_seconds()
    return max(0, int(delta))


__all__ = [
    "ProcessingAdapterInput",
    "ProcessingAdapterResult",
    "SparkDemoAdapter",
]
