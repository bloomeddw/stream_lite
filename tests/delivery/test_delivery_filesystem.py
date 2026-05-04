from __future__ import annotations

import errno
import hashlib
from datetime import date
from pathlib import Path
from uuid import UUID

import pytest

from app.config.path_policy import PathPolicy
from app.delivery import (
    DESTINATION_NOT_ALLOWLISTED,
    DESTINATION_NOT_FOUND,
    DESTINATION_NOT_WRITABLE,
    FINALIZE_UNSUPPORTED,
    SOURCE_TRANSFER_FAILED,
    copy_output_to_destination,
)


PROCESSING_ROOT = "/stream-lite-test/processing"
DESTINATION_ROOT = "/stream-lite-test/destinations"
JOB_ID = UUID("44444444-4444-4444-8444-444444444444")
WATCHER_ID = UUID("22222222-2222-4222-8222-222222222222")
SOURCE_OUTPUT_LOCATOR = (
    "/stream-lite-test/processing/job_id=44444444-4444-4444-8444-444444444444/output/orders.csv"
)
DESTINATION_ORDERS_ROOT = "/stream-lite-test/destinations/orders"


@pytest.fixture()
def filesystem_harness(tmp_path: Path) -> dict[str, object]:
    processing_root = tmp_path / "processing"
    destination_root = tmp_path / "destinations"
    processing_root.mkdir(parents=True, exist_ok=True)
    destination_root.mkdir(parents=True, exist_ok=True)

    def resolve(locator: str) -> Path:
        if locator == PROCESSING_ROOT or locator.startswith(f"{PROCESSING_ROOT}/"):
            suffix = locator.removeprefix(PROCESSING_ROOT).lstrip("/")
            return processing_root / suffix
        if locator == DESTINATION_ROOT or locator.startswith(f"{DESTINATION_ROOT}/"):
            suffix = locator.removeprefix(DESTINATION_ROOT).lstrip("/")
            return destination_root / suffix
        return tmp_path / "unmapped" / locator.strip("/").replace("/", "_")

    return {
        "resolve": resolve,
        "path_policy": PathPolicy(
            source_roots=(PROCESSING_ROOT,),
            destination_roots=(DESTINATION_ROOT,),
        ),
    }


def test_copy_output_to_destination_writes_final_output_and_leaves_source_unchanged(
    filesystem_harness: dict[str, object],
    tmp_path: Path,
) -> None:
    resolver = filesystem_harness["resolve"]
    path_policy = filesystem_harness["path_policy"]
    payload = b"id,total\n1,10\n"
    source_path = resolver(SOURCE_OUTPUT_LOCATOR)
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_bytes(payload)
    resolver(DESTINATION_ORDERS_ROOT).mkdir(parents=True, exist_ok=True)

    result = copy_output_to_destination(
        source_output_locator=SOURCE_OUTPUT_LOCATOR,
        destination_root_locator=DESTINATION_ORDERS_ROOT,
        watcher_id=WATCHER_ID,
        job_id=JOB_ID,
        as_of_date=date(2026, 5, 2),
        filesystem_resolver=resolver,
        path_policy=path_policy,
    )

    assert result.status == "delivered"
    assert (
        result.finalized_locator
        == "/stream-lite-test/destinations/orders/"
        "watcher_id=22222222-2222-4222-8222-222222222222/"
        "date=2026-05-02/"
        "job_id=44444444-4444-4444-8444-444444444444/"
        "output.csv"
    )
    assert (
        result.finalized_display_path
        == "/orders/"
        "watcher_id=22222222-2222-4222-8222-222222222222/"
        "date=2026-05-02/"
        "job_id=44444444-4444-4444-8444-444444444444/"
        "output.csv"
    )
    assert result.bytes_written == len(payload)
    assert result.checksum_sha256 == hashlib.sha256(payload).hexdigest()
    assert result.reason_code is None
    assert result.retryable is False

    finalized_path = resolver(result.finalized_locator)
    assert finalized_path.read_bytes() == payload
    assert source_path.read_bytes() == payload
    assert str(tmp_path) not in result.finalized_locator
    assert str(tmp_path) not in result.finalized_display_path
    assert str(tmp_path) not in result.operator_message
    assert "\\" not in result.finalized_locator


def test_copy_output_to_destination_reports_missing_source(
    filesystem_harness: dict[str, object],
) -> None:
    resolver = filesystem_harness["resolve"]
    path_policy = filesystem_harness["path_policy"]
    resolver(DESTINATION_ORDERS_ROOT).mkdir(parents=True, exist_ok=True)

    result = copy_output_to_destination(
        source_output_locator=SOURCE_OUTPUT_LOCATOR,
        destination_root_locator=DESTINATION_ORDERS_ROOT,
        watcher_id=WATCHER_ID,
        job_id=JOB_ID,
        as_of_date=date(2026, 5, 2),
        filesystem_resolver=resolver,
        path_policy=path_policy,
    )

    assert result.status == "failed"
    assert result.finalized_locator is None
    assert result.reason_code == SOURCE_TRANSFER_FAILED
    assert result.retryable is True
    assert result.bytes_written == 0


def test_copy_output_to_destination_reports_missing_destination_root(
    filesystem_harness: dict[str, object],
) -> None:
    resolver = filesystem_harness["resolve"]
    path_policy = filesystem_harness["path_policy"]
    source_path = resolver(SOURCE_OUTPUT_LOCATOR)
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_bytes(b"id,total\n1,10\n")

    result = copy_output_to_destination(
        source_output_locator=SOURCE_OUTPUT_LOCATOR,
        destination_root_locator=DESTINATION_ORDERS_ROOT,
        watcher_id=WATCHER_ID,
        job_id=JOB_ID,
        as_of_date=date(2026, 5, 2),
        filesystem_resolver=resolver,
        path_policy=path_policy,
    )

    assert result.status == "failed"
    assert result.finalized_locator is None
    assert result.reason_code == DESTINATION_NOT_FOUND
    assert result.retryable is True
    assert result.bytes_written == 0


def test_copy_output_to_destination_rejects_outside_allowlist_destination(
    filesystem_harness: dict[str, object],
) -> None:
    resolver = filesystem_harness["resolve"]
    path_policy = filesystem_harness["path_policy"]
    source_path = resolver(SOURCE_OUTPUT_LOCATOR)
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_bytes(b"id,total\n1,10\n")

    result = copy_output_to_destination(
        source_output_locator=SOURCE_OUTPUT_LOCATOR,
        destination_root_locator="/outside-allowlist/orders",
        watcher_id=WATCHER_ID,
        job_id=JOB_ID,
        as_of_date=date(2026, 5, 2),
        filesystem_resolver=resolver,
        path_policy=path_policy,
    )

    assert result.status == "failed"
    assert result.finalized_locator is None
    assert result.reason_code == DESTINATION_NOT_ALLOWLISTED
    assert result.retryable is False
    assert result.bytes_written == 0



def test_copy_output_to_destination_reports_unwritable_destination_root(
    filesystem_harness: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolver = filesystem_harness["resolve"]
    path_policy = filesystem_harness["path_policy"]
    source_path = resolver(SOURCE_OUTPUT_LOCATOR)
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_bytes(b"id,total\n1,10\n")
    resolver(DESTINATION_ORDERS_ROOT).mkdir(parents=True, exist_ok=True)
    original_open = Path.open

    def fail_staged_write(self: Path, mode: str = "r", *args, **kwargs):  # type: ignore[no-untyped-def]
        if "w" in mode and self.name.startswith(".output"):
            raise OSError(errno.EACCES, "permission denied")
        return original_open(self, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fail_staged_write)

    result = copy_output_to_destination(
        source_output_locator=SOURCE_OUTPUT_LOCATOR,
        destination_root_locator=DESTINATION_ORDERS_ROOT,
        watcher_id=WATCHER_ID,
        job_id=JOB_ID,
        as_of_date=date(2026, 5, 2),
        filesystem_resolver=resolver,
        path_policy=path_policy,
    )

    assert result.status == "failed"
    assert result.finalized_locator is None
    assert result.reason_code == DESTINATION_NOT_WRITABLE
    assert result.retryable is True
    assert result.bytes_written == 0

def test_copy_output_to_destination_returns_finalize_unsupported_when_replace_is_unavailable(
    filesystem_harness: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolver = filesystem_harness["resolve"]
    path_policy = filesystem_harness["path_policy"]
    source_path = resolver(SOURCE_OUTPUT_LOCATOR)
    source_path.parent.mkdir(parents=True, exist_ok=True)
    payload = b"id,total\n1,10\n"
    source_path.write_bytes(payload)
    resolver(DESTINATION_ORDERS_ROOT).mkdir(parents=True, exist_ok=True)

    def replace_unsupported(_self: Path, _target: Path) -> Path:
        raise OSError(errno.EXDEV, "cross-device link")

    monkeypatch.setattr(Path, "replace", replace_unsupported)

    result = copy_output_to_destination(
        source_output_locator=SOURCE_OUTPUT_LOCATOR,
        destination_root_locator=DESTINATION_ORDERS_ROOT,
        watcher_id=WATCHER_ID,
        job_id=JOB_ID,
        as_of_date=date(2026, 5, 2),
        filesystem_resolver=resolver,
        path_policy=path_policy,
    )

    assert result.status == "failed"
    assert result.finalized_locator is None
    assert result.reason_code == FINALIZE_UNSUPPORTED
    assert result.retryable is False
    assert result.bytes_written == len(payload)
