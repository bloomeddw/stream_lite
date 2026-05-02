# Development Environment Setup

This repo uses development-only tooling for contract validation, schema fixture validation, Sphinx documentation builds, and future pytest checks. Keep that tooling isolated from the operating system Python installation.

## Recommendation

Use a virtual environment under the project root while working locally. The recommended folder name is `.venv`.

Do not commit `.venv/`, generated Sphinx output, pytest caches, or generated evidence files unless the evidence artifact is intentionally requested for a patch.

## Windows PowerShell setup

From the `stream_lite` repository root:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

If PowerShell blocks activation, run this once for the current shell session and then retry activation:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Confirm the active Python comes from `.venv`:

```powershell
python -c "import sys; print(sys.executable)"
```

The printed path should include `stream_lite\.venv`.

## macOS/Linux setup

From the `stream_lite` repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

## Verification commands

After activating the virtual environment, run:

```bash
python tools/contract_lint.py --write-inventory
python tools/validate_schema_examples.py --write-evidence
python tools/verify_sphinx_build.py --docs-dir docs --build-dir docs/_build/html --output-file docs/verification/evidence/sphinx_build.txt
pytest tests/contract
```

Expected pre-runtime result:

- `contract_lint` passes with zero unresolved requirement references and zero duplicate active requirement rows.
- JSON Schema fixture validation reports zero failures.
- Sphinx build verification creates or updates `docs/verification/evidence/sphinx_build.txt`.
- `pytest tests/contract` passes.

## Why a virtual environment is preferred

A virtual environment prevents project tooling from being installed into the user-wide Python site packages. This keeps local verification reproducible and prevents conflicts with other Python projects or Python versions.

## Pytest import path behavior

The contract test suite imports verification utilities from the top-level `tools/` directory. Because Stream Lite is not yet packaged as an installable Python distribution, `tests/conftest.py` explicitly adds the repository root to `sys.path` during pytest collection.

Run pytest from the repository root:

```powershell
pytest tests/contract
```

If a direct shell environment still reports `ModuleNotFoundError: No module named 'tools'`, confirm that `tests/conftest.py` exists and that the current directory is the repository root containing `tools/` and `tests/`.
