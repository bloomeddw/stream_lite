# WORKLOG-20260501-codex-safety-guardrails

## Summary

Added repository-level Codex/agent safety guardrails after a completed Codex session reported that WP-07 verification passed and then a later cleanup step removed repository files from the working copy. The guardrails make cleanup non-destructive by default, require explicit changed-file patch packaging, and define incident recovery steps.

## Files changed

- `AGENTS.md`
- `.codex/RULES.md`
- `docs/implementation/CODEX_DESTRUCTIVE_OPERATION_RULES.md`
- `docs/implementation/CODEX_TASK_GUIDE.md`
- `docs/implementation/README.md`
- `docs/index.rst`
- `docs/worklogs/INDEX.md`
- `docs/worklogs/WORKLOG-20260501-codex-safety-guardrails.md`

## Requirements affected

- `SL-REQ-003`: worklog requirement for changes.
- `SL-DECOMP-010`: implementation planning requires contracts and explicit execution boundaries.
- `SL-VER-031`: milestone readiness requires recorded verification and known gaps.

## Decisions applied

- Root `AGENTS.md` is the first agent instruction file for the repository.
- `.codex/RULES.md` is the Codex-specific rule file.
- Generated artifacts are excluded from patch packaging instead of being removed from the working tree by broad cleanup commands.
- `.venv/` must not be deleted from a user's working copy by Codex cleanup; it should only be excluded from patch archives.

## Tests and verification

- `python -S tools/contract_lint.py --write-inventory` passed in the review sandbox.
- Sphinx-specific verification should be rerun in the project virtual environment after applying the patch because this sandbox does not have the full project dev environment.

## Assumptions

- The reported deletion happened after verification and during cleanup, not during WP-07 implementation logic.
- The latest known-good source should be restored from a zip or source control before reapplying any WP-07 implementation patch.
- The guardrails are docs/rules only; they do not replace source control, backups, or human review of destructive commands.

## Gaps

- No Codex CLI transcript is available because the session output was cleared.
- No forensic command history is included in this patch.
- These guardrails cannot prevent a tool from ignoring repo instructions; they reduce risk for agents that read repo-level instructions.

## Rollback notes

To roll back this guardrail patch, remove the added agent/rules documents and revert the index/README/task-guide/worklog-index entries. This rollback is not recommended because it would remove destructive-operation protection.

## Next step

Restore the latest known-good repository state, apply this guardrail patch, verify contract lint and Sphinx docs, then reissue a shorter WP-07 prompt that references `AGENTS.md` and `.codex/RULES.md` before implementation.
