"""Sphinx configuration for Stream Lite documentation.

This configuration is intentionally static-first for the requirements/design phase.
Autodoc paths may be enabled after implementation modules exist.
"""

project = "Stream Lite"
author = "Stream Lite Project"
release = "0.1.0"

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.todo",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
html_theme = "alabaster"
todo_include_todos = True

# Future implementation phase: insert stream_lite package path here for autodoc.
