from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence
from uuid import UUID

import pytest
from jsonschema.validators import Draft202012Validator

from app.artifacts import OutputManifest
from app.delivery import OutputManifestWriter, build_destination_outcome, build_output_manifest


SCHEMA_PATH = Path("schemas/artifacts/output_manifest.schema.json")
MANIFEST_LOCATOR = (
    "/stream-lite-test/manifests/job_id=44444444-4444-4444-8444-444444444444/output_manifest.json"
)


@pytest.mark.parametrize(
    ("status", "destination_outcomes"),
    [
        (
            "delivered",
            [
                build_destination_outcome(
                    destination_folder_id=UUID("33333333-3333-4333-8333-333333333333"),
                    destination_display_path="/orders",
                    matched_route_tags=("ORDERS",),
                    status="delivered",
                    finalized_locator=(
                        "/stream-lite-test/destinations/orders/"
                        "watcher_id=22222222-2222-4222-8222-222222222222/"
                        "date=2026-05-02/"
                        "job_id=44444444-4444-4444-8444-444444444444/"
                        "output.csv"
                    ),
                    checksum_sha256="b" * 64,
                    bytes_written=42,
                )
            ],
        ),
        (
            "completed_with_delivery_errors",
            [
                build_destination_outcome(
                    destination_folder_id=UUID("33333333-3333-4333-8333-333333333333"),
                    destination_display_path="/orders",
                    matched_route_tags=("ORDERS",),
                    status="delivered",
                    finalized_locator=(
                        "/stream-lite-test/destinations/orders/"
                        "watcher_id=22222222-2222-4222-8222-222222222222/"
                        "date=2026-05-02/"
                        "job_id=44444444-4444-4444-8444-444444444444/"
                        "output.csv"
                    ),
                    checksum_sha256="b" * 64,
                    bytes_written=42,
                ),
                build_destination_outcome(
                    destination_folder_id=UUID("55555555-5555-4555-8555-555555555555"),
                    destination_display_path="/archive",
                    matched_route_tags=("ORDERS",),
                    status="failed",
                    reason_code="DESTINATION_NOT_FOUND",
                    retryable=True,
                ),
            ],
        ),
        (
            "failed",
            [
                build_destination_outcome(
                    destination_folder_id=UUID("66666666-6666-4666-8666-666666666666"),
                    destination_display_path="/archive",
                    matched_route_tags=("ORDERS",),
                    status="failed",
                    reason_code="SOURCE_TRANSFER_FAILED",
                    retryable=True,
                )
            ],
        ),
    ],
)
def test_final_output_manifests_validate_against_model_and_json_schema(
    status: str,
    destination_outcomes: Sequence[dict[str, object]],
) -> None:
    manifest = build_output_manifest(
        existing_manifest=_processed_manifest_payload(),
        destination_outcomes=destination_outcomes,
        status=status,
    )
    payload = manifest.model_dump(mode="json")

    OutputManifest.model_validate(payload)
    Draft202012Validator(
        json.loads(SCHEMA_PATH.read_text(encoding="utf-8")),
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    ).validate(payload)

    assert payload["status"] == status
    assert payload["destination_outcomes"] == list(destination_outcomes)


def test_output_manifest_writer_writes_json_without_host_paths(tmp_path: Path) -> None:
    manifest = build_output_manifest(
        existing_manifest=_processed_manifest_payload(),
        destination_outcomes=[
            build_destination_outcome(
                destination_folder_id=UUID("33333333-3333-4333-8333-333333333333"),
                destination_display_path="/orders",
                matched_route_tags=("ORDERS",),
                status="delivered",
                finalized_locator=(
                    "/stream-lite-test/destinations/orders/"
                    "watcher_id=22222222-2222-4222-8222-222222222222/"
                    "date=2026-05-02/"
                    "job_id=44444444-4444-4444-8444-444444444444/"
                    "output.csv"
                ),
                checksum_sha256="b" * 64,
                bytes_written=42,
            )
        ],
        status="delivered",
    )
    writer = OutputManifestWriter(
        filesystem_resolver=lambda locator: tmp_path / locator.strip("/")
    )

    written_manifest = writer.write_manifest(
        manifest_locator=MANIFEST_LOCATOR,
        manifest=manifest,
    )

    local_path = tmp_path / MANIFEST_LOCATOR.strip("/")
    payload = json.loads(local_path.read_text(encoding="utf-8"))

    assert written_manifest.status == "delivered"
    assert OutputManifest.model_validate(payload).status == "delivered"
    assert str(tmp_path) not in local_path.read_text(encoding="utf-8")


def _processed_manifest_payload() -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "job_id": "44444444-4444-4444-8444-444444444444",
        "watcher_id": "22222222-2222-4222-8222-222222222222",
        "source_sha256": "a" * 64,
        "processor_version": "unknown",
        "processing_summary_locator": (
            "/stream-lite-test/processing/job_id=44444444-4444-4444-8444-444444444444/"
            "processing_summary.json"
        ),
        "produced_output_locators": [
            "/stream-lite-test/processing/job_id=44444444-4444-4444-8444-444444444444/output/orders.csv"
        ],
        "started_at": "2026-05-02T16:00:00Z",
        "completed_at": "2026-05-02T16:00:02Z",
        "duration_seconds": 2,
        "destination_outcomes": [],
        "status": "processed",
        "created_at": "2026-05-02T16:00:02Z",
        "correlation_id": "11111111-1111-4111-8111-111111111111",
    }
