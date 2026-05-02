#!/usr/bin/env python3
"""Run Sphinx HTML build verification for Stream Lite docs.

This tool intentionally lives outside runtime packages. It is used by Codex and
operators to produce repeatable documentation build evidence.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--docs-dir", default="docs", help="Sphinx source directory")
    parser.add_argument("--build-dir", default="docs/_build/html", help="HTML output directory")
    parser.add_argument("--output-file", default="docs/verification/evidence/sphinx_build.txt", help="Evidence output file")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors with -W")
    args = parser.parse_args(argv)

    sphinx_build = shutil.which("sphinx-build")
    output_path = Path(args.output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if sphinx_build is None:
        message = (
            "SKIPPED: sphinx-build was not found. Install development dependencies with "
            "`pip install -r requirements-dev.txt`, then rerun this command.\n"
        )
        output_path.write_text(message, encoding="utf-8")
        print(message, end="")
        return 2

    docs_dir = Path(args.docs_dir)
    build_dir = Path(args.build_dir)
    cmd = [sphinx_build, "-b", "html"]
    if args.strict:
        cmd.append("-W")
    cmd += [str(docs_dir), str(build_dir)]

    completed = subprocess.run(cmd, text=True, capture_output=True, check=False)
    evidence = [
        f"Command: {' '.join(cmd)}",
        f"Exit code: {completed.returncode}",
        "",
        "STDOUT:",
        completed.stdout,
        "",
        "STDERR:",
        completed.stderr,
    ]
    output_path.write_text("\n".join(evidence), encoding="utf-8")
    print(f"Sphinx build exit code: {completed.returncode}")
    print(f"Evidence: {output_path}")
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
