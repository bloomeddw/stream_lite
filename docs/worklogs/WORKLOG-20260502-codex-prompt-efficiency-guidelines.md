# WORKLOG-20260502-codex-prompt-efficiency-guidelines

## Summary

Updated repository agent guidance to reduce Codex reasoning-token usage while preserving requirements-first safety. The changes add allocated low-reasoning work prompt structure, tiered file-reading rules, task-splitting guidance, compact response mode, and verification-order guidance.

## Files changed

- `AGENTS.md`
- `RULES.md`
- `docs/implementation/CODEX_TASK_GUIDE.md`
- `docs/worklogs/WORKLOG-20260502-codex-prompt-efficiency-guidelines.md`
- `docs/worklogs/INDEX.md`

## Requirements affected

Instruction-only guidance update. No product requirement, API route, event schema, environment variable, persistence model, metric, retry rule, or runtime behavior was changed.

## Decisions applied

- Default future Codex implementation handoffs to allocated low-reasoning execution tickets.
- Split broad tasks into narrow sequential prompts when a task spans multiple major implementation surfaces.
- Use tiered required-read versus reference-only-if-needed file lists.
- Avoid architecture comparison and redesign unless explicitly requested.
- Prefer compact routine implementation reports and reserve full traceability reports for release gates or failed verification.

## Tests / verification

- Markdown files were updated directly.
- No runtime code was changed.
- `python -S tools/contract_lint.py --write-inventory` passed. Inventory output was not retained because no contract-bearing runtime or requirement references changed.

## Assumptions

- Project settings prompts are external ChatGPT/Codex configuration and must not be included in repo patch zips.
- The revised project settings prompt will be supplied in chat as copy/paste text and, if useful, as a separate non-repo artifact.

## Gaps

- No product behavior is validated by this patch because it only updates agent/workflow documentation.

## Rollback notes

Revert the four documentation files listed above and remove this worklog entry from the worklog index.

## Next step

Use the new allocated-work structure for the next Codex prompt and compare reasoning-token ratio against the previous WP-08 run.
