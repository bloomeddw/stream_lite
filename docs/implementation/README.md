# Implementation Planning Documents

This directory contains implementation-readiness artifacts. They guide future Codex coding tasks but do not contain runtime implementation code.

- `CODEX_TASK_GUIDE.md`: ordered Codex work packages with target files, requirements, schemas, tests, evidence, and rollback notes.
- `CODEX_DESTRUCTIVE_OPERATION_RULES.md`: mandatory safety rules for agents; forbids broad cleanup/deletion and defines patch-only packaging guardrails.
- `naming_review.md`: approved naming map for repositories, route handlers, workers, services, and module layout before coding begins.
- `development_environment.md`: local virtual environment setup and verification commands for contract/Sphinx checks.
- `wp_reference/WP05_FASTAPI_CONTROL_PLANE_MAP.md`: low-reasoning WP-05 implementation map for route modules, schemas, repositories, errors, tests, and completion criteria.
- `wp_reference/WP05_LOW_REASONING_CHECKLIST.md`: fixed implementation order, route response rules, repository use map, tests, and stop conditions for WP-05.
- `WP05_CODEX_PROMPT.md`: ready-to-use Codex prompt for WP-05 after WP-04 completes.
- `WP06_VERIFICATION_PLAN.md`: post-implementation test and evidence checklist for WP-06 watcher work.
- `wp_reference/`: low-reasoning reference maps for WP-06 through WP-14. These are supporting documents only; they are not prompts and do not authorize starting follow-on work before earlier work packages are complete.
