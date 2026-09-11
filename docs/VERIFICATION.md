# Verification record — 2026-09-10

Environment: Windows PowerShell, Python 3.14.0. Core application has no third-party Python dependencies.

| Check | Result | Evidence boundary |
| --- | --- | --- |
| `python -W error::ResourceWarning -m unittest discover -s tests -v` | 14 tests passed | Uses synthetic fixtures/mocked provider calls; no live-data proof. |
| `python -m stock_agent doctor` | Ran successfully; three provider variables absent | Environment presence only; no credential values printed. |
| `python -m stock_agent demo` | Generated Markdown, JSON, HTML and Gemini prompt; zero requests | Synthetic prices only; separate demo SQLite database. |
| `python -m stock_agent collect` | Generated incomplete report with explicit `not_configured` providers; zero requests | Correct missing-configuration behavior; live connectivity remains NOT VERIFIED. |

Example outputs created during verification:

- Synthetic workflow: `reports/53c3e62d-fdf2-43a2-b554-5be70350ee42/`
- Missing-provider collection: `reports/92e816de-e68e-4a48-96f7-5aae97807b42/`

Tests cover timezone requirements, observation-based staleness, nonfinite/negative/boolean prices, future trades, filing identity/column validation, duplicate accessions, invalid configuration, first-run baseline behavior, persistent deduplication, cache expiry, absent credentials, synthetic export, HTML escaping, rate-limit handling, request budgets, host allowlisting and partial-provider failure.

Live provider schemas/entitlements, browser rendering, market-session calendars, stock research quality and predictive usefulness are NOT VERIFIED. No deployment, external message, paid API request or trade was performed.

## Documentation milestone — 2026-09-11

Created `REQUIREMENTS_AND_ASSUMPTIONS.md`, `RESEARCH_DOSSIER.md` and `IMPLEMENTATION_BLUEPRINT.md`. Updated the README and project handoff and marked the earlier execution/provider notes historical. Selected Supabase PostgreSQL/private Storage for the target architecture after comparing managed database alternatives; no database migration occurred.

Validation: seven Markdown documents decoded as UTF-8; local links resolved; code fences balanced; all referenced source IDs/ranges resolved against 38 source-register entries. A separate agent reviewed the design. Its substantive findings were addressed: backup-storage/egress reservations now constrain retained-evidence admission, and generated material factual claims receive a mandatory budgeted passage-support review while human audits remain the ground truth.

These are documentation/static checks only. No application code or configuration was edited, and runtime tests were not repeated for this documentation-only change. The earlier 14-test result remains dated 2026-09-10 and does not validate PostgreSQL, Supabase, the proposed model pipeline or the future dashboard. No accounts, cloud resources, notifications or trading actions were created or performed.
