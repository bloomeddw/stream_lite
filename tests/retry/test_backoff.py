from __future__ import annotations

from app.config.settings import StreamLiteSettings
from app.retry import BackoffPolicy


def test_backoff_sequence_uses_documented_defaults_without_jitter() -> None:
    policy = BackoffPolicy.from_settings(_settings(retry_jitter_enabled=False))

    assert policy.next_delay_seconds(1) == 1.0
    assert policy.next_delay_seconds(2) == 2.0
    assert policy.next_delay_seconds(3) == 4.0
    assert policy.next_delay_seconds(6) == 30.0
    assert policy.next_delay_seconds(7) == 30.0


def test_jitter_can_be_disabled_for_deterministic_tests() -> None:
    policy = BackoffPolicy.from_settings(
        _settings(retry_jitter_enabled=False),
        jitter_sampler=lambda lower_bound, upper_bound: upper_bound,
    )

    assert policy.delay_bounds_seconds(2) == (2.0, 2.0)
    assert policy.next_delay_seconds(2) == 2.0


def test_jitter_enabled_stays_within_bounds() -> None:
    policy = BackoffPolicy.from_settings(
        _settings(retry_jitter_enabled=True),
        jitter_sampler=lambda lower_bound, upper_bound: upper_bound + 100.0,
    )

    lower_bound, upper_bound = policy.delay_bounds_seconds(2)
    delay = policy.next_delay_seconds(2)

    assert lower_bound == 1.0
    assert upper_bound == 3.0
    assert lower_bound <= delay <= upper_bound
    assert delay == upper_bound


def test_max_attempts_behavior_counts_the_initial_attempt() -> None:
    policy = BackoffPolicy.from_settings(_settings(retry_max_attempts=3, retry_jitter_enabled=False))

    assert policy.retry_allowed_after_attempt(1) is True
    assert policy.next_attempt_number(1) == 2
    assert policy.retry_allowed_after_attempt(2) is True
    assert policy.next_attempt_number(2) == 3
    assert policy.retry_allowed_after_attempt(3) is False
    assert policy.next_attempt_number(3) is None


def _settings(**overrides: object) -> StreamLiteSettings:
    values: dict[str, object] = {
        "api_port": 8000,
        "dashboard_port": 8501,
        "broker_profile": "redis_streams",
        "processing_engine": "spark",
        "watch_root": "/data/sources",
        "output_root": "/data/outputs",
        "quarantine_root": "/data/quarantine",
        "database_url": "postgresql://streamlite:streamlite@localhost:5432/stream_lite",
        "redis_url": "redis://localhost:6379/0",
        "debug": False,
        "file_stability_seconds": 2,
        "max_file_size_mb": 100,
        "retry_max_attempts": 3,
        "retry_initial_backoff_seconds": 1,
        "retry_backoff_multiplier": 2.0,
        "retry_max_backoff_seconds": 30,
        "retry_jitter_enabled": True,
        "dashboard_presentation_file": "/app/config/dashboard_presentation.yaml",
        "log_level": "INFO",
        "reconciliation_interval_seconds": 10,
    }
    values.update(overrides)
    return StreamLiteSettings(**values)
