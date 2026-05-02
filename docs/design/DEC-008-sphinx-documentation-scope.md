# DEC-008: Sphinx Documentation Scope

## Status

Accepted for v0.1.

## Decision

Sphinx shall build static project documentation first. Python autodoc shall be activated after route handlers, validators, event producers/consumers, processors, and retry handlers exist.

## Rationale

The current project is requirements-first. Requiring autodoc before implementation would create false documentation failures for modules that intentionally do not exist yet. Static documentation still proves requirements, architecture, operations, API contracts, schemas, verification, and worklogs can be rendered.

## Requirement Impact

- `REQ-014` adds static Sphinx build requirements and deferred autodoc behavior.

## Verification Impact

v0.1 documentation verification shall run a static Sphinx build. Missing future autodoc targets shall be listed as deferred rather than failing the v0.1 build.
