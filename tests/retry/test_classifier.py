from __future__ import annotations

import pytest

from app.retry import RetryClassifier


def test_retryable_processing_failure_returns_retryable() -> None:
    classification = RetryClassifier().classify(
        stage="processing",
        error_code="PROCESSOR_TRANSIENT_ERROR",
    )

    assert classification.stage == "processing"
    assert classification.failure_class == "retryable"
    assert classification.retryable is True
    assert classification.terminal_state_when_not_retryable is None


def test_retryable_delivery_failure_returns_retryable() -> None:
    classification = RetryClassifier().classify(
        stage="delivery",
        error_code="DESTINATION_TEMPORARILY_UNAVAILABLE",
    )

    assert classification.stage == "delivery"
    assert classification.failure_class == "retryable"
    assert classification.retryable is True
    assert classification.terminal_state_when_not_retryable is None


@pytest.mark.parametrize(
    ("error_code", "expected_message"),
    [
        ("SCHEMA_INVALID", "Validation rejected the source file schema and it will not be retried automatically."),
        ("EXTENSION_NOT_ALLOWED", "Validation rejected the source file extension and it will not be retried automatically."),
        ("PATH_POLICY_VIOLATION", "Validation rejected the source path and it will not be retried automatically."),
    ],
)
def test_validation_policy_failures_are_non_retryable(
    error_code: str,
    expected_message: str,
) -> None:
    classification = RetryClassifier().classify(
        stage="validation",
        error_code=error_code,
    )

    assert classification.failure_class == "non_retryable"
    assert classification.retryable is False
    assert classification.terminal_state_when_not_retryable == "QUARANTINED"
    assert classification.operator_message == expected_message


def test_unknown_failure_defaults_to_non_retryable() -> None:
    classification = RetryClassifier().classify(
        stage="processing",
        error_code="UNDOCUMENTED_FAILURE",
    )

    assert classification.stage == "processing"
    assert classification.failure_class == "non_retryable"
    assert classification.retryable is False
    assert classification.terminal_state_when_not_retryable == "FAILED"
    assert classification.operator_message == "Processing failed and it will not be retried automatically."


def test_broker_unavailable_event_failure_returns_retryable() -> None:
    classification = RetryClassifier().classify(
        stage="event",
        error_code="BROKER_UNAVAILABLE",
    )

    assert classification.stage == "event"
    assert classification.error_code == "BROKER_UNAVAILABLE"
    assert classification.failure_class == "retryable"
    assert classification.retryable is True
    assert classification.terminal_state_when_not_retryable is None
    assert "Broker is unavailable" in classification.operator_message


def test_broker_stage_alias_maps_to_event_retry_catalog() -> None:
    classification = RetryClassifier().classify(
        stage="broker",
        error_code="BROKER_PUBLISH_FAILURE",
    )

    assert classification.stage == "event"
    assert classification.error_code == "BROKER_PUBLISH_FAILURE"
    assert classification.failure_class == "retryable"
    assert classification.retryable is True


def test_event_path_policy_failure_is_non_retryable() -> None:
    classification = RetryClassifier().classify(
        stage="event",
        error_code="PATH_POLICY_VIOLATION",
    )

    assert classification.failure_class == "non_retryable"
    assert classification.retryable is False
    assert classification.terminal_state_when_not_retryable == "FAILED"

def test_retry_policy_failure_class_aliases_are_classified() -> None:
    classifier = RetryClassifier()

    assert classifier.classify(stage="processing", error_code="PROCESSING_TRANSIENT_FAILURE").retryable is True
    assert classifier.classify(stage="delivery", error_code="DELIVERY_TRANSIENT_FAILURE").retryable is True
    assert classifier.classify(stage="delivery", error_code="DESTINATION_UNAVAILABLE").retryable is True


def test_retry_policy_non_retryable_class_aliases_are_classified() -> None:
    classifier = RetryClassifier()

    validation_policy = classifier.classify(stage="validation", error_code="VALIDATION_POLICY_FAILURE")
    validation_path = classifier.classify(stage="validation", error_code="PATH_SECURITY_FAILURE")
    delivery_path = classifier.classify(stage="delivery", error_code="PATH_SECURITY_FAILURE")
    routing_path = classifier.classify(stage="routing", error_code="PATH_SECURITY_FAILURE")

    assert validation_policy.retryable is False
    assert validation_policy.terminal_state_when_not_retryable == "QUARANTINED"
    assert validation_path.retryable is False
    assert validation_path.terminal_state_when_not_retryable == "QUARANTINED"
    assert delivery_path.retryable is False
    assert delivery_path.terminal_state_when_not_retryable == "FAILED"
    assert routing_path.retryable is False
    assert routing_path.terminal_state_when_not_retryable == "FAILED"

