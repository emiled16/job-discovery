## Job Discovery Platform: Vision, Target Architecture, and Ultra-Granular Task Plan

### Common Vision Target

Build a fully containerized product that runs end-to-end with `docker compose up --build`, continuously ingests jobs, and provides a complete user/admin workflow for discovery and tracking.

Non-negotiable engineering goals:

1. Idempotent ingestion with zero duplicate job records.
2. Clear operational visibility for every pipeline run.
3. Fast user filtering and reliable application tracking.
4. Strict separation between API serving and ingestion execution.
5. Easy extensibility for new adapters and future auth modes.

### Target Architecture

- frontend (Next.js): dashboard, views, summary, admin.
- api (FastAPI): REST endpoints, validation, query logic, admin control plane.
- worker (Celery): ingestion/parsing/upsert execution.
- scheduler (Celery Beat): periodic sync triggering.
- postgres: transactional system of record.
- redis: broker/result backend.

---

## Execution Phases and Milestones

### Phase 1: Platform Bootstrap

- Scope: `A01-A10`
- Objective: establish runnable service skeletons, container definitions, health checks, and configuration discipline.
- Exit criteria:
  - `docker compose config` is valid.
  - frontend, api, worker, and scheduler containers build locally.
  - health and config-validation tests pass.
- Why first: every later phase depends on stable boot, env handling, and repeatable local startup.

### Phase 2: Persistence Foundation

- Scope: `A11-A25`
- Objective: land the database wiring, baseline schema, indexes, and deterministic seed path.
- Exit criteria:
  - baseline migrations apply to an empty database.
  - seed can be rerun without duplicate seed records.
  - local bootstrap produces a usable seeded user and starter companies.
- Why second: API, ingestion, and UI work all need a stable schema and predictable local data.

### Phase 3: Query and Admin API Surface

- Scope: `A26-A43`
- Objective: expose the minimal REST surface for jobs, applications, saved views, summary metrics, and admin controls.
- Exit criteria:
  - core user and admin endpoints pass contract/integration coverage.
  - request IDs and error envelopes are consistent.
  - manual sync can be requested from the API layer.
- Why third: this gives the frontend a contract early and decouples API development from ingestion completeness.

### Phase 4: Ingestion Core and Source Adapters

- Scope: `A44-A58`
- Objective: implement adapter contracts, source parsers, run/event tracking, idempotent upsert, reconciliation, closure, reopen, and scheduled sync.
- Exit criteria:
  - at least Greenhouse and Lever ingest through the shared adapter contract.
  - reruns do not create duplicate jobs.
  - scheduled and manual sync both produce observable pipeline runs and events.
  - closure and reopen behavior is proven by tests.
- Why fourth: this is the platform's highest-risk correctness layer and should be finished before UI polish.

### Phase 5: User Experience Delivery

- Scope: `A59-A75`
- Objective: ship the dashboard, saved views, summary, and admin workflows against the real API.
- Exit criteria:
  - dashboard browse/filter/detail/apply flows work end to end.
  - saved views and summary pages are fully functional.
  - admin users can manage companies, trigger syncs, and inspect runs from the UI.
- Why fifth: once ingestion and APIs are stable, the frontend can integrate without chasing moving backend behavior.

### Phase 6: Hardening, Runtime Proof, and Handoff

- Scope: `A76-A80`
- Objective: finish observability, safety controls, full-stack runtime validation, and operational documentation.
- Exit criteria:
  - logging, timeout, and input-hardening tests pass.
  - compose-backed E2E coverage passes for the product-critical workflows.
  - runbook steps reproduce a working stack from scratch.
- Why last: these tasks validate production readiness and make the platform operable by others.

### Milestone Summary

| Milestone | Completion Signal | Included Tasks |
|---|---|---|
| M1 | Services boot consistently in Compose with validated config. | `A01-A10` |
| M2 | Schema and seed path are stable enough for feature work. | `A11-A25` |
| M3 | API contract is usable by the frontend and admin operations. | `A26-A43` |
| M4 | Ingestion correctness guarantees are implemented and tested. | `A44-A58` |
| M5 | Full user/admin product workflow works in the UI. | `A59-A75` |
| M6 | Runtime proof, hardening, and docs are complete. | `A76-A80` |

### Critical Path

1. `A01-A12`: bootable services and migration capability.
2. `A13-A25`: schema completeness and seed repeatability.
3. `A26-A30`, `A39-A43`: API contract needed for UI and operations.
4. `A44-A58`: ingestion correctness, scheduled sync, and observability.
5. `A59-A75`: end-user and admin UX integration.
6. `A76-A80`: hardening, runtime E2E proof, and handoff docs.

### Parallel Work Guidance

- After Phase 2, backend API work (`A26-A43`) and adapter fixture preparation (`A47`) can proceed in parallel.
- Within Phase 4, source adapters (`A45-A46`) can move in parallel once `A44` is settled.
- Within Phase 5, dashboard (`A60-A65`), saved views (`A66-A68`), summary (`A69-A71`), and admin UI (`A72-A75`) can be split across contributors after `A59` is complete.
- `A76-A78` can begin before all UI polish is finished, but `A79-A80` should wait until the product-critical flows are stable.

---

## Ultra-Granular Tasks (Definition + Expected Result + Testable Success)

| ID | Task | Definition | Expected Result | Success Criteria (Tests) |
|---|---|---|---|---|
| A01 | Create root service directories | Add canonical folders for frontend/backend/infra/tests. | Predictable repo shape. | Repo-structure check validates required directories. |
| A02 | Add backend app package skeleton | Create FastAPI app modules and entrypoint. | API boots with placeholder route. | Startup test returns 200 from health endpoint. |
| A03 | Add worker package skeleton | Create Celery app config and worker entrypoint. | Worker process starts cleanly. | Worker boot test confirms broker connection. |
| A04 | Add scheduler package skeleton | Create Beat entrypoint and schedule config loader. | Beat process starts with schedule registry. | Beat boot test confirms registered periodic task IDs. |
| A05 | Add frontend app skeleton | Create Next.js app with route scaffolding. | Frontend serves base page in container. | UI smoke test returns 200 for `/`. |
| A06 | Add Dockerfiles per service | Define Docker build for frontend/api/worker/scheduler. | Reproducible image builds. | CI/local build test succeeds for all images. |
| A07 | Compose base service graph | Define all services, ports, networks, volumes. | Stack starts with all containers created. | Compose config validation + startup smoke passes. |
| A08 | Compose healthchecks | Add app/db/redis health probes and dependencies. | Startup gating avoids race failures. | Health test asserts all services become healthy. |
| A09 | Environment template | Create `.env.example` with all required variables. | Complete documented config surface. | Static config test checks required keys present. |
| A10 | Runtime config validation | Implement strict env parsing in each service. | Fast fail on misconfiguration. | Unit tests verify invalid env raises descriptive errors. |
| A11 | DB engine/session wiring | Create Postgres connection/session management. | Stable DB connectivity for API/worker. | Integration test creates and closes session successfully. |
| A12 | Migration framework setup | Add Alembic configuration and migration runner. | Versioned schema evolution available. | Migration test applies baseline to empty DB. |
| A13 | Users table migration | Add minimal users schema for local single-user mode. | Persistent user identity available. | DB test validates constraints and default seed key. |
| A14 | Companies table migration | Add company core fields and lifecycle status. | Company registry persisted. | DB test validates allowed lifecycle enum states. |
| A15 | Company sources table migration | Add source metadata for adapter routing. | Per-company ingestion source tracked. | DB test validates FK and source type constraints. |
| A16 | Jobs table migration | Add normalized job fields and identity keys. | Core job records persisted. | DB test validates uniqueness and nullable rules. |
| A17 | Job snapshots table migration | Add raw/derived snapshot history support. | Historical ingestion state retained. | DB test validates job FK and timestamp ordering constraints. |
| A18 | Applications table migration | Add per-user job tracking fields. | User-job tracking persists independently. | DB test enforces unique `(user_id, job_id)`. |
| A19 | Saved views table migration | Add view name + filter JSON + sort config. | Reusable query definitions persisted. | DB test validates JSON and ownership constraints. |
| A20 | Pipeline runs table migration | Add run metadata/status/timestamps. | Run-level observability persisted. | DB test validates status enum + lifecycle transitions. |
| A21 | Pipeline run events migration | Add per-step event/error records. | Fine-grained diagnostics retained. | DB test validates FK and event ordering by timestamp. |
| A22 | Query indexes migration | Add indexes for filters/sorts/search. | Dashboard query performance baseline. | EXPLAIN-based integration checks use expected indexes. |
| A23 | Seed command framework | Add deterministic seed runner command. | One-command local bootstrap. | Seed test verifies idempotent reruns with no duplicate seed records. |
| A24 | Seed local user | Insert default `local_user`. | Single-user mode usable immediately. | Test asserts user exists after seed run. |
| A25 | Seed starter companies | Insert small admin-visible company set. | Admin UI populated on first launch. | Test asserts company count and valid states. |
| A26 | API error envelope middleware | Standardize error shape + request IDs. | Uniform client-consumable errors. | API tests validate envelope and request ID propagation. |
| A27 | Pagination/sorting primitives | Build shared query parameter handlers. | Consistent list endpoint behavior. | Unit tests validate bounds/defaults/rejected inputs. |
| A28 | Jobs filter parser | Implement title/location/company/work-mode/date filters. | API supports dashboard filtering requirements. | Integration tests cover filter combinations. |
| A29 | Jobs list endpoint | Implement `GET /api/v1/jobs`. | Paginated filtered job retrieval. | Integration tests verify sort order and paging edges. |
| A30 | Job detail endpoint | Implement `GET /api/v1/jobs/{id}`. | Full detail payload available. | Test validates 404 and full content for valid IDs. |
| A31 | Application upsert endpoint | Implement `PUT /api/v1/jobs/{id}/application`. | Mark/update applied state per user-job. | Tests validate create/update semantics and validation rules. |
| A32 | Application list endpoint | Implement `GET /api/v1/applications`. | User tracking records queryable. | Tests validate filtering by status/date. |
| A33 | Saved views create endpoint | Implement `POST /api/v1/views`. | New view persisted with validation. | Contract tests validate accepted/rejected payloads. |
| A34 | Saved views read/list endpoints | Implement `GET /api/v1/views` + `GET /api/v1/views/{id}`. | Views retrievable for UI. | Tests validate ownership and not-found behavior. |
| A35 | Saved views update endpoint | Implement `PATCH /api/v1/views/{id}`. | View edits persisted safely. | Tests validate partial updates and invalid mutations. |
| A36 | Saved views delete endpoint | Implement `DELETE /api/v1/views/{id}`. | View lifecycle complete. | Tests validate deletion and idempotent second-delete behavior policy. |
| A37 | Summary metrics endpoint | Implement `GET /api/v1/summary/metrics`. | KPI totals available to UI. | Aggregation tests verify total/applied/rate correctness. |
| A38 | Summary timeseries endpoint | Implement `GET /api/v1/summary/timeseries`. | Trend data available to UI. | Tests verify bucket logic and stable ordering. |
| A39 | Admin companies list/create | Implement `GET/POST /api/v1/admin/companies`. | Admin can list/add companies. | Integration tests validate required fields and defaults. |
| A40 | Admin companies patch | Implement `PATCH /api/v1/admin/companies/{id}`. | Admin can edit URL/state/source metadata. | Tests validate valid/invalid lifecycle transitions. |
| A41 | Admin manual sync trigger | Implement `POST /api/v1/admin/companies/{id}/sync`. | On-demand sync task enqueued. | Integration test asserts Celery task dispatch with company + request metadata. |
| A42 | Admin pipeline runs list | Implement `GET /api/v1/admin/pipeline-runs`. | Operators can monitor runs. | Tests validate filtering by status/date/company. |
| A43 | Admin pipeline run detail | Implement `GET /api/v1/admin/pipeline-runs/{id}`. | Operators can inspect events/errors. | Tests validate joined event payload correctness. |
| A44 | Adapter contract + normalized schema | Define adapter interface, fetch result contract, and normalized job payload schema. | New adapters plug into one stable contract. | Unit tests validate adapter contract conformance and normalization rules. |
| A45 | Greenhouse adapter | Implement fetch + parse + normalize for Greenhouse. | First structured source supported. | Fixture tests validate normalization and resilience. |
| A46 | Lever adapter | Implement fetch + parse + normalize for Lever. | Second structured source supported. | Fixture tests validate normalization and resilience. |
| A47 | Adapter fixture corpus | Add representative success/error fixtures per supported source. | Parser regressions become testable and repeatable. | Fixture suite covers active, missing-field, and malformed-response cases. |
| A48 | Adapter selection logic | Route companies to adapters by source metadata. | Correct parser chosen per company. | Unit tests validate routing matrix and fallback policy. |
| A49 | Run creation workflow | Create pipeline run record at task start. | Every sync has a traceable run ID. | Integration test verifies run record creation for scheduled and manual sync paths. |
| A50 | Per-company event logging | Emit structured events per ingest step. | Fine-grained diagnostics available. | Tests assert event sequence and payload fields. |
| A51 | Parallel company processing | Execute active companies concurrently with bounds. | Faster sync throughput. | Integration test validates concurrency + deterministic completion. |
| A52 | Job identity and idempotent upsert workflow | Merge fetched jobs into canonical records using deterministic source identity keys. | Repeated syncs update existing jobs instead of creating duplicates. | Integration tests prove reruns and overlapping adapter payloads do not create duplicate job rows. |
| A53 | Snapshot persistence workflow | Persist raw payloads and normalized derivations for each observed job state. | Snapshot history explains how a job changed over time. | Integration tests verify one snapshot per observed state transition with raw payload retained. |
| A54 | Ingestion reconciliation workflow | Compare fetched active jobs against previously active jobs for the same company/source. | The system can detect when a previously seen job disappears from source results. | Integration tests validate reconciliation output for unchanged, added, and missing jobs. |
| A55 | Job closure workflow | Mark jobs closed after the configurable missed-cycle threshold. | Stale jobs are retired without deleting historical state. | Integration tests validate closure after 3 missed cycles by default and support config override. |
| A56 | Job reopen workflow | Reopen a previously closed job if the same source identity reappears. | Source recovery does not create a second job record. | Integration tests validate close-then-reopen preserves identity and audit history. |
| A57 | Scheduled sync registration | Register Beat schedule and dispatch the global sync task on configured cadence. | Periodic ingestion works without manual intervention. | Scheduler integration test validates Beat emits the expected task using the configured interval. |
| A58 | End-to-end ingestion correctness suite | Add compose/integration coverage for manual sync, scheduled sync, deduplication, closure, and reopen. | The platform's core ingestion guarantees are proven in runtime-like conditions. | End-to-end ingestion suite passes for no-duplicate, snapshot, closure, reopen, and observability scenarios. |
| A59 | Frontend API client layer | Add typed API client and error handling wrappers. | Consistent UI-backend integration. | Unit tests validate request/response mapping. |
| A60 | Dashboard route scaffolding | Create `/dashboard` page shell and layout. | Navigable core route available. | UI smoke test validates route render. |
| A61 | Dashboard job list component | Implement card/table rendering and switcher. | Jobs readable in preferred format. | Component tests validate rendering parity for card vs. table. |
| A62 | Dashboard filters UI | Implement title/location/company/mode/date controls. | Users can refine job results. | E2E tests validate controls modify API query params correctly. |
| A63 | Dashboard sorting + pagination UI | Implement sort selector and page controls/infinite load. | Large result sets navigable. | E2E tests validate stable ordering across pages. |
| A64 | Job detail drawer/page | Implement full job view with metadata and actions. | Users can inspect details without losing context. | E2E test validates open/close behavior and detail data integrity. |
| A65 | Applied toggle integration | Wire UI action to application upsert endpoint. | One-click apply tracking works. | E2E test validates toggle persists after refresh. |
| A66 | Saved views page shell | Create `/views` route and base list/create layout. | Saved views UX entrypoint available. | UI smoke test validates route render. |
| A67 | Saved views create/edit form | Implement name/filter/sort editor with validation. | Users can define reusable views. | E2E tests validate create/update flows and validation errors. |
| A68 | Saved views delete/apply actions | Implement delete and apply-to-dashboard actions. | Full saved-view lifecycle complete. | E2E tests validate delete and dashboard filter hydration. |
| A69 | Summary page shell | Create `/summary` route with KPI and chart regions. | Analytics entrypoint available. | UI smoke test validates route render. |
| A70 | Summary KPI components | Render totals, applied, and application rate. | Users see progress metrics quickly. | Component tests validate numeric formatting and values. |
| A71 | Summary trend chart integration | Render applications-over-time dataset. | Trend visibility complete. | UI integration tests validate ordered series and empty states. |
| A72 | Admin page shell | Create `/admin` route with tabs/sections. | Operator entrypoint available. | UI smoke test validates route render. |
| A73 | Admin companies table/form | Implement list/add/edit/enable-disable workflows. | Company management operable from UI. | E2E tests validate full company management flow. |
| A74 | Admin manual sync action | Add per-company sync trigger controls and feedback. | Operator can trigger immediate ingestion. | E2E tests validate trigger creates a visible new run with eventual status updates. |
| A75 | Admin run monitor view | Implement run list + run detail event/error panel. | Pipeline observability accessible in UI. | E2E tests validate run/event visibility and error display. |
| A76 | Structured logging baseline | Add JSON logging and correlation IDs across services. | Cross-service troubleshooting improved. | Log-format tests validate required fields on emitted logs. |
| A77 | Timeouts and fail-fast guards | Add HTTP/parser timeout configs and guards. | Hung adapters constrained. | Failure tests validate timeout path and graceful run failure state. |
| A78 | Security and input hardening | Add payload validation, safe URL handling, and output escaping baseline. | Reduced risk in admin/user inputs and fetch logic. | Security-focused tests validate rejected unsafe inputs. |
| A79 | Full-stack compose E2E harness | Run end-to-end scenarios against live compose stack. | Product-level behavior guaranteed in runtime target. | E2E suite passes: browse/apply/view/summary/admin/manual-sync flows. |
| A80 | Engineering runbook and ops docs | Document setup, run, migration, seed, tests, troubleshooting, adapter extension, and sync operations. | Team can execute and extend system consistently. | Onboarding validation confirms documented steps produce a working stack. |

---

### Platform Definition of Done

- All services are healthy in Docker Compose.
- Scheduled and manual sync both function and are observable.
- Dashboard, job detail, saved views, summary, and admin are fully usable.
- Unit + integration + E2E suites pass on the containerized stack.
- Idempotency, deduplication, snapshot history, and job closure/reopen logic are proven by tests.

### Assumptions and Defaults

- v1 runs with a single seeded local user (`local_user`) and no login UI.
- v1 admin capabilities run in the same local-user context; separate authorization modes are a future extension.
- Job closure threshold default: 3 missed cycles (configurable).
- Sync cadence default: every 4 hours (configurable).
- Future backlog: bookmarks/hide jobs, advanced funnel analytics, OAuth multi-user auth.
