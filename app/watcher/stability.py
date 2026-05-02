"""File snapshot, stability, and checksum helpers for WP-06 watcher polling."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class FileSnapshot:
    path: str
    size_bytes: int
    modified_ns: int
    observed_at_monotonic: float


def capture_file_snapshot(path: str | Path, *, observed_at_monotonic: float) -> FileSnapshot:
    """Capture size and mtime for a regular file without mutating it."""

    file_path = Path(path)
    stat = file_path.stat()
    return FileSnapshot(
        path=str(file_path),
        size_bytes=int(stat.st_size),
        modified_ns=int(stat.st_mtime_ns),
        observed_at_monotonic=float(observed_at_monotonic),
    )


def is_file_stable(
    previous: FileSnapshot | None,
    current: FileSnapshot,
    *,
    now_monotonic: float,
    stability_seconds: int | float,
) -> bool:
    """Return true when size and mtime are unchanged for the stability window."""

    if previous is None:
        return False
    if previous.path != current.path:
        return False
    if previous.size_bytes != current.size_bytes or previous.modified_ns != current.modified_ns:
        return False
    return float(now_monotonic) - float(previous.observed_at_monotonic) >= float(stability_seconds)


def sha256_file(path: str | Path, *, chunk_size: int = 1024 * 1024) -> str:
    """Return the lower-case SHA-256 hex digest for a file."""

    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


__all__ = ["FileSnapshot", "capture_file_snapshot", "is_file_stable", "sha256_file"]
