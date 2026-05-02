#!/usr/bin/env python3
"""Static contract lint checks for Stream Lite requirement and schema artifacts.

This script is intentionally dependency-free so it can run before implementation
packages are installed. It checks traceability and contract parity; it is not a
runtime implementation module.
"""

from __future__ import annotations

import argparse
import os
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

REQ_ROW_RE = re.compile(r"^\|\s*(SL-[A-Z0-9]+(?:-[A-Z0-9]+)*-\d{3})\s*\|")
REQ_REF_RE = re.compile(r"(?<!V-)(SL-[A-Z0-9]+(?:-[A-Z0-9]+)*-\d{3})")
VERIFY_REF_RE = re.compile(r"V-SL-[A-Z0-9]+(?:-[A-Z0-9]+)*-\d{3}")
METRIC_NAME_RE = re.compile(r"`(stream_lite_[a-z0-9_]+)`")
METRIC_DURATION_MS_RE = re.compile(r"stream_lite_[a-z0-9_]*duration_ms")
ENV_RE = re.compile(r"^(STREAM_LITE_[A-Z0-9_]+)=")
ENV_DOC_RE = re.compile(r"^\|\s*`(STREAM_LITE_[A-Z0-9_]+)`\s*\|")
SCHEMA_FILE_RE = re.compile(r"`(schemas/(?:api|events)/[a-z0-9_]+\.schema\.json)`")
CAMEL_RE_1 = re.compile(r"(.)([A-Z][a-z]+)")
CAMEL_RE_2 = re.compile(r"([a-z0-9])([A-Z])")
RFC3339_PATTERN = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$"
PATH_FIELD_NAMES = {"path", "normalized_path", "display_path", "root"}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def iter_text_files(root: Path):
    for path in sorted(root.rglob("*")):
        path_text = path.as_posix()
        if any(
            excluded in path_text
            for excluded in (
                "/.idea/",
                "/.pytest_vendor/",
                "/pytest_vendor/",
                "/wheelhouse/",
                "/.venv/",
                "/docs/_build/",
                "/.pytest_cache/",
            )
        ):
            continue
        if path.is_file() and path.suffix.lower() in {".md", ".rst", ".txt", ".json", ".example", ".py", ".yml", ".yaml"}:
            yield path


def camel_to_snake(name: str) -> str:
    s = CAMEL_RE_1.sub(r"\1_\2", name)
    s = CAMEL_RE_2.sub(r"\1_\2", s)
    return s.lower()


def collect_requirement_rows(root: Path):
    rows = defaultdict(list)
    for path in sorted((root / "docs" / "reqs").glob("REQ-*.md")):
        for line_no, line in enumerate(read_text(path).splitlines(), 1):
            m = REQ_ROW_RE.match(line)
            if m:
                rows[m.group(1)].append((path, line_no))
    return rows


def collect_requirement_references(root: Path):
    refs = defaultdict(list)
    for path in iter_text_files(root):
        if "/.idea/" in path.as_posix():
            continue
        text = read_text(path)
        for line_no, line in enumerate(text.splitlines(), 1):
            line_without_verifications = VERIFY_REF_RE.sub("", line)
            for ref in REQ_REF_RE.findall(line_without_verifications):
                refs[ref].append((path, line_no))
    return refs


def check_json(root: Path):
    errors = []
    for path in sorted((root / "schemas").rglob("*.json")):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{path}: invalid JSON: {exc}")
    return errors


def check_schema_examples(root: Path):
    errors = []
    examples = root / "schemas" / "examples"
    for family in ["api", "events", "artifacts"]:
        schema_dir = root / "schemas" / family
        example_dir = examples / family
        if not example_dir.exists():
            errors.append(f"missing example directory: {example_dir}")
            continue
        for schema_path in sorted(schema_dir.glob("*.schema.json")):
            stem = schema_path.name.removesuffix(".schema.json")
            example_cases = {
                path.name.split(".")[1]
                for path in example_dir.glob(f"{stem}.*.json")
                if len(path.name.split(".")) >= 3
            }
            valid = example_dir / f"{stem}.valid.json"
            invalid = example_dir / f"{stem}.invalid.json"
            if not valid.exists():
                errors.append(f"missing valid example for {schema_path}: {valid}")
            if not invalid.exists():
                errors.append(f"missing invalid example for high-risk schema {schema_path}: {invalid}")
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            if schema_contains_enum_contract(schema) and "invalid_enum" not in example_cases:
                errors.append(
                    f"missing invalid_enum example for schema with enum/pattern-coded status fields: {schema_path}"
                )
            if schema_contains_timestamp_contract(schema) and "invalid_timestamp" not in example_cases:
                errors.append(
                    f"missing invalid_timestamp example for schema with serialized timestamps: {schema_path}"
                )
            if schema_contains_path_contract(schema) and "invalid_path" not in example_cases:
                errors.append(
                    f"missing invalid_path example for schema with operator-facing paths or locators: {schema_path}"
                )
    return errors


def check_metric_units(root: Path):
    errors = []
    for path in iter_text_files(root):
        if path.as_posix().startswith((root / "schemas" / "examples").as_posix()):
            continue
        for line_no, line in enumerate(read_text(path).splitlines(), 1):
            if METRIC_DURATION_MS_RE.search(line):
                errors.append(f"{path}:{line_no}: duration metric must use _duration_seconds")
    return errors


def parse_markdown_table_rows(path: Path):
    rows = []
    for line_no, line in enumerate(read_text(path).splitlines(), 1):
        if not line.startswith("|") or "---" in line:
            continue
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        rows.append((line_no, cols))
    return rows


def schema_contains_enum_contract(node):
    if isinstance(node, dict):
        if "enum" in node or "const" in node:
            return True
        return any(schema_contains_enum_contract(value) for value in node.values())
    if isinstance(node, list):
        return any(schema_contains_enum_contract(item) for item in node)
    return False


def schema_contains_timestamp_contract(node):
    if isinstance(node, dict):
        if node.get("format") == "date-time" or node.get("pattern") == RFC3339_PATTERN:
            return True
        return any(schema_contains_timestamp_contract(value) for value in node.values())
    if isinstance(node, list):
        return any(schema_contains_timestamp_contract(item) for item in node)
    return False


def schema_contains_path_contract(node, *, current_key=None):
    if isinstance(node, dict):
        if current_key and (
            current_key in PATH_FIELD_NAMES
            or current_key.endswith("_path")
            or current_key.endswith("_locator")
        ):
            return True
        return any(
            schema_contains_path_contract(value, current_key=key)
            for key, value in node.items()
        )
    if isinstance(node, list):
        return any(schema_contains_path_contract(item) for item in node)
    return False


def check_api_schema_parity(root: Path):
    errors = []
    endpoint_doc = root / "docs" / "api" / "endpoints.md"
    api_schema_doc = root / "docs" / "schemas" / "api_schemas.md"
    schema_dir = root / "schemas" / "api"

    available_files = {p.name for p in schema_dir.glob("*.schema.json")}
    documented_schema_names = set()
    documented_files = set()
    for _line_no, cols in parse_markdown_table_rows(api_schema_doc):
        if cols and cols[0] in {"Schema", "Type"}:
            continue
        if len(cols) >= 2 and cols[1].startswith("`schemas/api/"):
            schema_name = cols[0].strip("`")
            file_name = Path(cols[1].strip("`")).name
            documented_schema_names.add(schema_name)
            documented_files.add(file_name)
            expected = f"{camel_to_snake(schema_name)}.schema.json"
            if file_name != expected:
                errors.append(f"{api_schema_doc}: schema {schema_name} maps to {file_name}, expected {expected}")
            if file_name not in available_files:
                errors.append(f"{api_schema_doc}: documented API schema file missing: {file_name}")

    for schema_file in available_files:
        if schema_file not in documented_files:
            errors.append(f"{schema_dir / schema_file}: API schema file is not documented in docs/schemas/api_schemas.md")

    for line_no, cols in parse_markdown_table_rows(endpoint_doc):
        if len(cols) < 6 or cols[0] == "Method":
            continue
        request_schema = cols[3].strip("`")
        success_schema = cols[4].strip("`")
        for schema_name in [request_schema, success_schema]:
            if schema_name in {"none", "query", "path", "n/a", ""}:
                continue
            file_name = f"{camel_to_snake(schema_name)}.schema.json"
            if file_name not in available_files:
                errors.append(f"{endpoint_doc}:{line_no}: endpoint references missing API schema file {file_name} for {schema_name}")
            if schema_name not in documented_schema_names:
                errors.append(f"{endpoint_doc}:{line_no}: endpoint references schema not documented in api_schemas.md: {schema_name}")
    return errors


def check_event_schema_parity(root: Path):
    errors = []
    event_doc = root / "docs" / "schemas" / "events.md"
    schema_dir = root / "schemas" / "events"
    available = {p.name: p for p in schema_dir.glob("*.schema.json")}
    documented_files = set()

    for line_no, cols in parse_markdown_table_rows(event_doc):
        if len(cols) < 6 or cols[0] == "Event type":
            continue
        event_type = cols[0].strip("`")
        schema_path_text = cols[5].strip("`")
        if not schema_path_text.startswith("stream_lite/schemas/events/"):
            continue
        schema_file = Path(schema_path_text).name
        documented_files.add(schema_file)
        schema_path = available.get(schema_file)
        if schema_path is None:
            errors.append(f"{event_doc}:{line_no}: documented event schema file missing: {schema_file}")
            continue
        try:
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{schema_path}: invalid JSON: {exc}")
            continue
        actual_const = schema.get("properties", {}).get("event_type", {}).get("const")
        if actual_const != event_type:
            errors.append(f"{schema_path}: event_type const {actual_const!r} does not match docs value {event_type!r}")

    for schema_file in available:
        if schema_file not in documented_files:
            errors.append(f"{schema_dir / schema_file}: event schema file is not documented in docs/schemas/events.md")
    return errors


def check_artifact_schema_parity(root: Path):
    errors = []
    artifact_doc = root / "docs" / "schemas" / "artifact_schemas.md"
    schema_dir = root / "schemas" / "artifacts"

    available_files = {path.name for path in schema_dir.glob("*.schema.json")}
    documented_schema_names = set()
    documented_files = set()
    for _line_no, cols in parse_markdown_table_rows(artifact_doc):
        if cols and cols[0] == "Schema":
            continue
        if len(cols) >= 2 and cols[1].startswith("`schemas/artifacts/"):
            schema_name = cols[0].strip("`")
            file_name = Path(cols[1].strip("`")).name
            documented_schema_names.add(schema_name)
            documented_files.add(file_name)
            expected = f"{camel_to_snake(schema_name)}.schema.json"
            if file_name != expected:
                errors.append(
                    f"{artifact_doc}: schema {schema_name} maps to {file_name}, expected {expected}"
                )
            if file_name not in available_files:
                errors.append(
                    f"{artifact_doc}: documented artifact schema file missing: {file_name}"
                )

    for schema_file in available_files:
        if schema_file not in documented_files:
            errors.append(
                f"{schema_dir / schema_file}: artifact schema file is not documented in docs/schemas/artifact_schemas.md"
            )
    return errors


def check_env_var_parity(root: Path):
    errors = []
    env_file = root / ".env.example"
    env_doc = root / "docs" / "operations" / "environment_variables.md"
    env_vars = {m.group(1) for line in read_text(env_file).splitlines() if (m := ENV_RE.match(line.strip()))}
    doc_vars = {m.group(1) for line in read_text(env_doc).splitlines() if (m := ENV_DOC_RE.match(line))}
    for name in sorted(env_vars - doc_vars):
        errors.append(f"{env_file}: {name} is present in .env.example but missing from environment_variables.md")
    for name in sorted(doc_vars - env_vars):
        errors.append(f"{env_doc}: {name} is documented but missing from .env.example")
    return errors


def check_metrics_catalog_parity(root: Path):
    errors = []
    catalog = root / "docs" / "operations" / "prometheus_metrics.md"
    catalog_metrics = set()
    for _line_no, cols in parse_markdown_table_rows(catalog):
        if cols and cols[0].startswith("`stream_lite_"):
            catalog_metrics.add(cols[0].strip("`"))
    for path in iter_text_files(root):
        if path == catalog or path.as_posix().startswith((root / "schemas" / "examples").as_posix()):
            continue
        for line_no, line in enumerate(read_text(path).splitlines(), 1):
            for metric in METRIC_NAME_RE.findall(line):
                if metric.startswith("stream_lite_") and metric not in catalog_metrics:
                    errors.append(f"{path}:{line_no}: metric {metric} is referenced but missing from prometheus_metrics.md")
    return errors


def render_inventory(root: Path, rows, refs, duplicates, unresolved) -> str:
    lines = [
        "# Requirement Reference Inventory",
        "",
        "Generated by `tools/contract_lint.py --write-inventory`.",
        "",
        "## Summary",
        "",
        "| Check | Count |",
        "|---|---:|",
        f"| Unique requirement references scanned | {len(refs)} |",
        f"| Active requirement rows found | {len(rows)} |",
        f"| Unresolved requirement references | {len(unresolved)} |",
        f"| Duplicate active requirement rows | {len(duplicates)} |",
        "",
        "## Unresolved References",
        "",
    ]
    if unresolved:
        lines += ["| Requirement ID | References |", "|---|---|"]
        for rid in sorted(unresolved):
            locs = "; ".join(f"{p.relative_to(root)}:{n}" for p, n in refs[rid][:5])
            lines.append(f"| `{rid}` | {locs} |")
    else:
        lines.append("No unresolved requirement references were found.")
    lines += ["", "## Duplicate Active Rows", ""]
    if duplicates:
        lines += ["| Requirement ID | Definitions |", "|---|---|"]
        for rid, loc_list in sorted(duplicates.items()):
            locs = "; ".join(f"{p.relative_to(root)}:{n}" for p, n in loc_list)
            lines.append(f"| `{rid}` | {locs} |")
    else:
        lines.append("No duplicate active requirement rows were found.")
    lines += ["", "## Notes", "", "Verification IDs prefixed with `V-SL-` are intentionally excluded from missing-requirement checks.", ""]
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="Repository root, default current directory")
    parser.add_argument("--write-inventory", action="store_true", help="Rewrite docs/reqs/REQUIREMENT_REFERENCE_INVENTORY.md")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()

    rows = collect_requirement_rows(root)
    refs = collect_requirement_references(root)
    duplicates = {rid: locs for rid, locs in rows.items() if len(locs) > 1}
    unresolved = {rid: locs for rid, locs in refs.items() if rid not in rows}

    errors = []
    errors += [f"duplicate requirement {rid}: {locs}" for rid, locs in duplicates.items()]
    errors += [f"unresolved requirement {rid}: {locs[:3]}" for rid, locs in unresolved.items()]
    errors += check_json(root)
    errors += check_schema_examples(root)
    errors += check_metric_units(root)
    errors += check_api_schema_parity(root)
    errors += check_event_schema_parity(root)
    errors += check_artifact_schema_parity(root)
    errors += check_env_var_parity(root)
    errors += check_metrics_catalog_parity(root)

    if args.write_inventory:
        out = root / "docs" / "reqs" / "REQUIREMENT_REFERENCE_INVENTORY.md"
        out.write_text(render_inventory(root, rows, refs, duplicates, unresolved), encoding="utf-8")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        sys.stderr.flush()
        os._exit(1)
    print("contract_lint passed")
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
