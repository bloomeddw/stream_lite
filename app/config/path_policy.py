"""Path allowlist and safe-display primitives for Stream Lite WP-01."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Callable, Iterable, Literal

from app import ensure_uuid_str

PathPurpose = Literal["source", "destination"]
PathStatus = Literal["green", "red"]
PathResolver = Callable[[str], str]

_WINDOWS_DRIVE_PATTERN = re.compile(r"^[A-Za-z]:[\\/]")


@dataclass(frozen=True, slots=True)
class PathValidationResult:
    """Operator-safe path validation result aligned with the API schema."""

    purpose: PathPurpose
    path: str
    normalized_path: str
    display_path: str
    status: PathStatus
    reason_code: str | None
    message: str
    correlation_id: str

    @property
    def is_allowlisted(self) -> bool:
        return self.status == "green"

    def to_dict(self) -> dict[str, str | None]:
        return {
            "purpose": self.purpose,
            "path": self.path,
            "normalized_path": self.normalized_path,
            "display_path": self.display_path,
            "status": self.status,
            "reason_code": self.reason_code,
            "message": self.message,
            "correlation_id": self.correlation_id,
        }


@dataclass(frozen=True, slots=True)
class PathPolicy:
    """Purpose-scoped path allowlists using documented container-path semantics."""

    source_roots: tuple[str, ...]
    destination_roots: tuple[str, ...]
    debug: bool = False
    resolver: PathResolver | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_roots", _normalize_roots(self.source_roots))
        object.__setattr__(
            self,
            "destination_roots",
            _normalize_roots(self.destination_roots),
        )

    def validate_path(
        self,
        purpose: PathPurpose,
        raw_path: str,
        *,
        correlation_id: str | None = None,
    ) -> PathValidationResult:
        allowed_roots = self._allowed_roots_for(purpose)
        correlation = ensure_uuid_str(correlation_id, field_name="correlation_id")

        try:
            normalized_candidate, had_parent_reference = _normalize_candidate_path(raw_path)
        except _PathValidationFailure as exc:
            display_path = safe_display_path(raw_path)
            return self._build_result(
                purpose=purpose,
                path=display_path,
                normalized_path=display_path,
                display_path=display_path,
                status="red",
                reason_code=exc.error_code,
                correlation_id=correlation,
            )

        resolved_path = normalized_candidate
        if self.resolver is not None:
            try:
                resolved_candidate, _ = _normalize_candidate_path(
                    self.resolver(normalized_candidate)
                )
            except _PathValidationFailure:
                display_path = safe_display_path(normalized_candidate, allowed_roots=allowed_roots)
                return self._build_result(
                    purpose=purpose,
                    path=display_path,
                    normalized_path=display_path,
                    display_path=display_path,
                    status="red",
                    reason_code="PATH_SYMLINK_ESCAPE",
                    correlation_id=correlation,
                )

            if self._contains(resolved_candidate, allowed_roots) is False and self._contains(
                normalized_candidate,
                allowed_roots,
            ):
                display_path = _display_from_root(
                    normalized_candidate,
                    self._matching_root(normalized_candidate, allowed_roots),
                )
                return self._build_result(
                    purpose=purpose,
                    path=display_path,
                    normalized_path=display_path,
                    display_path=display_path,
                    status="red",
                    reason_code="PATH_SYMLINK_ESCAPE",
                    correlation_id=correlation,
                )

            resolved_path = resolved_candidate

        matched_root = self._matching_root(resolved_path, allowed_roots)
        if matched_root is None:
            display_path = safe_display_path(raw_path, allowed_roots=allowed_roots)
            reason_code = (
                "PATH_TRAVERSAL_REJECTED" if had_parent_reference else "PATH_NOT_ALLOWLISTED"
            )
            return self._build_result(
                purpose=purpose,
                path=display_path,
                normalized_path=display_path,
                display_path=display_path,
                status="red",
                reason_code=reason_code,
                correlation_id=correlation,
            )

        display_path = _display_from_root(resolved_path, matched_root)
        safe_path = resolved_path if self.debug or matched_root else display_path
        return self._build_result(
            purpose=purpose,
            path=safe_path,
            normalized_path=resolved_path,
            display_path=display_path,
            status="green",
            reason_code=None,
            correlation_id=correlation,
        )

    def _allowed_roots_for(self, purpose: PathPurpose) -> tuple[str, ...]:
        if purpose == "source":
            return self.source_roots
        if purpose == "destination":
            return self.destination_roots
        raise ValueError(f"Unsupported path purpose: {purpose}")

    def _contains(self, candidate: str, roots: Iterable[str]) -> bool:
        return self._matching_root(candidate, roots) is not None

    def _matching_root(self, candidate: str, roots: Iterable[str]) -> str | None:
        candidate_path = PurePosixPath(candidate)
        matches = [
            root
            for root in roots
            if candidate_path == PurePosixPath(root)
            or candidate_path.is_relative_to(PurePosixPath(root))
        ]
        if not matches:
            return None
        return max(matches, key=len)

    def _build_result(
        self,
        *,
        purpose: PathPurpose,
        path: str,
        normalized_path: str,
        display_path: str,
        status: PathStatus,
        reason_code: str | None,
        correlation_id: str,
    ) -> PathValidationResult:
        message = _build_message(
            purpose=purpose,
            status=status,
            reason_code=reason_code,
            display_path=display_path,
        )
        return PathValidationResult(
            purpose=purpose,
            path=path,
            normalized_path=normalized_path,
            display_path=display_path,
            status=status,
            reason_code=reason_code,
            message=message,
            correlation_id=correlation_id,
        )


@dataclass(frozen=True, slots=True)
class _PathValidationFailure(Exception):
    error_code: str


def _normalize_roots(roots: Iterable[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    for root in roots:
        normalized_root, had_parent_reference = _normalize_candidate_path(root)
        if had_parent_reference:
            raise ValueError("allowlist roots must not contain traversal segments")
        normalized.append(normalized_root)
    return tuple(normalized)


def _normalize_candidate_path(raw_path: str) -> tuple[str, bool]:
    value = raw_path.strip()
    if not value:
        raise _PathValidationFailure("PATH_INVALID")
    if "\x00" in value:
        raise _PathValidationFailure("PATH_INVALID")
    if "\\" in value or _WINDOWS_DRIVE_PATTERN.match(value):
        raise _PathValidationFailure("PATH_INVALID")
    if not value.startswith("/"):
        raise _PathValidationFailure("PATH_INVALID")

    normalized_parts: list[str] = []
    had_parent_reference = False
    for part in value.split("/"):
        if part in {"", "."}:
            continue
        if part == "..":
            had_parent_reference = True
            if normalized_parts:
                normalized_parts.pop()
                continue
            raise _PathValidationFailure("PATH_TRAVERSAL_REJECTED")
        normalized_parts.append(part)

    normalized_path = "/" + "/".join(normalized_parts) if normalized_parts else "/"
    return normalized_path, had_parent_reference


def safe_display_path(raw_path: str, *, allowed_roots: Iterable[str] = ()) -> str:
    try:
        normalized_path, _ = _normalize_candidate_path(raw_path)
    except _PathValidationFailure:
        return _fallback_display_path(raw_path)

    matched_root = _matching_root_for_display(normalized_path, allowed_roots)
    if matched_root is None:
        return _fallback_display_path(normalized_path)
    return _display_from_root(normalized_path, matched_root)


def _matching_root_for_display(candidate: str, roots: Iterable[str]) -> str | None:
    candidate_path = PurePosixPath(candidate)
    matches = [
        root
        for root in roots
        if candidate_path == PurePosixPath(root)
        or candidate_path.is_relative_to(PurePosixPath(root))
    ]
    if not matches:
        return None
    return max(matches, key=len)


def _display_from_root(normalized_path: str, root: str | None) -> str:
    if root is None:
        return _fallback_display_path(normalized_path)
    relative = PurePosixPath(normalized_path).relative_to(PurePosixPath(root))
    relative_text = relative.as_posix()
    if not relative_text or relative_text == ".":
        return "/"
    return f"/{relative_text}"


def _fallback_display_path(raw_path: str) -> str:
    sanitized = raw_path.replace("\\", "/").strip()
    parts = [part for part in sanitized.split("/") if part not in {"", ".", ".."}]
    if not parts:
        return "/"
    return f"/{parts[-1]}"


def _build_message(
    *,
    purpose: PathPurpose,
    status: PathStatus,
    reason_code: str | None,
    display_path: str,
) -> str:
    role = f"{purpose} path"
    if status == "green":
        return f"{role.capitalize()} is allowlisted."
    if reason_code == "PATH_NOT_ALLOWLISTED":
        return f"{role.capitalize()} {display_path} is outside the configured allowlist."
    if reason_code == "PATH_TRAVERSAL_REJECTED":
        return f"{role.capitalize()} {display_path} failed path-safety validation."
    if reason_code == "PATH_SYMLINK_ESCAPE":
        return f"{role.capitalize()} {display_path} resolves outside the configured allowlist."
    return f"{role.capitalize()} is not a supported absolute container path."


__all__ = ["PathPolicy", "PathValidationResult", "safe_display_path"]
