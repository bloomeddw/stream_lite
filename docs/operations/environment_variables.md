# Environment Variable Catalog

Every variable in this catalog shall appear in `.env.example`. Secrets shall never be logged.

| Name | Purpose | Required | Default | Demo value | Allowed values/format | Sensitive | Owner | Missing behavior | Invalid behavior | Requirements |
|---|---|---:|---|---|---|---:|---|---|---|---|
| `STREAM_LITE_API_PORT` | Host API port. | yes | `8000` | `8000` | integer `1024`-`65535` | no | runtime | use default | `CONFIG_INVALID_ENUM` | SL-RUN-002 |
| `STREAM_LITE_DASHBOARD_PORT` | Host Streamlit port. | yes | `8501` | `8501` | integer `1024`-`65535` | no | runtime | use default | `CONFIG_INVALID_ENUM` | SL-RUN-003 |
| `STREAM_LITE_BROKER_PROFILE` | Event broker profile. | yes | `redis_streams` | `redis_streams` | `redis_streams` only in v0.1 | no | runtime | use default | `CONFIG_UNSUPPORTED_DEFERRED_PROFILE` | SL-RUN-012 |
| `STREAM_LITE_PROCESSING_ENGINE` | Processing engine profile. | yes | `spark` | `spark` | `spark` only in v0.1 | no | runtime | use default | `CONFIG_UNSUPPORTED_DEFERRED_PROFILE` | SL-RUN-010 |
| `STREAM_LITE_WATCH_ROOT` | Container root for source folders. | yes | `/data/sources` | `/data/sources` | absolute container path under mounted volume | no | watcher | service not ready | `PATH_ROOT_UNAVAILABLE` | SL-RUN-006 |
| `STREAM_LITE_OUTPUT_ROOT` | Container root for delivered outputs. | yes | `/data/outputs` | `/data/outputs` | absolute container path under mounted volume | no | delivery | service not ready | `PATH_ROOT_UNAVAILABLE` | SL-RUN-006 |
| `STREAM_LITE_QUARANTINE_ROOT` | Container root for quarantine copies. | yes | `/data/quarantine` | `/data/quarantine` | absolute container path under mounted volume | no | validator | service not ready | `PATH_ROOT_UNAVAILABLE` | SL-VAL-016 |
| `STREAM_LITE_DATABASE_URL` | PostgreSQL connection string. | yes | none | `postgresql://stream_lite:stream_lite@postgres:5432/stream_lite` | SQLAlchemy PostgreSQL URL | yes | API/workers | service exits | `DB_UNAVAILABLE` | SL-RUN-004 |
| `STREAM_LITE_REDIS_URL` | Redis connection string. | yes | none | `redis://redis:6379/0` | Redis URL | no | event dispatcher/workers | service exits | `BROKER_UNAVAILABLE` | SL-EVT-001 |
| `STREAM_LITE_DEBUG` | Enables extra local debug details after redaction. | no | `false` | `false` | `true` or `false` | no | all | use default | `CONFIG_INVALID_ENUM` | SL-SEC-009 |
| `STREAM_LITE_FILE_STABILITY_SECONDS` | Time a file must remain unchanged before registration. | yes | `2` | `2` | integer `1`-`3600` | no | watcher | use default | `CONFIG_INVALID_ENUM` | SL-FDI-005 |
| `STREAM_LITE_MAX_FILE_SIZE_MB` | Max accepted file size. | yes | `100` | `100` | integer `1`-`10240` | no | validator | use default | `CONFIG_INVALID_ENUM` | SL-VAL-004 |
| `STREAM_LITE_RETRY_MAX_ATTEMPTS` | Default retry count. | yes | `3` | `3` | integer `0`-`10` | no | retry scheduler | use default | `CONFIG_INVALID_ENUM` | SL-RET-004 |
| `STREAM_LITE_RETRY_INITIAL_BACKOFF_SECONDS` | Initial retry delay. | yes | `1` | `1` | integer `1`-`3600` | no | retry scheduler | use default | `CONFIG_INVALID_ENUM` | SL-RET-004 |
| `STREAM_LITE_RETRY_BACKOFF_MULTIPLIER` | Retry multiplier. | yes | `2` | `2` | number `1`-`10` | no | retry scheduler | use default | `CONFIG_INVALID_ENUM` | SL-RET-004 |
| `STREAM_LITE_RETRY_MAX_BACKOFF_SECONDS` | Maximum retry backoff. | yes | `30` | `30` | integer `1`-`86400` | no | retry scheduler | use default | `CONFIG_INVALID_ENUM` | SL-RET-004 |
| `STREAM_LITE_RETRY_JITTER_ENABLED` | Enables jitter for async retries. | yes | `true` | `true` | `true` or `false` | no | retry scheduler | use default | `CONFIG_INVALID_ENUM` | SL-RET-004 |
| `STREAM_LITE_DASHBOARD_PRESENTATION_FILE` | YAML file for theme/layout defaults. | yes | `/app/config/dashboard_presentation.yaml` | `/app/config/dashboard_presentation.yaml` | absolute container path | no | dashboard/API | use embedded fallback read-only | `PRESENTATION_CONFIG_INVALID` | SL-UI-004 |
| `STREAM_LITE_LOG_LEVEL` | Service log threshold. | no | `INFO` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` | no | all | use default | `CONFIG_INVALID_ENUM` | SL-OBS-001 |
| `STREAM_LITE_RECONCILIATION_INTERVAL_SECONDS` | Worker reconciliation interval. | yes | `10` | `10` | integer `1`-`60` | no | workers | use default | `CONFIG_INVALID_ENUM` | SL-LIFE-011 |
