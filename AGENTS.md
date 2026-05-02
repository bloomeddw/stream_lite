# Stream Lite Agent Instructions

These instructions apply to the entire repository. They are mandatory for Codex, ChatGPT, shell agents, and any automated implementation helper working inside this repo.

## Prime directive

Stream Lite is requirements-first, patch-first, and restore-safe. Do not perform broad cleanup, broad deletion, or destructive repository reset operations. A coding task is not complete until the repository remains intact, tests are reported, generated artifacts are excluded from the deliverable, and a worklog is written when the task changes product/code/docs behavior.

## Critical safety rules for all future work

These rules are mandatory for every Stream Lite work package, patch, verification run, and packaging step:

1. Do not delete files from the working tree as a cleanup step.
2. Do not run `Remove-Item -Recurse`, `rm -rf`, `git clean`, `git reset --hard`, `rd /s`, `rmdir /s`, `del /s`, `find -delete`, or any cleanup loop based on `$root`, `$PWD`, `Resolve-Path .`, or repository-wide recursion.
3. Cleanup means excluding generated/cache/vendor files from the final zip, not deleting them from the repo.
4. Do not delete `.venv`, `.pytest_vendor`, `pytest_vendor`, `docs/_build`, `.pytest_cache`, `__pycache__`, `tmp`, `.tmp`, `wheelhouse`, or `*.pyc` from the user workspace. Leave them alone.
5. If generated/cache files exist, ignore them when building the patch zip.
6. If deletion appears required, stop and report the exact file list and reason. Do not execute deletion.
7. Do not use `git reset`, `git checkout`, or `git clean` to discard local work.
8. Before editing product code, inspect `AGENTS.md` and `RULES.md`; these are the repo-owned agent instruction sources. Do not create additional hidden agent rule folders.

## Required reading before code changes

Before modifying files, read:

1. `rtc_source.md` when present beside or inside the repo.
2. `docs/implementation/CODEX_TASK_GUIDE.md`.
3. `RULES.md` 
4. The current work-package reference under `docs/implementation/wp_reference/`.
5. The owning requirement files for the work package.

If any of these files are missing after a destructive operation, stop and report recovery steps instead of continuing.

## Destructive-command ban for all future work

Never run any command that can recursively delete or reset the repository, including but not limited to:

- `rm -rf .`, `rm -rf *`, `rm -rf stream_lite`, or any repo-root recursive delete.
- `git clean -fd`, `git clean -fdx`, `git reset --hard`, or `git checkout .` unless the user explicitly asks for recovery and names the exact target.
- PowerShell `Remove-Item -Recurse`, `Remove-Item -Force -Recurse`, `rd /s`, `rmdir /s`, `del /s`, or `Get-ChildItem -Recurse | Remove-Item` from the repo root.
- Any PowerShell loop that builds a `$targets`, `$paths`, `$items`, or similar list and pipes or iterates those paths into `Remove-Item`.
- Any command that combines `$root`, `$PWD`, `Resolve-Path .`, repo-root path joins, or recursive discovery with deletion.
- `find . -delete`, `find . -exec rm`, or equivalent broad delete pipelines.
- Docker or system prune commands such as `docker system prune`, `docker volume prune`, or commands that remove local data volumes.

Generated artifacts must be excluded from zip patches, not removed from the working tree with broad deletes.

## No working-tree cleanup after verification for any work package

After tests pass, do not run deletion cleanup in the user's working tree. This includes targeted-looking cleanup loops such as removing `docs/_build`, `.pytest_cache`, vendor folders, `__pycache__`, `*.pyc`, or `pytest-cache-files-*` with `Remove-Item`, `rm`, `del`, `find -delete`, or scripts.

Instead:

1. Build patch zips from an explicit include list of changed files.
2. Exclude generated/cache/vendor artifacts in the zip command or staging manifest.
3. Inspect the zip content listing.
4. Leave the working tree intact.

This rule exists because a prior run used a targeted PowerShell cleanup command with `Remove-Item -Recurse`; it included `.venv` and removed required files/evidence. That pattern is forbidden for every future work package even when the command appears to list only generated paths.

## Safe cleanup policy

For normal implementation work, cleanup means **package exclusion**, not working-tree deletion.

The following paths may be excluded from a patch zip:

- `docs/_build/`
- `.pytest_cache/`
- `__pycache__/`
- `*.pyc`
- `.tmp/`
- `tmp/`
- `.pytest_vendor/`
- `pytest_vendor/`
- `wheelhouse/`
- `pytest-cache-files-*`

Do not delete these paths from the user's working copy unless the user gives an explicit one-off recovery instruction naming the exact path. Do not delete `.venv/` from the user's working copy under any packaging or cleanup instruction. Do not delete `app/`, `docs/`, `schemas/`, `tests/`, `tools/`, `.env.example`, requirements files, migrations, evidence, or worklogs.

For packaging, create a patch zip from an explicit include list of changed source/docs/test files. Do not clean the whole repository to make a zip.

## Patch and worklog requirements

Every non-trivial product/code/docs change must include a worklog under `docs/worklogs/` with:

- summary
- files changed
- requirements affected
- decisions applied
- tests or verification commands run
- assumptions
- gaps
- rollback notes
- next step

Prompts do not go in zip patches. Show prompts only in chat or external handoff text.

Instruction-only safety changes may omit a worklog when the user explicitly says not to create one.

## Stop conditions

Stop immediately and report instead of continuing if:

- A command would delete anything from the user's working tree for packaging or cleanup.
- A command contains `Remove-Item`, `rm`, `del`, `rd`, `rmdir`, `find -delete`, or `git clean` and the target is inside the repo.
- A command would delete more than a single exact file intentionally removed as part of the patch.
- `git status --short` shows unexpected deleted source, docs, schema, test, migration, evidence, or worklog files.
- The current task would need a new environment variable, API route, schema, event, migration, metric, state transition, or Streamlit control that is not requirements-backed.
- The work-package prompt conflicts with `AGENTS.md` or `RULES.md`
- Tests pass only before cleanup but files are missing after cleanup.

## Incident recovery rule

If files are deleted unexpectedly:

1. Stop all implementation work.
2. Do not run more cleanup commands.
3. Capture `pwd`, `git status --short`, `git status --ignored --short`, and the last destructive command if known.
4. Do not attempt to recreate the entire repo from memory.
5. Ask the user to restore from the latest known-good zip or source control before reapplying changes.
