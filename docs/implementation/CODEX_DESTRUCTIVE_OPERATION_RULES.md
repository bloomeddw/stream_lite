# Codex Destructive Operation Rules

## Purpose

This document defines repository-safety rules for Stream Lite implementation agents. It exists because a completed Codex session reported that verification had passed and then a later cleanup step removed repository files. These rules prevent cleanup from becoming destructive work.

## Related requirements

- `SL-REQ-003`: every requirements-changing patch includes a worklog.
- `SL-DECOMP-010`: implementation planning does not assign code tasks until contracts are defined.
- `SL-VER-031`: readiness gates require contract lint, schema validation, Sphinx where applicable, and recorded gaps.

## Required agent files

- `AGENTS.md` at the repository root is the first file agents must read.
- `RULES.md` at the repository root contain Codex-specific safety rules.
- This document is the human-readable implementation reference for destructive-operation prevention.

## Non-negotiable rules

1. Agents SHALL NOT run broad recursive delete commands from the repository root.
2. Agents SHALL NOT run targeted-looking cleanup loops that delete paths under the repository root.
3. Agents SHALL NOT use repository reset commands as a cleanup mechanism.
4. Agents SHALL NOT delete `.venv/` from a user working copy.
5. Agents SHALL NOT delete source, docs, schemas, tests, migrations, requirements, `.env.example`, evidence, or worklogs during packaging.
6. Agents SHALL create zip patches from explicit changed-file include lists instead of cleaning the full working tree.
7. Agents SHALL record exact verification commands and results before final handoff.
8. Agents SHALL stop if unexpected deleted files appear in `git status --short`.

## Forbidden command examples

The following command shapes are forbidden unless the user explicitly requests destructive recovery and names the exact target:

```text
rm -rf .
rm -rf *
git clean -fd
git clean -fdx
git reset --hard
Remove-Item -Recurse
Remove-Item -Force -Recurse
rd /s
rmdir /s
del /s
Get-ChildItem -Recurse | Remove-Item
find . -delete
find . -exec rm
```

Equivalent aliases, scripts, and shell pipelines are also forbidden.

## Targeted cleanup loop ban

This is not a corner case: a cleanup command that lists generated paths but performs recursive deletion from the repo root is still destructive and forbidden.

A prior WP-07 command used this shape:

```text
$root = (Resolve-Path '.').Path
$targets = @((Join-Path $root 'docs\\_build'), ...)
foreach ($target in $targets) { Remove-Item -LiteralPath $target -Recurse -Force }
Get-ChildItem -LiteralPath $root -Recurse ... | ForEach-Object { Remove-Item ... }
```

That pattern is forbidden because it:

- runs after successful verification,
- deletes from the user's working tree instead of excluding from a zip,
- can include `.venv` or evidence by mistake,
- can delete recursively discovered files such as `__pycache__` and `*.pyc`, and
- makes it hard to prove what was removed after Codex exits.

Agents SHALL NOT run commands that combine any of these terms inside the repository:

```text
$root
$PWD
Resolve-Path '.'
Join-Path $root
$targets = @(...)
$paths = @(...)
foreach (...) { Remove-Item ... }
Get-ChildItem -Recurse ... Remove-Item
Remove-Item -LiteralPath ... -Recurse
Remove-Item -LiteralPath ... -Force
```

## Safe packaging approach

Use an explicit file list for the patch. Example intent:

```text
zip patch.zip AGENTS.md RULES.md  docs/implementation/CODEX_DESTRUCTIVE_OPERATION_RULES.md
```

Inspect the zip contents. Do not delete the repository to remove generated files from the archive.

## Generated-artifact exclusion list

Generated artifacts may be excluded from packaging:

```text
docs/_build/
.pytest_cache/
__pycache__/
*.pyc
.tmp/
tmp/
.pytest_vendor/
pytest_vendor/
wheelhouse/
pytest-cache-files-*/
```

These paths are an **exclusion list**, not a deletion allowlist. Removal from the user's working copy is not part of normal packaging. Removal of `.venv/` from a user working copy is never allowed for packaging. Exclude it from packaging instead.

## Evidence and worklog protection

Verification evidence is part of the implementation record. Agents SHALL NOT delete:

```text
docs/verification/evidence/**
docs/verification/evidence_index.md
docs/worklogs/**
docs/reqs/REQUIREMENT_REFERENCE_INVENTORY.md
```

If evidence should not be in a patch zip, exclude it from the zip rather than deleting it from disk.

## Recovery checklist

If accidental deletion occurs:

1. Stop all implementation work.
2. Capture current path and status:
   - `pwd`
   - `git status --short`
   - `git status --ignored --short`
3. Capture the last destructive command if available.
4. Restore from the latest known-good zip/source control.
5. Reapply only the intended patch files.
6. Add a worklog describing the incident and recovery evidence, unless the user explicitly asks only for rules/instruction changes and says not to create a worklog.

## Acceptance criteria

This safety layer is accepted when:

- `AGENTS.md` exists at repository root.
- `RULES.md` exists at repository root.
- `docs/implementation/CODEX_DESTRUCTIVE_OPERATION_RULES.md` is linked from implementation docs.
- `python -S tools/contract_lint.py --write-inventory` passes.
