from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from jsonschema import Draft202012Validator

from app.config.path_policy import PathPolicy
from app.config.settings import StreamLiteSettings
from app.validation import QuarantineService


def test_quarantine_copy_preserves_original_source_and_layout(tmp_path) -> None:
    service, paths = _make_quarantine_service(tmp_path)
    watcher_id = uuid4()
    job_id = uuid4()
    correlation_id = str(uuid4())
    source_path = paths["local_source_root"] / "orders.csv"
    source_content = "a,b\n1,2\n"
    source_path.write_bytes(source_content.encode("utf-8"))

    result = service.quarantine_file(
        job_id=job_id,
        watcher_id=watcher_id,
        source_container_locator=f"{paths['container_source_root']}/orders.csv",
        source_display_path="/source-a/orders.csv",
        source_file_name="orders.csv",
        source_sha256="a" * 64,
        reason_codes=["SCHEMA_INVALID"],
        operator_message="Source file /source-a/orders.csv failed structured-format validation.",
        correlation_id=correlation_id,
    )

    expected_local_dir = (
        paths["local_quarantine_root"]
        / f"watcher_id={watcher_id}"
        / "date=2026-05-01"
        / f"job_id={job_id}"
    )
    copied_file = expected_local_dir / "orders.csv"
    artifact_path = expected_local_dir / "quarantine_record.json"

    assert source_path.read_text(encoding="utf-8") == source_content
    assert copied_file.read_text(encoding="utf-8") == source_content
    assert artifact_path.exists()
    assert result.quarantine_locator.endswith(f"/watcher_id={watcher_id}/date=2026-05-01/job_id={job_id}/orders.csv")
    assert result.quarantine_display_path == f"/watcher_id={watcher_id}/date=2026-05-01/job_id={job_id}/orders.csv"
    assert result.copied_size_bytes == len(source_content.encode("utf-8"))


def test_quarantine_record_artifact_validates_and_hides_host_paths(tmp_path) -> None:
    service, paths = _make_quarantine_service(tmp_path)
    watcher_id = uuid4()
    job_id = uuid4()
    correlation_id = str(uuid4())
    source_path = paths["local_source_root"] / "broken.json"
    source_path.write_text("{", encoding="utf-8")

    result = service.quarantine_file(
        job_id=job_id,
        watcher_id=watcher_id,
        source_container_locator=f"{paths['container_source_root']}/broken.json",
        source_display_path="/source-a/broken.json",
        source_file_name="broken.json",
        source_sha256="b" * 64,
        reason_codes=["SCHEMA_INVALID"],
        operator_message="Source file /source-a/broken.json failed structured-format validation.",
        correlation_id=correlation_id,
    )

    schema = json.loads((paths["repo_root"] / "schemas" / "artifacts" / "quarantine_record.schema.json").read_text(encoding="utf-8"))
    artifact_path = (
        paths["local_quarantine_root"]
        / f"watcher_id={watcher_id}"
        / "date=2026-05-01"
        / f"job_id={job_id}"
        / "quarantine_record.json"
    )
    artifact_payload = json.loads(artifact_path.read_text(encoding="utf-8"))

    Draft202012Validator(schema).validate(artifact_payload)
    assert result.artifact_payload == artifact_payload
    assert str(tmp_path) not in json.dumps(artifact_payload)


def _make_quarantine_service(tmp_path):
    local_source_root = tmp_path / "sources" / "source-a"
    local_output_root = tmp_path / "outputs"
    local_quarantine_root = tmp_path / "quarantine"
    local_source_root.mkdir(parents=True, exist_ok=True)
    local_output_root.mkdir(parents=True, exist_ok=True)
    local_quarantine_root.mkdir(parents=True, exist_ok=True)

    container_base = f"/stream-lite-test/{tmp_path.name}"
    container_watch_root = f"{container_base}/sources"
    container_source_root = f"{container_watch_root}/source-a"
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
        max_file_size_mb=100,
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
        if container_path == container_watch_root or container_path.startswith(f"{container_watch_root}/"):
            return local_source_root.parent / container_path.removeprefix(container_watch_root).lstrip("/")
        if container_path == container_quarantine_root or container_path.startswith(f"{container_quarantine_root}/"):
            return local_quarantine_root / container_path.removeprefix(container_quarantine_root).lstrip("/")
        if container_path == container_output_root or container_path.startswith(f"{container_output_root}/"):
            return local_output_root / container_path.removeprefix(container_output_root).lstrip("/")
        return container_path

    service = QuarantineService(
        settings=settings,
        path_policy=path_policy,
        filesystem_resolver=filesystem_resolver,
        now=lambda: datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc),
    )
    return service, {
        "container_source_root": container_source_root,
        "local_source_root": local_source_root,
        "local_quarantine_root": local_quarantine_root,
        "repo_root": Path(__file__).resolve().parents[2],
    }
