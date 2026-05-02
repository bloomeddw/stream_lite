from __future__ import annotations

from pathlib import Path

import pytest

from app.config.path_policy import PathPolicy
from app.config.settings import StreamLiteSettings
from app.validation import (
    FileValidator,
    REASON_EXTENSION_NOT_ALLOWED,
    REASON_FILE_EMPTY,
    REASON_FILE_NOT_FOUND,
    REASON_FILE_NOT_READABLE,
    REASON_FILE_TOO_LARGE,
    REASON_SCHEMA_INVALID,
)


def test_validator_accepts_valid_csv_json_and_txt(tmp_path) -> None:
    validator, paths = _make_validator(tmp_path)
    local_source_root = paths["local_source_root"]
    container_source_root = paths["container_source_root"]

    cases = {
        "valid.csv": "a,b\n1,2\n",
        "valid.json": '{"ok": true, "items": [1, 2]}',
        "valid.txt": "hello\n",
    }
    for file_name, content in cases.items():
        source_path = local_source_root / file_name
        source_path.write_text(content, encoding="utf-8")
        result = validator.validate_file(
            f"{container_source_root}/{file_name}",
            source_display_path=f"/source-a/{file_name}",
        )
        assert result.status == "valid"
        assert result.reason_codes == ()
        assert result.rules_applied[-1] == "STRUCTURED_FORMAT"



def test_validator_accepts_configurable_extension_allowlist(tmp_path) -> None:
    validator, paths = _make_validator(tmp_path, allowed_extensions=(".dat",))
    source_path = paths["local_source_root"] / "payload.dat"
    source_path.write_text("hello", encoding="utf-8")

    result = validator.validate_file(
        f"{paths['container_source_root']}/payload.dat",
        source_display_path="/source-a/payload.dat",
    )

    assert result.status == "valid"
    assert result.reason_codes == ()


def test_validator_rejects_empty_supported_file(tmp_path) -> None:
    validator, paths = _make_validator(tmp_path)
    source_path = paths["local_source_root"] / "empty.txt"
    source_path.write_text("", encoding="utf-8")

    result = validator.validate_file(
        f"{paths['container_source_root']}/empty.txt",
        source_display_path="/source-a/empty.txt",
    )

    assert result.status == "invalid"
    assert result.reason_codes == (REASON_FILE_EMPTY,)


def test_validator_rejects_oversized_file_without_full_read(tmp_path, monkeypatch) -> None:
    validator, paths = _make_validator(tmp_path, max_file_size_mb=1)
    source_path = paths["local_source_root"] / "large.csv"
    source_path.write_bytes(b"x" * (validator.max_file_size_bytes + 1))
    read_sizes: list[int] = []
    real_open = Path.open

    def tracking_open(self: Path, *args, **kwargs):  # type: ignore[no-untyped-def]
        handle = real_open(self, *args, **kwargs)
        mode = args[0] if args else kwargs.get("mode", "r")
        if self == source_path and mode == "rb":
            return _TrackedBinaryHandle(handle, read_sizes)
        return handle

    monkeypatch.setattr(Path, "open", tracking_open)

    result = validator.validate_file(
        f"{paths['container_source_root']}/large.csv",
        source_display_path="/source-a/large.csv",
    )

    assert result.status == "invalid"
    assert result.reason_codes == (REASON_FILE_TOO_LARGE,)
    assert read_sizes == [1]


def test_validator_rejects_unsupported_extension(tmp_path) -> None:
    validator, paths = _make_validator(tmp_path)
    source_path = paths["local_source_root"] / "input.xml"
    source_path.write_text("<root />", encoding="utf-8")

    result = validator.validate_file(
        f"{paths['container_source_root']}/input.xml",
        source_display_path="/source-a/input.xml",
    )

    assert result.status == "invalid"
    assert result.reason_codes == (REASON_EXTENSION_NOT_ALLOWED,)


@pytest.mark.parametrize(
    ("file_name", "payload"),
    [
        ("broken.json", b"{"),
        ("broken.csv", b'"unterminated\n'),
        ("broken.txt", b"\xff\xfe\xfd"),
    ],
)
def test_validator_rejects_malformed_structured_files(tmp_path, file_name: str, payload: bytes) -> None:
    validator, paths = _make_validator(tmp_path)
    source_path = paths["local_source_root"] / file_name
    source_path.write_bytes(payload)

    result = validator.validate_file(
        f"{paths['container_source_root']}/{file_name}",
        source_display_path=f"/source-a/{file_name}",
    )

    assert result.status == "invalid"
    assert result.reason_codes == (REASON_SCHEMA_INVALID,)


def test_validator_rejects_missing_file(tmp_path) -> None:
    validator, paths = _make_validator(tmp_path)

    result = validator.validate_file(
        f"{paths['container_source_root']}/missing.csv",
        source_display_path="/source-a/missing.csv",
    )

    assert result.status == "invalid"
    assert result.reason_codes == (REASON_FILE_NOT_FOUND,)


def test_validator_rejects_unreadable_file(tmp_path, monkeypatch) -> None:
    validator, paths = _make_validator(tmp_path)
    source_path = paths["local_source_root"] / "protected.csv"
    source_path.write_text("a,b\n1,2\n", encoding="utf-8")
    real_open = Path.open

    def unreadable_open(self: Path, *args, **kwargs):  # type: ignore[no-untyped-def]
        if self == source_path and (args[0] if args else kwargs.get("mode", "r")) == "rb":
            raise PermissionError("denied")
        return real_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", unreadable_open)

    result = validator.validate_file(
        f"{paths['container_source_root']}/protected.csv",
        source_display_path="/source-a/protected.csv",
    )

    assert result.status == "invalid"
    assert result.reason_codes == (REASON_FILE_NOT_READABLE,)


def _make_validator(
    tmp_path,
    *,
    max_file_size_mb: int = 100,
    allowed_extensions: tuple[str, ...] | None = None,
) -> tuple[FileValidator, dict[str, Path | str]]:
    local_source_root = tmp_path / "sources" / "source-a"
    local_output_root = tmp_path / "outputs"
    local_quarantine_root = tmp_path / "quarantine"
    local_source_root.mkdir(parents=True, exist_ok=True)
    local_output_root.mkdir(parents=True, exist_ok=True)
    local_quarantine_root.mkdir(parents=True, exist_ok=True)

    container_base = f"/stream-lite-test/{tmp_path.name}"
    container_source_root = f"{container_base}/sources/source-a"
    container_watch_root = f"{container_base}/sources"
    container_output_root = f"{container_base}/outputs"
    container_quarantine_root = f"{container_base}/quarantine"

    settings = StreamLiteSettings(
        api_port=8000,
        dashboard_port=8501,
        broker_profile="redis_streams",
        processing_engine="spark",
        watch_root=container_watch_root,
        output_root=container_output_root,
        quarantine_root=container_quarantine_root,
        database_url="postgresql://stream_lite:stream_lite@postgres:5432/stream_lite",
        redis_url="redis://redis:6379/0",
        debug=False,
        file_stability_seconds=2,
        max_file_size_mb=max_file_size_mb,
        retry_max_attempts=3,
        retry_initial_backoff_seconds=1,
        retry_backoff_multiplier=2.0,
        retry_max_backoff_seconds=30,
        retry_jitter_enabled=True,
        dashboard_presentation_file="/app/config/dashboard_presentation.yaml",
        log_level="INFO",
        reconciliation_interval_seconds=10,
    )
    path_policy = PathPolicy(
        source_roots=(container_watch_root,),
        destination_roots=(container_output_root,),
        debug=False,
    )

    def filesystem_resolver(container_path: str):
        if container_path == container_source_root or container_path.startswith(f"{container_source_root}/"):
            return local_source_root / container_path.removeprefix(container_source_root).lstrip("/")
        if container_path == container_watch_root:
            return local_source_root.parent
        if container_path == container_output_root:
            return local_output_root
        if container_path == container_quarantine_root:
            return local_quarantine_root
        return container_path

    validator = FileValidator(
        path_policy=path_policy,
        settings=settings,
        filesystem_resolver=filesystem_resolver,
        allowed_extensions=allowed_extensions,
    )
    return validator, {
        "local_source_root": local_source_root,
        "container_source_root": container_source_root,
    }


class _TrackedBinaryHandle:
    def __init__(self, handle, read_sizes: list[int]) -> None:  # type: ignore[no-untyped-def]
        self._handle = handle
        self._read_sizes = read_sizes

    def __getattr__(self, name: str):  # type: ignore[no-untyped-def]
        return getattr(self._handle, name)

    def __enter__(self):  # type: ignore[no-untyped-def]
        self._handle.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb):  # type: ignore[no-untyped-def]
        return self._handle.__exit__(exc_type, exc, tb)

    def read(self, size: int = -1) -> bytes:
        self._read_sizes.append(size)
        if size in {-1, 0} or size > 1:
            raise AssertionError("validation read more than the readability probe")
        return self._handle.read(size)
