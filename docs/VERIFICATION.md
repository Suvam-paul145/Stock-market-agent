# Verification record

## Readable report folders — 2026-10-01

Both exporters now use original report generation time in IST, for example `2026-10-01_14-30-25_IST_screen`. Same-second collisions receive a numbered suffix; existing files are never overwritten. The generated `reports/index.html` history page orders reports by their original timestamp, newest first. Windows folder views can use Name descending.

Renamed all 12 existing UUID folders using embedded timestamps and checked SHA-256 hashes for every file before and after each move. The reversible old/new mapping is recorded in `reports/folder-renames.json`; historical paths mentioned below refer to the original names. Contents, market observation times and source hashes remain unchanged. No provider requests were made.

Validation: **41 tests and 6 subtests passed** across report paths, the legacy workbench and screening. Ruff passed. Checks include the IST date boundary, collision preservation and timestamp ordering independent of directory creation order.

## Multi-horizon screening and PostgreSQL — 2026-09-17 to 2026-09-19

These results supersede the historical missing-provider and implementation-status statements below. They establish software/provider behavior, not profitable trading performance.

| Check | Result | Evidence boundary |
| --- | --- | --- |
| Full suite with disposable PostgreSQL 17.11, September 17 | **78 tests and 6 subtests passed** | Includes real DB migrations, transactions, role restrictions, lease/budget concurrency, imports and screening fixtures; existing application data preserved. |
| `ruff check stock_agent migrations tests` | Passed | Static code checks, not financial validation. |
| Screening tests after weekend wording correction, September 19 | **24 tests passed**; targeted Ruff passed | Corrected closed-session volume explanation; no scoring formula changed. |
| Live on-demand collection, September 17 | Four boards, five candidates each, 100% configured-universe coverage | IEX-only feed across 30 configured stocks plus SPY; all selected SEC metadata calls succeeded. |
| Live weekend collection, September 19 | Four boards, five candidates each, 100% configured-universe coverage; 18 HTTP requests | The leader view correctly identifies September 18 as the latest completed session, not live Saturday data. Fifteen selected companies had successful SEC metadata enrichment. |
| Recompute from saved live input | Evidence hash matched; new report directory preserved the original cutoff | Clarified completed-session wording without refetching or changing source observations. |
| Credential export check | No configured SEC identity, Alpaca key or secret found in final exported files | Only boolean result printed; credentials were not displayed or transmitted to a model. |
| Browser/layout check | Generated four-view HTML opened and visually inspected in local browser | Navigation, readable cards, evidence disclosures and visible limitations checked; no cloud deployment. |
| Markdown references | Ten Markdown files checked; no missing local links | Documentation links only. |

Latest checked input run: `reports/screen-e2ecc98fcda149baba1a0d3f667e85ab/`, observed at **2026-09-19 17:50:56 UTC**. Final report recomputed from those same inputs: `reports/screen-251591726214467ca2dcb923b43f4c96/`. Refresh before relying on later market conditions; reports are saved snapshots.

Screening regressions cover hand-calculated returns, benchmark alignment, ties, sector caps, missing/future/duplicate/nonfinite/inconsistent bars, incomplete pagination, partial-day exclusion, short histories, stale and inconsistent snapshots, weekend/holiday/early-close/DST handling, dates through September 2028, HTML escaping and environment precedence. Declining markets need not produce five candidates. PostgreSQL tests caught and fixed an existing-instance Pydantic validation bypass. Independent review caught and fixed after-hours leader handling and mixing daily prices with unrelated minute timestamps.

News, earnings calendars, financial statement analysis, claim-validated AI synthesis, prospective return evaluation, cloud publication, scheduled monitoring and backup/restore operations remain pending. The local screening workflow does not yet persist into PostgreSQL. The two-year document describes maintenance and evaluation work; no two-year uptime or profitability claim has been verified. No trades, paid subscriptions or cloud resources were created.

## Original prototype — 2026-09-10

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
