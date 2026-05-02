# Sphinx Build Contract

## Build Command

From `stream_lite/docs`:

```bash
make html
```

Equivalent direct command from repository root:

```bash
sphinx-build -b html docs docs/_build/html
```

## Verification Command

Codex and operators SHALL use the repository verifier so build output is captured as evidence:

```bash
python tools/verify_sphinx_build.py --docs-dir docs --build-dir docs/_build/html --output-file docs/verification/evidence/sphinx_build.txt
```

Strict mode may be used once documentation warnings are intentionally zero:

```bash
python tools/verify_sphinx_build.py --docs-dir docs --build-dir docs/_build/html --output-file docs/verification/evidence/sphinx_build.txt --strict
```

If `sphinx-build` is not installed, the verifier writes a skipped evidence file and exits with status `2`. Install development dependencies with:

```bash
pip install -r requirements-dev.txt
```

## Failure Behavior

The Sphinx build shall fail verification when required documentation pages cannot be parsed, a referenced toctree file is missing, Markdown/RST syntax prevents rendering, or autodoc configuration fails after implementation modules are enabled.

## Requirements

- SL-DECOMP-009
- SL-REQ-004
- V-SL-SPHINX-001

## Current Scope

This skeleton is static-first. Autodoc is configured but not expected to import runtime modules until implementation code exists. The Batch 4 verifier wires Sphinx build evidence without adding runtime implementation code.
