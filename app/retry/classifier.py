"""Retry classification primitives for WP-10."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

RetryStage = Literal["validation", "processing", "delivery", "routing", "event"]
RetryFailureClass = Literal["retryable", "non_retryable"]
TerminalState = Literal["FAILED", "QUARANTINED"]

_VALID_STAGES = frozenset({"validation", "processing", "delivery", "routing", "event"})


@dataclass(frozen=True, slots=True)
class RetryClassification:
    stage: RetryStage
    error_code: str
    failure_class: RetryFailureClass
    retryable: bool
    terminal_state_when_not_retryable: TerminalState | None
    operator_message: str


@dataclass(frozen=True, slots=True)
class _CatalogEntry:
    failure_class: RetryFailureClass
    retryable: bool
    terminal_state_when_not_retryable: TerminalState | None
    operator_message: str


_CATALOG: dict[tuple[str, str], _CatalogEntry] = {

    ("event", "BROKER_UNAVAILABLE"): _CatalogEntry(
        failure_class="retryable",
        retryable=True,
        terminal_state_when_not_retryable=None,
        operator_message="Broker is unavailable and event publication or consumption will retry.",
    ),
    ("event", "BROKER_PUBLISH_FAILURE"): _CatalogEntry(
        failure_class="retryable",
        retryable=True,
        terminal_state_when_not_retryable=None,
        operator_message="Broker publish failed and event publication will retry.",
    ),
    ("event", "PATH_POLICY_VIOLATION"): _CatalogEntry(
        failure_class="non_retryable",
        retryable=False,
        terminal_state_when_not_retryable="FAILED",
        operator_message="Event handling failed a path policy check and it will not be retried automatically.",
    ),
    ("validation", "FILE_EMPTY"): _CatalogEntry(
        failure_class="non_retryable",
        retryable=False,
        terminal_state_when_not_retryable="QUARANTINED",
        operator_message="Validation rejected an empty source file and it will not be retried automatically.",
    ),
    ("validation", "FILE_NOT_FOUND"): _CatalogEntry(
        failure_class="non_retryable",
        retryable=False,
        terminal_state_when_not_retryable="QUARANTINED",
        operator_message="Validation could not locate the source file and it will not be retried automatically.",
    ),
    ("validation", "FILE_NOT_READABLE"): _CatalogEntry(
        failure_class="non_retryable",
        retryable=False,
        terminal_state_when_not_retryable="QUARANTINED",
        operator_message="Validation could not read the source file and it will not be retried automatically.",
    ),
    ("validation", "FILE_TOO_LARGE"): _CatalogEntry(
        failure_class="non_retryable",
        retryable=False,
        terminal_state_when_not_retryable="QUARANTINED",
        operator_message="Validation rejected the source file size and it will not be retried automatically.",
    ),
    ("validation", "EXTENSION_NOT_ALLOWED"): _CatalogEntry(
        failure_class="non_retryable",
        retryable=False,
        terminal_state_when_not_retryable="QUARANTINED",
        operator_message="Validation rejected the source file extension and it will not be retried automatically.",
    ),
    ("validation", "SCHEMA_INVALID"): _CatalogEntry(
        failure_class="non_retryable",
        retryable=False,
        terminal_state_when_not_retryable="QUARANTINED",
        operator_message="Validation rejected the source file schema and it will not be retried automatically.",
    ),
    ("validation", "PATH_POLICY_VIOLATION"): _CatalogEntry(
        failure_class="non_retryable",
        retryable=False,
        terminal_state_when_not_retryable="QUARANTINED",
        operator_message="Validation rejected the source path and it will not be retried automatically.",
    ),
    ("validation", "PATH_SECURITY_FAILURE"): _CatalogEntry(
        failure_class="non_retryable",
        retryable=False,
        terminal_state_when_not_retryable="QUARANTINED",
        operator_message="Validation failed a path security check and it will not be retried automatically.",
    ),
    ("validation", "VALIDATION_POLICY_FAILURE"): _CatalogEntry(
        failure_class="non_retryable",
        retryable=False,
        terminal_state_when_not_retryable="QUARANTINED",
        operator_message="Validation policy failed and it will not be retried automatically.",
    ),
    ("processing", "PROCESSOR_TIMEOUT"): _CatalogEntry(
        failure_class="retryable",
        retryable=True,
        terminal_state_when_not_retryable=None,
        operator_message="Processing timed out and a retry can be scheduled.",
    ),
    ("processing", "PROCESSOR_TRANSIENT_ERROR"): _CatalogEntry(
        failure_class="retryable",
        retryable=True,
        terminal_state_when_not_retryable=None,
        operator_message="Processing hit a transient error and a retry can be scheduled.",
    ),
    ("processing", "PROCESSING_TRANSIENT_FAILURE"): _CatalogEntry(
        failure_class="retryable",
        retryable=True,
        terminal_state_when_not_retryable=None,
        operator_message="Processing hit a transient failure and a retry can be scheduled.",
    ),
    ("processing", "PROCESSING_INPUT_UNAVAILABLE"): _CatalogEntry(
        failure_class="retryable",
        retryable=True,
        terminal_state_when_not_retryable=None,
        operator_message="Processing input is temporarily unavailable and a retry can be scheduled.",
    ),
    ("processing", "PROCESSING_OUTPUT_UNAVAILABLE"): _CatalogEntry(
        failure_class="retryable",
        retryable=True,
        terminal_state_when_not_retryable=None,
        operator_message="Processing output staging is temporarily unavailable and a retry can be scheduled.",
    ),
    ("processing", "PROCESSING_UNEXPECTED_ERROR"): _CatalogEntry(
        failure_class="retryable",
        retryable=True,
        terminal_state_when_not_retryable=None,
        operator_message="Processing failed unexpectedly and a retry can be scheduled.",
    ),
    ("processing", "PROCESSING_ARTIFACT_INVALID"): _CatalogEntry(
        failure_class="non_retryable",
        retryable=False,
        terminal_state_when_not_retryable="FAILED",
        operator_message="Processing produced an invalid artifact contract and it will not be retried automatically.",
    ),
    ("processing", "PROCESSING_INPUT_INVALID"): _CatalogEntry(
        failure_class="non_retryable",
        retryable=False,
        terminal_state_when_not_retryable="FAILED",
        operator_message="Processing rejected invalid input and it will not be retried automatically.",
    ),
    ("processing", "PROCESSING_SOURCE_SHA256_MISSING"): _CatalogEntry(
        failure_class="non_retryable",
        retryable=False,
        terminal_state_when_not_retryable="FAILED",
        operator_message="Processing metadata is incomplete and it will not be retried automatically.",
    ),
    ("processing", "UNSUPPORTED_EXTENSION_REACHED_PROCESSING"): _CatalogEntry(
        failure_class="non_retryable",
        retryable=False,
        terminal_state_when_not_retryable="FAILED",
        operator_message="Processing reached an unsupported extension and it will not be retried automatically.",
    ),
    ("delivery", "DESTINATION_TEMPORARILY_UNAVAILABLE"): _CatalogEntry(
        failure_class="retryable",
        retryable=True,
        terminal_state_when_not_retryable=None,
        operator_message="Delivery destination is temporarily unavailable and a retry can be scheduled.",
    ),
    ("delivery", "DESTINATION_UNAVAILABLE"): _CatalogEntry(
        failure_class="retryable",
        retryable=True,
        terminal_state_when_not_retryable=None,
        operator_message="Delivery destination is unavailable and a retry can be scheduled.",
    ),
    ("delivery", "DELIVERY_TRANSIENT_FAILURE"): _CatalogEntry(
        failure_class="retryable",
        retryable=True,
        terminal_state_when_not_retryable=None,
        operator_message="Delivery hit a transient failure and a retry can be scheduled.",
    ),
    ("delivery", "DESTINATION_NOT_FOUND"): _CatalogEntry(
        failure_class="retryable",
        retryable=True,
        terminal_state_when_not_retryable=None,
        operator_message="Delivery destination is unavailable and a retry can be scheduled.",
    ),
    ("delivery", "DESTINATION_NOT_WRITABLE"): _CatalogEntry(
        failure_class="retryable",
        retryable=True,
        terminal_state_when_not_retryable=None,
        operator_message="Delivery destination is not writable and a retry can be scheduled.",
    ),
    ("delivery", "FINALIZE_FAILED"): _CatalogEntry(
        failure_class="retryable",
        retryable=True,
        terminal_state_when_not_retryable=None,
        operator_message="Delivery finalize failed and a retry can be scheduled.",
    ),
    ("delivery", "SOURCE_TRANSFER_FAILED"): _CatalogEntry(
        failure_class="retryable",
        retryable=True,
        terminal_state_when_not_retryable=None,
        operator_message="Delivery could not read the staged output and a retry can be scheduled.",
    ),
    ("delivery", "DESTINATION_NOT_ALLOWLISTED"): _CatalogEntry(
        failure_class="non_retryable",
        retryable=False,
        terminal_state_when_not_retryable="FAILED",
        operator_message="Delivery destination failed the allowlist policy and it will not be retried automatically.",
    ),
    ("delivery", "FINALIZE_UNSUPPORTED"): _CatalogEntry(
        failure_class="non_retryable",
        retryable=False,
        terminal_state_when_not_retryable="FAILED",
        operator_message="Delivery finalize is unsupported for the current destination and it will not be retried automatically.",
    ),
    ("delivery", "PATH_POLICY_VIOLATION"): _CatalogEntry(
        failure_class="non_retryable",
        retryable=False,
        terminal_state_when_not_retryable="FAILED",
        operator_message="Delivery failed a path policy check and it will not be retried automatically.",
    ),
    ("delivery", "PATH_SECURITY_FAILURE"): _CatalogEntry(
        failure_class="non_retryable",
        retryable=False,
        terminal_state_when_not_retryable="FAILED",
        operator_message="Delivery failed a path security check and it will not be retried automatically.",
    ),
    ("routing", "NO_MATCHING_DESTINATION"): _CatalogEntry(
        failure_class="non_retryable",
        retryable=False,
        terminal_state_when_not_retryable="FAILED",
        operator_message="Routing found no matching destination and it will not be retried automatically.",
    ),
    ("routing", "PATH_POLICY_VIOLATION"): _CatalogEntry(
        failure_class="non_retryable",
        retryable=False,
        terminal_state_when_not_retryable="FAILED",
        operator_message="Routing failed a path policy check and it will not be retried automatically.",
    ),
    ("routing", "PATH_SECURITY_FAILURE"): _CatalogEntry(
        failure_class="non_retryable",
        retryable=False,
        terminal_state_when_not_retryable="FAILED",
        operator_message="Routing failed a path security check and it will not be retried automatically.",
    ),
}


class RetryClassifier:
    """Map stage-local failure codes to retry policy decisions."""

    def classify(
        self,
        *,
        stage: str,
        error_code: str,
        operator_message: str | None = None,
    ) -> RetryClassification:
        normalized_stage = _normalize_stage(stage)
        normalized_error_code = _normalize_error_code(error_code)
        entry = _CATALOG.get((normalized_stage, normalized_error_code))
        if entry is None:
            entry = _default_non_retryable_entry(normalized_stage)

        resolved_message = operator_message.strip() if operator_message and operator_message.strip() else entry.operator_message
        return RetryClassification(
            stage=normalized_stage,
            error_code=normalized_error_code,
            failure_class=entry.failure_class,
            retryable=entry.retryable,
            terminal_state_when_not_retryable=entry.terminal_state_when_not_retryable,
            operator_message=resolved_message,
        )


def _normalize_stage(stage: str) -> RetryStage:
    normalized = stage.strip().lower()
    if normalized not in _VALID_STAGES:
        if normalized == "broker":
            normalized = "event"
        else:
            raise ValueError("stage must be one of validation, processing, delivery, routing, event, or broker")
    return normalized  # type: ignore[return-value]


def _normalize_error_code(error_code: str) -> str:
    normalized = error_code.strip().upper()
    if not normalized:
        raise ValueError("error_code must not be empty")
    return normalized


def _default_non_retryable_entry(stage: RetryStage) -> _CatalogEntry:
    terminal_state = "QUARANTINED" if stage == "validation" else "FAILED"
    message_by_stage = {
        "validation": "Validation failed and it will not be retried automatically.",
        "processing": "Processing failed and it will not be retried automatically.",
        "delivery": "Delivery failed and it will not be retried automatically.",
        "routing": "Routing failed and it will not be retried automatically.",
        "event": "Event publication or consumption failed and it will not be retried automatically.",
    }
    return _CatalogEntry(
        failure_class="non_retryable",
        retryable=False,
        terminal_state_when_not_retryable=terminal_state,
        operator_message=message_by_stage[stage],
    )


__all__ = ["RetryClassification", "RetryClassifier"]
