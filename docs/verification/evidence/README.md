# Verification Evidence Artifacts

This directory stores generated evidence from contract-first verification commands.
Generated evidence files should be updated by Codex implementation patches when the relevant command is run.

Current WP-00 evidence outputs:

- `schema_fixture_validation.md` from `python tools/validate_schema_examples.py --write-evidence`
- `sphinx_build.txt` from `python tools/verify_sphinx_build.py --docs-dir docs --build-dir docs/_build/html --output-file docs/verification/evidence/sphinx_build.txt`
- `docs/reqs/REQUIREMENT_REFERENCE_INVENTORY.md` from `python -S tools/contract_lint.py --write-inventory`
