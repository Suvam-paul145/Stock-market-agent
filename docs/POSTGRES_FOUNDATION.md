# PostgreSQL foundation — increment B

Verified locally on 2026-09-17. This increment provides durable evidence storage,
publication checks, role separation, worker leases and shared budgets. It does not
establish forecasting performance or connect the screening collector to PostgreSQL.
See [implementation blueprint](IMPLEMENTATION_BLUEPRINT.md) for subsequent integration.

## Implemented behavior

- Alembic revision `0001_foundation` creates the private `research` schema. Its
  explicit downgrade removes its own objects and preserves unrelated tables.
- Evidence is append-only for the application writer. Provider identity plus content
  hash deduplicates retries, revisions remain separate, and the first observation
  timestamp is preserved. A batch and its source watermark commit together.
- Publication accepts attributed source excerpts. Missing, cross-company, synthetic,
  post-cutoff or nonmatching citations fail the whole transaction. Review IDs are
  idempotent; retrying an older review cannot move the current pointer backwards.
- A database-clock publisher lease fences stale workers. Budget reservations lock
  their shared row and are idempotent by request ID, including concurrent requests.
- Dedicated readers can select the published-review view. Writers cannot modify
  source permissions, rewrite evidence, delete records or create schema objects.
  Source policy approval remains an administrator operation.
- Legacy SQLite inventory is read-only. An explicit import places original records
  into synthetic or quarantined archives and never promotes them to live evidence.
- Pydantic models revalidate existing instances, including nested excerpts. This
  closes a bypass through unvalidated `model_copy(update=...)` values.

## Local commands

Run PowerShell from the repository root with Docker Desktop running. `uv sync --locked`
installs the locked Python environment; network access is required for an uncached install.

```powershell
uv sync --locked
.\scripts\postgres-local.ps1 -Action Start
$env:STOCK_AGENT_DB_PROFILE = 'local'
$env:STOCK_AGENT_MIGRATION_URL = 'postgresql://stock_agent_dev:local-development-only@127.0.0.1:55432/stock_agent_test'
$env:STOCK_AGENT_DATABASE_URL = $env:STOCK_AGENT_MIGRATION_URL
.\.venv\Scripts\python -m stock_agent.db migrate
.\.venv\Scripts\python -m stock_agent.db doctor
.\.venv\Scripts\python -m stock_agent.db demo
```

The public password above belongs only to the loopback development container.
Using its administrator as the runtime user is acceptable only for this local
smoke check. The demo writes a synthetic fixture and deliberately publishes nothing.
Repeated demo runs reuse the same evidence. The database CLI reads shell environment
variables directly. Its commands perform no provider or model requests.

`STOCK_AGENT_MIGRATION_URL` is for schema administration, source policy setup and
legacy import. `STOCK_AGENT_DATABASE_URL` is the ordinary connection: use a writer
credential for the future worker and a reader credential for exports/dashboard reads.
`STOCK_AGENT_DB_PROFILE=production` requires PostgreSQL with `sslmode=verify-full`;
configure a provider-appropriate trust certificate if needed. Hosted TLS and pooler
compatibility have not been validated by the local tests.

After an administrator creates separate, unelevated `stock_agent_writer` and
`stock_agent_reader` roles, apply their grants with:

```powershell
.\.venv\Scripts\python -m stock_agent.db grant-access
```

This command grants privileges to existing roles; it does not create passwords.
Store hosted connection strings in the deployment's secret manager. The browser
must never receive a writer, migration or raw PostgreSQL credential.

For a closed legacy SQLite file, inspect before explicitly importing:

```powershell
.\.venv\Scripts\python -m stock_agent.db import-legacy --path data/research.sqlite3
.\.venv\Scripts\python -m stock_agent.db import-legacy --path data/research.sqlite3 --apply
.\.venv\Scripts\python -m stock_agent.db export --path reports/published-reviews.json
```

Replace the example paths with the actual input and a new output filename. Export
refuses to overwrite an existing file. No user's existing SQLite file was imported
during verification. Stop only the project container, preserving its data, with:

```powershell
.\scripts\postgres-local.ps1 -Action Stop
```

## Verification and reproduction

The verified suite contains 18 contract tests, 22 PostgreSQL integration cases and
14 original workbench tests: **54 passed, plus 6 subtests**. Ruff also passed for
`stock_agent/db`, `migrations`, and both foundation test files.

Integration tests used PostgreSQL 17.11 in the project's pinned Docker image. The
test database was freshly created solely for this verification, separately from
`stock_agent_test`. No hosted database, API secret or user legacy data was used.

To reproduce, create a fresh database such as `foundation_local_test` on the local
container, owned by the test administrator. Do not run these tests on an application
database. Then set the explicit opt-in URL:

```powershell
$env:STOCK_AGENT_TEST_DATABASE_URL = 'postgresql://stock_agent_dev:local-development-only@127.0.0.1:55432/foundation_local_test'
.\.venv\Scripts\python -m pytest tests/test_db_contracts.py tests/test_postgres.py tests/test_workbench.py -q --basetemp=.pytest_cache/foundation-tests
.\.venv\Scripts\ruff check stock_agent/db migrations tests/test_db_contracts.py tests/test_postgres.py
```

The test URL must point to loopback and a database ending in `_test`. The fixture
creates and removes only its owned `research` schema carrying the explicit
`stock_agent_disposable_integration_tests` marker. It refuses to remove an unmarked
schema. The `--basetemp` path is disposable pytest scratch space inside this project;
pytest replaces it on subsequent runs. Without the test URL, database cases skip
while URL guards and non-database tests can run.

Checks cover migration repeatability and downgrade preservation; deduplication;
batch and publication rollback; citation validity; stale/replaced leases; concurrent
lease acquisition and budget reservations through independent connection pools;
actual reader/writer SQL denial; and idempotent, atomic legacy quarantine imports.

## Remaining work and operating limits

- The schema is a foundation. Live collection, horizon screens, retention jobs and
  operational history must be wired to it before it becomes the main runtime store.
- Raw writer credentials remain trusted application credentials. Publication gates
  live in repository code; a compromised writer can bypass that code with direct SQL.
  Do not expose database execution tools or credentials to a model or a browser.
- Quote containment proves that an excerpt exists. It does not prove a generated
  interpretation, investment conclusion, licensing permission or forecast accuracy.
  Source approval is a recorded administrator decision, not an automated legal check.
- Hosted role creation, Supabase private storage, TLS verification, capacity limits,
  encrypted backups and a full restoration drill remain deployment acceptance work.
- Two-year operation needs monitored failures, provider-entitlement checks, bounded
  retention, tested schema upgrades and dependency/security maintenance. These tests
  are a baseline, not evidence of uninterrupted two-year operation.
