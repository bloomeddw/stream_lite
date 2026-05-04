from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from app.artifacts import OutputManifest, ProcessingSummary
from app.processing import ProcessingAdapterInput, SparkDemoAdapter


@pytest.fixture()
def workspace_path(tmp_path: Path) -> Path:
    return tmp_path


def test_csv_input_preserves_rows_and_writes_valid_artifacts(workspace_path: Path) -> None:
    harness = _make_adapter_harness(workspace_path)
    source_path = harness["local_source_root"] / "orders.csv"
    source_path.write_text("id,total\n1,10\n2,20\n", encoding="utf-8", newline="")

    result = harness["adapter"].run_demo_transform(_build_input(harness, "orders.csv"))

    output_path = _resolve_local_path(harness, result.output_locator)
    summary_path = _resolve_local_path(harness, result.summary_locator)
    manifest_path = _resolve_local_path(harness, result.manifest_locator)
    summary_payload = json.loads(summary_path.read_text(encoding="utf-8"))
    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert result.status == "processed"
    assert result.row_count == 2
    assert result.record_count == 2
    assert output_path.read_text(encoding="utf-8") == "id,total\n1,10\n2,20\n"
    summary = ProcessingSummary.model_validate(summary_payload)
    assert summary.status == "processed"
    assert summary.source_sha256 == "c" * 64
    assert summary.processor_version == result.engine_version
    manifest = OutputManifest.model_validate(manifest_payload)
    assert manifest.status == "processed"
    assert manifest.processor_version == result.engine_version
    assert manifest.produced_output_locators == [result.output_locator]
    assert manifest.started_at == "2026-05-02T14:00:00Z"
    assert manifest.completed_at == "2026-05-02T14:00:01Z"
    assert manifest.duration_seconds == 1
    assert str(workspace_path) not in summary_path.read_text(encoding="utf-8")
    assert str(workspace_path) not in manifest_path.read_text(encoding="utf-8")


def test_json_input_writes_deterministic_pretty_json(workspace_path: Path) -> None:
    harness = _make_adapter_harness(workspace_path)
    source_path = harness["local_source_root"] / "payload.json"
    source_path.write_text('[{"b":2,"a":1},{"d":4,"c":3}]', encoding="utf-8")

    result = harness["adapter"].run_demo_transform(_build_input(harness, "payload.json"))

    output_text = _resolve_local_path(harness, result.output_locator).read_text(encoding="utf-8")
    assert result.status == "processed"
    assert result.row_count is None
    assert result.record_count == 2
    assert output_text == '[\n  {\n    "a": 1,\n    "b": 2\n  },\n  {\n    "c": 3,\n    "d": 4\n  }\n]\n'


def test_txt_input_copies_content_unchanged(workspace_path: Path) -> None:
    harness = _make_adapter_harness(workspace_path)
    source_path = harness["local_source_root"] / "notes.txt"
    source_path.write_text("alpha\nbeta\n", encoding="utf-8")

    result = harness["adapter"].run_demo_transform(_build_input(harness, "notes.txt"))

    output_text = _resolve_local_path(harness, result.output_locator).read_text(encoding="utf-8")
    assert result.status == "processed"
    assert result.row_count == 2
    assert result.record_count == 2
    assert output_text == "alpha\nbeta\n"


def test_missing_input_returns_retryable_unavailable_failure(workspace_path: Path) -> None:
    harness = _make_adapter_harness(workspace_path)

    result = harness["adapter"].run_demo_transform(_build_input(harness, "missing.csv"))

    assert result.status == "failed"
    assert result.error_code == "PROCESSING_INPUT_UNAVAILABLE"
    assert result.retryable is True


def test_malformed_json_returns_non_retryable_invalid_failure(workspace_path: Path) -> None:
    harness = _make_adapter_harness(workspace_path)
    source_path = harness["local_source_root"] / "broken.json"
    source_path.write_text("{", encoding="utf-8")

    result = harness["adapter"].run_demo_transform(_build_input(harness, "broken.json"))

    assert result.status == "failed"
    assert result.error_code == "PROCESSING_INPUT_INVALID"
    assert result.retryable is False


def _make_adapter_harness(tmp_path: Path):
    local_source_root = tmp_path / "source"
    local_processing_root = tmp_path / "processing"
    local_source_root.mkdir(parents=True, exist_ok=True)
    local_processing_root.mkdir(parents=True, exist_ok=True)

    container_source_root = "/stream-lite-test/source"
    container_processing_root = "/stream-lite-test/processing"

    def resolver(container_locator: str):
        if container_locator == container_source_root or container_locator.startswith(f"{container_source_root}/"):
            return local_source_root / container_locator.removeprefix(container_source_root).lstrip("/")
        if container_locator == container_processing_root or container_locator.startswith(f"{container_processing_root}/"):
            return local_processing_root / container_locator.removeprefix(container_processing_root).lstrip("/")
        return container_locator

    base_time = datetime(2026, 5, 2, 14, 0, 0, tzinfo=timezone.utc)

    class Clock:
        def __init__(self) -> None:
            self.calls = 0

        def now(self) -> datetime:
            value = base_time + timedelta(seconds=self.calls + 1)
            self.calls += 1
            return value

    clock = Clock()
    adapter = SparkDemoAdapter(
        processing_root=container_processing_root,
        filesystem_resolver=resolver,
        clock=clock.now,
    )
    return {
        "adapter": adapter,
        "container_processing_root": container_processing_root,
        "container_source_root": container_source_root,
        "local_processing_root": local_processing_root,
        "local_source_root": local_source_root,
    }


def _build_input(harness, file_name: str) -> ProcessingAdapterInput:  # type: ignore[no-untyped-def]
    started_at = datetime(2026, 5, 2, 14, 0, 0, tzinfo=timezone.utc)
    return ProcessingAdapterInput(
        job_id=uuid4(),
        watcher_id=uuid4(),
        correlation_id=uuid4(),
        input_locator=f"{harness['container_source_root']}/{file_name}",
        source_file_name=file_name,
        source_extension=Path(file_name).suffix,
        source_sha256="c" * 64,
        started_at=started_at,
        source_display_path=f"/source/{file_name}",
    )


def _resolve_local_path(harness, locator: str | None) -> Path:  # type: ignore[no-untyped-def]
    if locator is None:
        raise AssertionError("expected locator to be present")
    return Path(harness["adapter"].filesystem_resolver(locator))
