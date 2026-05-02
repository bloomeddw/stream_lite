"""Sphinx build wiring tests.

The actual Sphinx build is executed by `tools/verify_sphinx_build.py` when the
Sphinx development dependency is installed. This test ensures the verifier is
present and documents the expected command surface.
"""

from pathlib import Path


def test_sphinx_verifier_exists_and_is_documented() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    verifier = repo_root / "tools" / "verify_sphinx_build.py"
    sphinx_doc = repo_root / "docs" / "sphinx_build.md"
    assert verifier.exists()
    assert "verify_sphinx_build.py" in sphinx_doc.read_text(encoding="utf-8")
