from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.api.schemas import API_MODEL_BY_SCHEMA_NAME
from app.artifacts import ARTIFACT_MODEL_BY_SCHEMA_NAME
from app.events import EVENT_MODEL_BY_SCHEMA_NAME

REPO_ROOT = Path(__file__).resolve().parents[2]

MODEL_REGISTRIES = {
    "api": API_MODEL_BY_SCHEMA_NAME,
    "artifacts": ARTIFACT_MODEL_BY_SCHEMA_NAME,
    "events": EVENT_MODEL_BY_SCHEMA_NAME,
}


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _schema_name_from_path(path: Path) -> str:
    if path.name.endswith(".schema.json"):
        return path.name.removesuffix(".schema.json")
    return path.name.split(".")[0]


def _case_name_from_example(path: Path) -> str:
    return path.name.split(".")[1]


def _iter_schema_paths(family: str) -> list[Path]:
    return sorted((REPO_ROOT / "schemas" / family).glob("*.schema.json"))


def _iter_example_paths(family: str) -> list[Path]:
    return sorted((REPO_ROOT / "schemas" / "examples" / family).glob("*.json"))


@pytest.mark.parametrize("family", sorted(MODEL_REGISTRIES))
def test_model_registry_covers_every_schema_file(family: str) -> None:
    registry = MODEL_REGISTRIES[family]
    schema_names = {_schema_name_from_path(path) for path in _iter_schema_paths(family)}
    assert set(registry) == schema_names


@pytest.mark.parametrize(
    ("family", "schema_path"),
    [
        (family, schema_path)
        for family in sorted(MODEL_REGISTRIES)
        for schema_path in _iter_schema_paths(family)
    ],
)
def test_model_json_schema_titles_match_contract_titles(family: str, schema_path: Path) -> None:
    schema_name = _schema_name_from_path(schema_path)
    schema = _load_json(schema_path)
    model_cls = MODEL_REGISTRIES[family][schema_name]

    assert model_cls.model_json_schema()["title"] == schema["title"]


@pytest.mark.parametrize(
    ("family", "example_path"),
    [
        (family, example_path)
        for family in sorted(MODEL_REGISTRIES)
        for example_path in _iter_example_paths(family)
        if _case_name_from_example(example_path) == "valid"
    ],
)
def test_valid_examples_validate_and_preserve_schema_field_names(
    family: str,
    example_path: Path,
) -> None:
    schema_name = _schema_name_from_path(example_path)
    payload = _load_json(example_path)
    model_cls = MODEL_REGISTRIES[family][schema_name]

    model = model_cls.model_validate(payload)

    assert model.model_dump(mode="json", exclude_unset=True) == payload


@pytest.mark.parametrize(
    ("family", "example_path"),
    [
        (family, example_path)
        for family in sorted(MODEL_REGISTRIES)
        for example_path in _iter_example_paths(family)
        if _case_name_from_example(example_path).startswith("invalid")
    ],
)
def test_invalid_examples_fail_validation(family: str, example_path: Path) -> None:
    schema_name = _schema_name_from_path(example_path)
    payload = _load_json(example_path)
    model_cls = MODEL_REGISTRIES[family][schema_name]

    with pytest.raises(ValidationError):
        model_cls.model_validate(payload)
