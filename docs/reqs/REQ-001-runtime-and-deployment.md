# REQ-001: Runtime and Deployment Requirements

## Capability Intent

The system shall run as a Dockerized local platform composed of independently addressable services for API control, dashboard interaction, metadata storage, event streaming, file watching, validation, processing, delivery, and observability. The runtime shall be reproducible enough for a product demo and structured enough to evolve into a larger data platform.

## Scope

In scope:
- Docker Compose runtime.
- Service health checks.
- Environment-based configuration.
- Mounted source and destination folders.
- PostgreSQL, Redis Streams, FastAPI, Streamlit, and Spark services for the v0.1 MVP profile.
- Redpanda and Flink are future-compatible profiles documented as deferred implementation scope, not v0.1 startup targets.

Out of scope:
- Kubernetes.
- Cloud deployment.
- Multi-node high availability.

## Functional Requirements

| ID | Requirement | Priority | Verification |
|---|---|---:|---|
| SL-RUN-001 | The system shall provide a Docker Compose file that starts all required services with one command. | Must | V-SL-RUN-001 |
| SL-RUN-002 | The runtime shall expose FastAPI on host port from `STREAM_LITE_API_PORT`, default `8000`, allowed integer range `1024` through `65535`. | Must | V-SL-RUN-002 |
| SL-RUN-003 | The runtime shall expose Streamlit on host port from `STREAM_LITE_DASHBOARD_PORT`, default `8501`, allowed integer range `1024` through `65535`. | Must | V-SL-RUN-003 |
| SL-RUN-004 | PostgreSQL shall persist data to a named Docker volume so job metadata survives container restart. | Must | V-SL-RUN-004 |
| SL-RUN-005 | The selected event broker shall use a named Docker volume for broker data; the v0.1 MVP profile shall be `redis_streams` and shall enable Redis append-only persistence. | Must | V-SL-RUN-005 |
| SL-RUN-006 | Source and destination folders shall be mounted into containers through explicit volume mappings. | Must | V-SL-RUN-006 |
| SL-RUN-007 | Runtime configuration shall be supplied through environment variables and shall not require code changes for broker choice, watch path root, destination root, or processing engine. | Must | V-SL-RUN-007 |
| SL-RUN-008 | Each service shall expose a health status that can be inspected by Docker Compose or the API. | Must | V-SL-RUN-008 |
| SL-RUN-009 | The runtime shall fail fast when required environment variables are missing or invalid. | Must | V-SL-RUN-009 |
| SL-RUN-010 | The processing engine service shall be selected by `STREAM_LITE_PROCESSING_ENGINE`; the v0.1 MVP allowed value shall be `spark`, the default local demo value shall be `spark`, and any `flink` value shall fail startup with `CONFIG_UNSUPPORTED_DEFERRED_PROFILE` until Flink requirements are moved from future-compatible scope to active scope. | Must | V-SL-RUN-010 |

## Nonfunctional Requirements and Metrics

| ID | Metric Requirement | Target |
|---|---|---:|
| SL-RUN-NFR-001 | Full local stack startup time on a developer machine after images are built | <= 90 seconds |
| SL-RUN-NFR-002 | API health endpoint readiness after container start | <= 20 seconds |
| SL-RUN-NFR-003 | Dashboard readiness after container start | <= 30 seconds |
| SL-RUN-NFR-004 | Container restart metadata preservation for PostgreSQL-backed jobs | 100% for committed records |
| SL-RUN-NFR-005 | Configuration values documented in `.env.example` | 100% of required values |

## Required Interfaces

- `GET /health`
- `GET /health/dependencies`
- Docker Compose service health checks.
- `.env.example` with documented defaults.

## Configuration Failure Contract

| Condition | Required behavior |
|---|---|
| Required env var missing | The affected service exits non-zero before accepting traffic, logs `CONFIG_MISSING`, and `/health/dependencies` reports the dependency as unavailable until corrected. |
| Env var has unsupported enum value | The affected service exits non-zero, logs `CONFIG_INVALID_ENUM`, and includes the variable name and allowed values without logging secret values. |
| Required mounted root absent | Watcher creation and folder validation return `422` with `PATH_ROOT_UNAVAILABLE`; existing watchers enter `blocked_source` or `blocked_destination` according to folder role. |
| Broker profile unavailable | API readiness remains false, worker services do not process new jobs, and a `BROKER_UNAVAILABLE` health reason is reported. |
| Deferred broker or engine profile selected | The affected service exits non-zero, logs `CONFIG_UNSUPPORTED_DEFERRED_PROFILE`, and reports the unsupported profile name without starting workers. |

## L2 Contract Decomposition Requirements

These rows decompose runtime/deployment into Docker Compose, configuration, volume, readiness, and unsupported-profile contracts.

| ID | Level | Parent requirement IDs | Contract surface | Requirement | Priority | Verification |
|---|---|---|---|---|---:|---|
| SL-RUN-019 | L2 | SL-RUN-001, SL-RUN-011 | Docker Compose service contract | Docker Compose shall declare API, dashboard, watcher, worker, PostgreSQL, Redis Streams, and processing services with stable service names, documented host ports, health checks where supported, named volumes, and startup dependencies. | Must | V-SL-RUN-019 |
| SL-RUN-020 | L2 | SL-RUN-002, SL-RUN-003, SL-RUN-007, SL-RUN-009 | Runtime configuration loader contract | Service startup shall validate documented environment variables, apply documented defaults, reject unsupported enum/range values with `CONFIG_INVALID_ENUM`, reject missing required values with `CONFIG_MISSING`, reject deferred profiles with `CONFIG_UNSUPPORTED_DEFERRED_PROFILE`, and log sanitized active profile values. | Must | V-SL-RUN-020 |
| SL-RUN-021 | L2 | SL-RUN-004, SL-RUN-005, SL-RUN-006 | Volume ownership contract | Runtime docs shall identify the named volume or bind mount for PostgreSQL data, Redis data, source roots, destination roots, quarantine roots, output roots, and evidence artifacts, including read/write access per service. | Must | V-SL-RUN-021 |
| SL-RUN-022 | L2 | SL-RUN-008, SL-RUN-012 | Readiness response contract | Readiness responses shall include service name, dependency status, startup timestamp, and unhealthy reason code when readiness cannot be achieved. | Must | V-SL-RUN-022 |
| SL-RUN-023 | L2 | SL-RUN-010 | Unsupported profile contract | Requested `flink` or `redpanda` profiles in v0.1 shall fail before side effects with `CONFIG_UNSUPPORTED_DEFERRED_PROFILE` and an operator-safe message naming the active supported value. | Must | V-SL-RUN-023 |

## Acceptance Criteria

The requirement is accepted when a clean checkout can start the system, confirm API and dashboard availability, create a watcher using mounted folders, restart the stack, and still see previously persisted watcher and job metadata.

## Migrated Docker Runtime Requirements

The following requirements were migrated from the duplicate draft `REQ-012-dockerized-runtime.md` and normalized under the active runtime requirement namespace.

| ID | Requirement | Priority | Verification |
|---|---|---:|---|
| SL-RUN-011 | Docker Compose shall define services for API, dashboard, watcher, worker, PostgreSQL, and the selected Redis Streams or Redpanda broker. | Must | V-SL-RUN-011 |
| SL-RUN-012 | The default and only active v0.1 runtime profile shall use Redis Streams; Redpanda shall remain documented as a future-compatible profile and shall not be accepted by v0.1 startup configuration. | Must | V-SL-RUN-012 |
| SL-RUN-013 | The API shall wait for database and event-broker readiness before reporting ready for traffic. | Must | V-SL-RUN-013 |
| SL-RUN-014 | The repository shall provide `.env.example` values sufficient to start the default demo stack after copying to `.env`. | Must | V-SL-RUN-014 |
| SL-RUN-015 | The repository shall document a local reset procedure for generated data, broker state, and PostgreSQL volumes. | Should | V-SL-RUN-015 |
| SL-RUN-016 | Docker named volumes shall use stable names prefixed with `stream_lite_`. | Must | V-SL-RUN-016 |
| SL-RUN-017 | Container service names shall remain stable for the default stack: `api`, `dashboard`, `watcher`, `worker`, `postgres`, and either `redis` or `redpanda`. | Must | V-SL-RUN-017 |
| SL-RUN-018 | Logs for all long-running services shall be available through `docker compose logs`. | Must | V-SL-RUN-018 |

## Migrated Runtime Verification Requirements

| ID | Verification Method | Evidence Artifact |
|---|---|---|
| V-SL-RUN-011 | Docker Compose configuration validation and service inventory check. | Compose service list and config validation output. |
| V-SL-RUN-012 | Default profile startup test. | Startup log showing Redis Streams mode. |
| V-SL-RUN-013 | Dependency readiness smoke test. | API readiness response and startup log excerpt. |
| V-SL-RUN-014 | Fresh setup test from `.env.example`. | Setup transcript and resulting health checks. |
| V-SL-RUN-015 | Local reset procedure test. | Reset command transcript and post-reset health summary. |
| V-SL-RUN-016 | Compose volume naming check. | Volume list showing `stream_lite_` prefix. |
| V-SL-RUN-017 | Compose service naming check. | Compose service list. |
| V-SL-RUN-018 | Service log accessibility check. | `docker compose logs` evidence for each service. |

## Applied Decision Records

| Decision | Requirement impact |
|---|---|
| DEC-003 broker profile | v0.1 uses Redis Streams only; Redpanda is deferred. |
| DEC-004 processing engine | v0.1 uses Spark only; Flink is deferred. |
