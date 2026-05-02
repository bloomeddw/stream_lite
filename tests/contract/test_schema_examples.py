"""Executable JSON Schema fixture validation tests.

These tests are contract verification tests, not runtime implementation tests.
They require the development dependencies declared in `requirements-dev.txt`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("jsonschema")

from tools.validate_schema_examples import validate_all


def test_all_schema_examples_match_expected_validity() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    results = validate_all(repo_root)
    failures = [result for result in results if not result.passed]
    assert failures == []


def test_schema_example_suite_is_not_empty() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    results = validate_all(repo_root)
    assert results, "schema fixture validation suite must include at least one example"
