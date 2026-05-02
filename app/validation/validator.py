"""Deterministic rule-based file validation for WP-07."""

from __future__ import annotations

import csv
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Literal

from app.config.path_policy import PathPolicy, safe_display_path
from app.config.settings import StreamLiteSettings

FilesystemResolver = Callable[[str], str | Path]

RULE_PATH_ALLOWLISTED = "PATH_ALLOWLISTED"
RULE_FILE_EXISTS = "FILE_EXISTS"
RULE_FILE_READABLE = "FILE_READABLE"
RULE_FILE_SIZE_LIMIT = "FILE_SIZE_LIMIT"
RULE_EXTENSION_ALLOWED = "EXTENSION_ALLOWED"
RULE_FILE_NON_EMPTY = "FILE_NON_EMPTY"
RULE_STRUCTURED_FORMAT = "STRUCTURED_FORMAT"

REASON_FILE_NOT_FOUND = "FILE_NOT_FOUND"
REASON_FILE_NOT_READABLE = "FILE_NOT_READABLE"
REASON_FILE_EMPTY = "FILE_EMPTY"
REASON_FILE_TOO_LARGE = "FILE_TOO_LARGE"
REASON_EXTENSION_NOT_ALLOWED = "EXTENSION_NOT_ALLOWED"
REASON_SCHEMA_INVALID = "SCHEMA_INVALID"
REASON_PATH_POLICY_VIOLATION = "PATH_POLICY_VIOLATION"

ALLOWED_EXTENSIONS = (".csv", ".json", ".txt")


@dataclass(frozen=True, slots=True)
class ValidationResult:
    status: Literal["valid", "invalid"]
    reason_codes: tuple[str, ...]
    operator_message: str
    rules_applied: tuple[str, ...]
    duration_seconds: float

    @property
    def is_valid(self) -> bool:
        return self.status == "valid"

    @property
    def primary_reason_code(self) -> str | None:
        if not self.reason_codes:
            return None
        return self.reason_codes[0]


class FileValidator:
    """Apply the documented validation rules without mutating the source file."""

    def __init__(
        self,
        *,
        path_policy: PathPolicy,
        settings: StreamLiteSettings,
        filesystem_resolver: FilesystemResolver | None = None,
        monotonic: Callable[[], float] | None = None,
        allowed_extensions: Iterable[str] | None = None,
    ) -> None:
        self.path_policy = path_policy
        self.settings = settings
        self.filesystem_resolver = filesystem_resolver or (lambda container_path: container_path)
        self.monotonic = monotonic or time.monotonic
        self.max_file_size_bytes = int(settings.max_file_size_mb) * 1024 * 1024
        self.allowed_extensions = tuple(
            dict.fromkeys(
                extension.strip().lower()
                for extension in (allowed_extensions or ALLOWED_EXTENSIONS)
                if extension and extension.strip()
            )
        )
        if not self.allowed_extensions:
            raise ValueError("allowed_extensions must contain at least one extension")

    def validate_file(
        self,
        source_container_locator: str,
        *,
        source_display_path: str | None = None,
        correlation_id: str | None = None,
    ) -> ValidationResult:
        started = self.monotonic()
        safe_display = source_display_path or safe_display_path(
            source_container_locator,
            allowed_roots=self.path_policy.source_roots,
        )
        rules_applied: list[str] = []
        reason_codes: list[str] = []

        path_result = self.path_policy.validate_path(
            "source",
            source_container_locator,
            correlation_id=correlation_id,
        )
        rules_applied.append(RULE_PATH_ALLOWLISTED)
        if path_result.status != "green":
            return self._build_result(
                status="invalid",
                reason_codes=(REASON_PATH_POLICY_VIOLATION,),
                operator_message=path_result.message,
                rules_applied=rules_applied,
                started=started,
            )

        safe_display = source_display_path or path_result.display_path
        local_path = Path(self.filesystem_resolver(path_result.normalized_path))

        rules_applied.append(RULE_FILE_EXISTS)
        try:
            stat_result = local_path.stat()
        except FileNotFoundError:
            return self._build_result(
                status="invalid",
                reason_codes=(REASON_FILE_NOT_FOUND,),
                operator_message=_operator_message(REASON_FILE_NOT_FOUND, safe_display),
                rules_applied=rules_applied,
                started=started,
            )
        except OSError:
            return self._build_result(
                status="invalid",
                reason_codes=(REASON_FILE_NOT_READABLE,),
                operator_message=_operator_message(REASON_FILE_NOT_READABLE, safe_display),
                rules_applied=rules_applied,
                started=started,
            )
        if not local_path.is_file():
            return self._build_result(
                status="invalid",
                reason_codes=(REASON_FILE_NOT_FOUND,),
                operator_message=_operator_message(REASON_FILE_NOT_FOUND, safe_display),
                rules_applied=rules_applied,
                started=started,
            )

        rules_applied.append(RULE_FILE_READABLE)
        try:
            with local_path.open("rb") as handle:
                handle.read(1)
        except OSError:
            return self._build_result(
                status="invalid",
                reason_codes=(REASON_FILE_NOT_READABLE,),
                operator_message=_operator_message(REASON_FILE_NOT_READABLE, safe_display),
                rules_applied=rules_applied,
                started=started,
            )

        rules_applied.append(RULE_FILE_SIZE_LIMIT)
        if stat_result.st_size > self.max_file_size_bytes:
            reason_codes.append(REASON_FILE_TOO_LARGE)

        extension = local_path.suffix.lower()
        rules_applied.append(RULE_EXTENSION_ALLOWED)
        if extension not in self.allowed_extensions:
            reason_codes.append(REASON_EXTENSION_NOT_ALLOWED)

        rules_applied.append(RULE_FILE_NON_EMPTY)
        if stat_result.st_size == 0:
            reason_codes.append(REASON_FILE_EMPTY)

        if not reason_codes:
            rules_applied.append(RULE_STRUCTURED_FORMAT)
            parse_reason = self._validate_structured_format(local_path, extension)
            if parse_reason is not None:
                reason_codes.append(parse_reason)

        if reason_codes:
            return self._build_result(
                status="invalid",
                reason_codes=tuple(reason_codes),
                operator_message=_operator_message(reason_codes[0], safe_display),
                rules_applied=rules_applied,
                started=started,
            )

        return self._build_result(
            status="valid",
            reason_codes=(),
            operator_message=f"Source file {safe_display} passed validation.",
            rules_applied=rules_applied,
            started=started,
        )

    def _validate_structured_format(self, path: Path, extension: str) -> str | None:
        try:
            if extension == ".csv":
                return self._validate_csv(path)
            if extension == ".json":
                return self._validate_json(path)
            if extension == ".txt":
                return self._validate_text(path)

            # Custom allowlist entries have already passed EXTENSION_ALLOWED.
            # WP-07 does not define per-extension schemas beyond CSV, JSON, and TXT,
            # so configured non-MVP extensions receive the same safe UTF-8
            # decodability check as TXT rather than being rejected as unsupported.
            return self._validate_text(path)
        except OSError:
            return REASON_FILE_NOT_READABLE

    def _validate_csv(self, path: Path) -> str | None:
        try:
            with path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.reader(handle, delimiter=",", strict=True)
                saw_row = False
                for row in reader:
                    if row:
                        saw_row = True
                if not saw_row:
                    return REASON_SCHEMA_INVALID
        except (UnicodeDecodeError, csv.Error, ValueError):
            return REASON_SCHEMA_INVALID
        return None

    def _validate_json(self, path: Path) -> str | None:
        try:
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            return REASON_SCHEMA_INVALID
        if not isinstance(payload, (dict, list)):
            return REASON_SCHEMA_INVALID
        return None

    def _validate_text(self, path: Path) -> str | None:
        try:
            with path.open("r", encoding="utf-8") as handle:
                chunk = handle.read(8192)
                while chunk:
                    chunk = handle.read(8192)
        except (UnicodeDecodeError, ValueError):
            return REASON_SCHEMA_INVALID
        return None

    def _build_result(
        self,
        *,
        status: Literal["valid", "invalid"],
        reason_codes: tuple[str, ...],
        operator_message: str,
        rules_applied: list[str],
        started: float,
    ) -> ValidationResult:
        return ValidationResult(
            status=status,
            reason_codes=reason_codes,
            operator_message=operator_message,
            rules_applied=tuple(rules_applied),
            duration_seconds=max(0.0, self.monotonic() - started),
        )


def _operator_message(reason_code: str, safe_display_path_text: str) -> str:
    if reason_code == REASON_FILE_NOT_FOUND:
        return f"Source file {safe_display_path_text} was not found during validation."
    if reason_code == REASON_FILE_NOT_READABLE:
        return f"Source file {safe_display_path_text} is not readable by the validation service."
    if reason_code == REASON_FILE_EMPTY:
        return f"Source file {safe_display_path_text} is empty."
    if reason_code == REASON_FILE_TOO_LARGE:
        return f"Source file {safe_display_path_text} exceeds the configured maximum file size."
    if reason_code == REASON_EXTENSION_NOT_ALLOWED:
        return f"Source file {safe_display_path_text} uses an unsupported extension for WP-07 validation."
    if reason_code == REASON_SCHEMA_INVALID:
        return f"Source file {safe_display_path_text} failed structured-format validation."
    if reason_code == REASON_PATH_POLICY_VIOLATION:
        return f"Source file {safe_display_path_text} failed source path validation."
    return f"Source file {safe_display_path_text} failed validation."


__all__ = [
    "ALLOWED_EXTENSIONS",
    "FileValidator",
    "REASON_EXTENSION_NOT_ALLOWED",
    "REASON_FILE_EMPTY",
    "REASON_FILE_NOT_FOUND",
    "REASON_FILE_NOT_READABLE",
    "REASON_FILE_TOO_LARGE",
    "REASON_PATH_POLICY_VIOLATION",
    "REASON_SCHEMA_INVALID",
    "RULE_EXTENSION_ALLOWED",
    "RULE_FILE_EXISTS",
    "RULE_FILE_NON_EMPTY",
    "RULE_FILE_READABLE",
    "RULE_FILE_SIZE_LIMIT",
    "RULE_PATH_ALLOWLISTED",
    "RULE_STRUCTURED_FORMAT",
    "ValidationResult",
]
