"""Watcher-side orchestration helpers for WP-06."""

from app.watcher.deduplication import compute_deduplication_key
from app.watcher.routing import build_route_preview, match_source_to_destinations, normalize_route_tags
from app.watcher.service import PollOnceResult, WatcherService
from app.watcher.stability import FileSnapshot, capture_file_snapshot, is_file_stable, sha256_file

__all__ = [
    "FileSnapshot",
    "PollOnceResult",
    "WatcherService",
    "build_route_preview",
    "capture_file_snapshot",
    "compute_deduplication_key",
    "is_file_stable",
    "match_source_to_destinations",
    "normalize_route_tags",
    "sha256_file",
]
