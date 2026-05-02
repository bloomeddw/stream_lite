"""Structured logging bootstrap primitives for WP-01."""

from .logging import (
    build_structured_log,
    configure_structured_logging,
    emit_structured_log,
    redact_sensitive_fields,
)

__all__ = [
    "build_structured_log",
    "configure_structured_logging",
    "emit_structured_log",
    "redact_sensitive_fields",
]
