"""Retry backoff primitives for WP-10."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable

from app.config.settings import StreamLiteSettings

JITTER_FACTOR_MIN = 0.5
JITTER_FACTOR_MAX = 1.5

JitterSampler = Callable[[float, float], float]


@dataclass(slots=True)
class BackoffPolicy:
    max_attempts: int
    initial_backoff_seconds: int
    multiplier: float
    max_backoff_seconds: int
    jitter_enabled: bool
    jitter_sampler: JitterSampler | None = None

    def __post_init__(self) -> None:
        if self.max_attempts < 0:
            raise ValueError("max_attempts must be greater than or equal to 0")
        if self.initial_backoff_seconds < 1:
            raise ValueError("initial_backoff_seconds must be greater than or equal to 1")
        if self.multiplier < 1:
            raise ValueError("multiplier must be greater than or equal to 1")
        if self.max_backoff_seconds < 1:
            raise ValueError("max_backoff_seconds must be greater than or equal to 1")
        if self.jitter_sampler is None:
            self.jitter_sampler = random.uniform

    @classmethod
    def from_settings(
        cls,
        settings: StreamLiteSettings,
        *,
        jitter_sampler: JitterSampler | None = None,
    ) -> "BackoffPolicy":
        return cls(
            max_attempts=settings.retry_max_attempts,
            initial_backoff_seconds=settings.retry_initial_backoff_seconds,
            multiplier=settings.retry_backoff_multiplier,
            max_backoff_seconds=settings.retry_max_backoff_seconds,
            jitter_enabled=settings.retry_jitter_enabled,
            jitter_sampler=jitter_sampler,
        )

    def retry_allowed_after_attempt(self, current_attempt_number: int) -> bool:
        _validate_attempt_number(current_attempt_number)
        return current_attempt_number < self.max_attempts

    def next_attempt_number(self, current_attempt_number: int) -> int | None:
        if not self.retry_allowed_after_attempt(current_attempt_number):
            return None
        return current_attempt_number + 1

    def base_delay_seconds(self, current_attempt_number: int) -> float:
        _validate_attempt_number(current_attempt_number)
        raw_delay = float(self.initial_backoff_seconds) * (self.multiplier ** (current_attempt_number - 1))
        return min(float(self.max_backoff_seconds), raw_delay)

    def delay_bounds_seconds(self, current_attempt_number: int) -> tuple[float, float]:
        base_delay = self.base_delay_seconds(current_attempt_number)
        if not self.jitter_enabled:
            return base_delay, base_delay

        lower_bound = max(0.0, base_delay * JITTER_FACTOR_MIN)
        upper_bound = min(float(self.max_backoff_seconds), base_delay * JITTER_FACTOR_MAX)
        return lower_bound, max(lower_bound, upper_bound)

    def next_delay_seconds(self, current_attempt_number: int) -> float:
        lower_bound, upper_bound = self.delay_bounds_seconds(current_attempt_number)
        if lower_bound == upper_bound:
            return lower_bound

        sampled_delay = float(self.jitter_sampler(lower_bound, upper_bound))
        return min(upper_bound, max(lower_bound, sampled_delay))


def _validate_attempt_number(current_attempt_number: int) -> None:
    if current_attempt_number < 1:
        raise ValueError("current_attempt_number must be greater than or equal to 1")


__all__ = [
    "BackoffPolicy",
    "JITTER_FACTOR_MAX",
    "JITTER_FACTOR_MIN",
    "JitterSampler",
]
