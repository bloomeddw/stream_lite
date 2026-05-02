# WP-13 Reference Map: Sphinx Documentation Build

## Purpose

Reduce Codex reasoning for WP-13 by fixing the documentation build scope, autodoc targets, warning policy, and evidence expectations.

## Scope boundary

WP-13 makes Sphinx documentation verification complete for the implemented runtime modules. It does not add application behavior.

## Primary requirement IDs

- `SL-DECOMP-009`
- `SL-REQ-004`
- `V-SL-SPHINX-001`
- Sphinx-related rows in `REQ-000` and verification docs

## Read before coding

- `docs/conf.py`
- `docs/index.rst`
- `docs/sphinx_build.md`
- `tools/verify_sphinx_build.py`
- `docs/implementation/CODEX_TASK_GUIDE.md`
- public modules under `app/` and `streamlit_app/`

## Target files

| File/folder | Responsibility |
|---|---|
| `docs/api_reference/` | Autodoc pages for public runtime modules. |
| `docs/index.rst` | Include API reference and all relevant index pages. |
| `docs/conf.py` | Sphinx extensions and autodoc settings. |
| `tools/verify_sphinx_build.py` | Keep evidence-generating wrapper stable. |
| `tests/contract/test_sphinx_build_command.py` | Ensure verifier wiring remains tested. |

## Fixed implementation map

### Static docs

All index pages should be included in the Sphinx toctree. Historical worklogs may be included through `docs/worklogs/INDEX.md` rather than individually in `docs/index.rst`.

### Autodoc scope

Add autodoc pages for public modules implemented through WP-12:

- `app.api.*`
- `app.config.*`
- `app.db.*`
- `app.repositories.*`
- `app.events.*`
- `app.watcher.*`
- `app.validation.*`
- `app.processing.*`
- `app.delivery.*`
- `app.retry.*`
- `app.observability.*`
- `streamlit_app.*` if implemented

Do not document private helpers unless needed to explain a public surface.

### Warning policy

Preferred goal: Sphinx build exits 0 with no unexpected warnings.

If a warning is intentionally accepted, document it in:

- `docs/sphinx_build.md`
- WP-13 worklog
- evidence output

## Test checklist

- `python tools/verify_sphinx_build.py ...` exits 0 or records accepted skipped status only if Sphinx is unavailable.
- No `toc.not_included` warnings for active docs.
- Public modules import cleanly for autodoc.
- Generated `_build` is not committed.

## Out of scope

- Runtime code behavior changes.
- New requirements unrelated to docs.

## Verification commands

Run:

```powershell
python tools/verify_sphinx_build.py --docs-dir docs --build-dir docs/_build/html --output-file docs/verification/evidence/sphinx_build.txt
pytest tests/contract
```

Remove `docs/_build/` before handoff.
