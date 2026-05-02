# Evidence Index

Evidence artifacts shall be written under `stream_lite/docs/verification/evidence/` during test execution.

| Artifact | Producer | Format | Required contents |
|---|---|---|---|
| `api_contract_review.md` | docs review | Markdown | endpoint coverage, missing schemas, status. |
| `api_schema_validation.json` | schema lint | JSON | schema file list, validation result, errors. |
| `event_schema_validation.json` | schema lint | JSON | event fixture validation result. |
| `env_var_lint.json` | static lint | JSON | variables in requirements, docs, `.env.example`, mismatches. |
| `metrics_catalog_review.md` | docs review | Markdown | metric coverage by component and requirement. |
| `failure_policy_review.md` | docs review | Markdown | failure classes and missing behavior. |
| `streamlit_control_review.md` | docs review/manual | Markdown | control-to-API mapping result. |
| `verification_matrix_lint.json` | static lint | JSON | requirements without verification entries. |
| `sphinx_build.txt` | docs build | text | command, exit code, warnings, errors. |
| `e2e_happy_path/summary.md` | E2E test | Markdown | steps, job IDs, outputs, metrics, screenshots if available. |
| `e2e_quarantine/summary.md` | E2E test | Markdown | invalid files, quarantine records, source preservation proof. |
| `e2e_retry/summary.md` | E2E test | Markdown | injected failure, retry schedule, final state. |

## Documentation tree

```{toctree}
:maxdepth: 1

evidence/README
evidence/schema_fixture_validation
```
