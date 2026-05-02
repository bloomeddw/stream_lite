# Stream Lite Agent Safety Rules

These repo-owned rules exist to prevent accidental repository deletion and high-token, high-risk cleanup behavior for every future Stream Lite work package. They apply to Codex, ChatGPT, shell agents, and any automated helper. They are subordinate to user instructions only when the user explicitly asks for destructive recovery and names the exact files or directories to remove.

## 1. Work in small, reversible patches

- Change only the files required by the current work package.
- Prefer direct edits to named files over generated rewrites.
- Do not reformat unrelated files.
- Do not include prompts in zip patches.
- Always add or update a worklog for non-trivial product/code/docs behavior changes, unless the user explicitly says not to create one for an instruction-only safety patch.

## 1a. Critical safety addendum for all future work

- Do not delete files from the working tree as a cleanup step.
- Cleanup means excluding generated, cache, and vendor files from the final zip, not deleting them from the repo.
- Do not delete `.venv`, `.pytest_vendor`, `pytest_vendor`, `docs/_build`, `.pytest_cache`, `__pycache__`, `tmp`, `.tmp`, `wheelhouse`, or `*.pyc` from the user workspace.
- If generated/cache files exist, ignore them when building the patch zip.
- If you believe deletion is required, stop and report the exact file list and reason. Do not execute deletion.
- Do not use `git reset`, `git checkout`, or `git clean` to discard local work.

## 2. No broad deletion

Forbidden commands and patterns:

```text
rm -rf .
rm -rf *
rm -rf stream_lite
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

Do not run any equivalent command, alias, script, or shell pipeline from the repo root.

## 3. Targeted cleanup loop ban

A prior run used a targeted-looking PowerShell cleanup command that built a `$targets` list from `$root = Resolve-Path '.'` and then ran `Remove-Item -Recurse -Force` for generated folders. It also included `.venv` and damaged the working copy. That exact command shape is forbidden for every future work package.

Do not run commands that combine any of the following inside the repo:

```text
$root = Resolve-Path '.'
$PWD
Join-Path $root
$targets = @(...)
$paths = @(...)
foreach ($target in $targets) { Remove-Item ... }
foreach ($path in $paths) { Remove-Item ... }
Get-ChildItem -Recurse ... Remove-Item
Remove-Item -LiteralPath ... -Recurse
Remove-Item -LiteralPath ... -Force
```

This ban applies even if the list appears to contain only generated artifacts. Cleanup must happen through patch-zip exclusion, not by deleting the working tree.

## 4. Packaging without deleting

To exclude generated artifacts from a zip, build the zip from an explicit include list. Do not delete the working tree first.

Safe include categories:

```text
AGENTS.md
RULES.md
app/**/*.py
schemas/**/*.json
tests/**/*.py
docs/**/*.md
docs/**/*.rst
docs/conf.py
docs/Makefile
tools/**/*.py
requirements*.txt
.env.example
alembic.ini
```

Unsafe include categories:

```text
.venv/**
__pycache__/**
*.pyc
.pytest_cache/**
docs/_build/**
.pytest_vendor/**
pytest_vendor/**
wheelhouse/**
.tmp/**
tmp/**
pytest-cache-files-*/**
```

Never delete `.venv/`, evidence files, worklogs, source files, schemas, tests, migrations, or requirements files as part of packaging.

## 5. Verification before packaging

Run required tests first. If tests pass, record the exact commands and results in the worklog. After packaging, inspect the zip contents instead of deleting repository files.

Minimum checks for patch packaging:

```text
python -S tools/contract_lint.py --write-inventory
zip content listing proves no generated/cache/vendor artifacts are included
```

## 6. Context-budget discipline

To avoid wasting Codex time:

- Read the specific files named by the work package first.
- Do not dump large docs into the prompt or terminal output.
- Use targeted search such as `grep`, `Select-String`, or opening narrow line ranges.
- Stop and ask for a smaller task if the task spans multiple work packages.

## 7. Recovery if damage occurs

If source files, docs, schemas, tests, migrations, evidence, or worklogs disappear:

1. Stop immediately.
2. Do not attempt to recreate the entire repo from memory.
3. Report the exact last action and current file status.
4. Restore from the latest known-good zip/source control before applying any new patch.
5. Add a recovery worklog once the repo is restored, unless the user explicitly asks only for rule changes and no recovery worklog.


## 8. Single source of truth for agent rules

- `AGENTS.md` and `RULES.md` are the only repo-owned agent instruction files.
- Do not create or reference hidden agent rule folders for persistent instructions.
- Do not create a separate destructive-operation rules document. Keep destructive-operation and packaging safety rules in `AGENTS.md` and `RULES.md`.
