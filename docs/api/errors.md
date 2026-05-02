# API Error Code Catalog

| Error code | HTTP status | Trigger | Operator message rule | Related requirements |
|---|---:|---|---|---|
| `API_TIMEOUT` | 504 | Dependency operation exceeds 10 seconds. | Name operation and resource role; include correlation ID. | SL-API-007 |
| `BROKER_UNAVAILABLE` | 503 | Redis Streams unavailable. | State broker is unavailable and workers are paused. | SL-RUN-013 |
| `COMMAND_NOT_FOUND` | 404 | Unknown command ID. | State command ID was not found. | SL-LIFE-015 |
| `CONFIG_INVALID_ENUM` | 500/503 | Unsupported runtime enum at startup. | Name variable and allowed values. | SL-RUN-009 |
| `CONFIG_UNSUPPORTED_DEFERRED_PROFILE` | 500/503 | Redpanda or Flink selected in v0.1. | State profile is deferred and name active profile. | SL-RUN-010 |
| `DB_UNAVAILABLE` | 503 | PostgreSQL unavailable. | State metadata database is unavailable. | SL-RUN-013 |
| `FILTER_INVALID` | 422 | Invalid list filter value. | Name invalid filter and allowed values. | SL-API-009 |
| `JOB_NOT_FOUND` | 404 | Unknown job ID. | State job ID was not found. | SL-API-004 |
| `JOB_NOT_RETRYABLE` | 409 | Retry requested for non-eligible job. | State current state and non-retryable reason. | SL-API-005, SL-RET-012 |
| `NO_MATCHING_DESTINATION` | 409 on start, 200 warning on preview | Source has tags but no destination match. | Identify source display path and route tags. | SL-FWM-028 |
| `PAGINATION_INVALID` | 422 | Invalid `limit` or `offset`. | Include allowed range. | SL-API-008 |
| `PATH_INVALID` | 422 | Malformed or unsupported path. | State path cannot be normalized. | SL-SEC-001 |
| `PATH_NOT_ALLOWLISTED` | 422 | Path outside mounted allowlist. | Show sanitized display path only. | SL-SEC-002 |
| `PATH_ROOT_UNAVAILABLE` | 422/503 | Configured root missing or inaccessible. | State root role is unavailable. | SL-RUN-009 |
| `PRESENTATION_CONFIG_INVALID` | 500 | Dashboard YAML fails schema validation. | State presentation config is invalid and fallback status. | SL-UI-004 |
| `RETRY_LIMIT_EXHAUSTED` | 409 | No attempts remain. | State retry attempts exhausted. | SL-RET-009 |
| `ROUTE_NOT_ENABLED` | 409 | Watcher start requested before valid route preview. | State route preview must be green. | SL-API-019 |
| `TAG_INVALID` | 422 | Route tag fails regex. | Name invalid tag field, not raw untrusted path. | SL-FWM-024 |
| `WATCHER_NOT_FOUND` | 404 | Unknown watcher ID. | State watcher ID was not found. | SL-API-002 |
| `WATCHER_STATE_CONFLICT` | 409 | Invalid watcher lifecycle transition. | Include current state and allowed action. | SL-API-003 |
