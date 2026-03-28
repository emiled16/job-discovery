# Job Discovery Platform Runbook

## 1. Purpose

This runbook is the operational guide for standing up, verifying, and extending the local Job Discovery platform. It covers:

- container startup
- migrations and seed behavior
- frontend/backend test commands
- compose-backed runtime verification
- ingestion troubleshooting
- adapter extension workflow

The target outcome is a working stack from a clean checkout with seeded user/company/job data and a repeatable smoke path for dashboard, views, summary, and admin flows.

## 2. Prerequisites

- Docker with Compose
- Node.js 24+ for local frontend work
- Python 3.13 for local backend work

## 3. Environment

Copy `.env.example` to `.env` when you need overrides. The defaults already support local Compose.

Important variables:

- `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`
- `API_INTERNAL_BASE_URL=http://api:8000`
- `DATABASE_URL=postgresql://job_discovery:job_discovery@postgres:5432/job_discovery`
- `WORKER_DATABASE_URL=postgresql://job_discovery:job_discovery@postgres:5432/job_discovery`
- `WORKER_HTTP_TIMEOUT_SECONDS=15`
- `SCHEDULER_SYNC_INTERVAL_SECONDS=14400`

## 4. Startup

Bring the stack up:

```bash
docker compose up --build -d
```

Check service status:

```bash
docker compose ps
docker compose logs api --tail=100
docker compose logs worker --tail=100
docker compose logs scheduler --tail=100
docker compose logs frontend --tail=100
```

Notes:

- the API container runs migrations and deterministic seed data before starting
- the seed creates `local_user`, starter companies, and two starter jobs for repeatable UI/runtime proof
- frontend proxy requests use `API_INTERNAL_BASE_URL`, so the browser talks only to the frontend origin

## 5. Local URLs

- frontend: `http://localhost:3000`
- api: `http://localhost:8000`
- api health: `http://localhost:8000/health`

## 6. Test Commands

Backend:

```bash
cd backend
pytest -q
```

Frontend:

```bash
cd frontend
npm install
npm test
npm run build
```

## 7. Compose E2E Smoke

Run the live-stack verifier after `docker compose up --build -d`:

```bash
python infra/compose_e2e.py
```

The harness checks:

- frontend routes render
- backend health responds
- seeded jobs are visible
- application upsert works
- saved view create/delete works
- summary metrics reflect the apply flow
- admin companies list works
- manual sync creates a pipeline run with observable events

## 8. Migrations and Seed

Run migrations locally:

```bash
cd backend
python -m job_discovery_backend.db.migrate upgrade head
```

Run seed locally:

```bash
cd backend
python -m job_discovery_backend.db.seed
```

Seed behavior:

- idempotent on rerun
- updates seeded user/company/job records in place
- does not create duplicate rows

## 9. Troubleshooting

If the frontend loads but data actions fail:

- confirm `api` is healthy: `curl http://localhost:8000/health`
- confirm the frontend proxy can reach the backend: `docker compose logs frontend --tail=100`
- verify `API_INTERNAL_BASE_URL` is `http://api:8000` inside Compose

If worker syncs never complete:

- confirm Redis and Postgres are healthy: `docker compose ps`
- inspect worker logs: `docker compose logs worker --tail=200`
- check timeout configuration: `WORKER_HTTP_TIMEOUT_SECONDS`
- inspect run detail in `/admin` or hit `GET /api/v1/admin/pipeline-runs/{id}`

If a company URL is rejected:

- admin-facing URL validation only allows public `http(s)` hosts
- localhost, private IPs, credentialed URLs, and fragment-bearing URLs are rejected intentionally

If manual sync creates a failed run:

- inspect the run events in `/admin`
- verify the company source type is supported (`greenhouse` or `lever`)
- verify the company source key/base URL resolves to a valid public target

## 10. Adapter Extension

To add a new ingestion adapter:

1. Implement a new adapter under `backend/src/job_discovery_backend/ingestion/adapters/`.
2. Conform to the shared adapter contract:
   - `build_request_url(source)`
   - `parse_payload(payload, source)`
   - `fetch(source)`
3. Register the adapter in `backend/src/job_discovery_backend/ingestion/registry.py`.
4. Add fixtures under `backend/tests/fixtures/adapters/`.
5. Extend unit coverage in `backend/tests/unit/test_ingestion_adapters.py`.
6. Verify idempotent ingestion behavior with `pytest -q`.

## 11. Sync Operations

Scheduled sync:

- dispatched by Celery Beat on `SCHEDULER_SYNC_INTERVAL_SECONDS`
- lands in `pipeline.sync_all_companies`

Manual sync:

- triggered from `/admin`
- posts to `POST /api/v1/admin/companies/{id}/sync`
- creates a `pipeline_runs` row immediately
- worker updates run status and event history as execution progresses

## 12. Shutdown and Cleanup

Stop services:

```bash
docker compose down
```

Remove persisted state:

```bash
docker compose down -v
```
