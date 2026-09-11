# Stock Market Agent

A local research workbench for Suvam's personal US-stock watchlist. Trades remain manual in INDmoney. Version 0.1 collects evidence and exports it for review; it does not yet produce evaluated investment recommendations.

## Current project direction

The 2026-09-11 research stage is documented separately:

- [Requirements and resolved assumptions](docs/REQUIREMENTS_AND_ASSUMPTIONS.md)
- [Research findings and source register](docs/RESEARCH_DOSSIER.md)
- [Implementation blueprint and acceptance gates](docs/IMPLEMENTATION_BLUEPRINT.md)

The selected target is Supabase PostgreSQL with private Storage, a scheduled Python research worker, and a private Vercel dashboard. Days-to-weeks research, strictly free recurring services and automatic public-evidence analysis are confirmed. These cloud capabilities are **planned, not implemented**. The commands below still run the original local SQLite prototype. Its example configuration is historical/demo configuration, not the confirmed production watchlist.

## Run on Windows

Python 3.11 or newer is required. This version uses only the Python standard library; no package install is needed. Run from this project folder:

```powershell
python -m stock_agent doctor
python -m stock_agent demo
python -m unittest discover -s tests -v
```

`demo` uses synthetic prices, makes no network requests and writes to a separate demonstration database. Open the printed report folder's `index.html` or `research.md`. Its prices are not market observations.

## Configure real collection

Copy `config.example.json` to `config.local.json`. Replace its watchlist, set `watchlist_is_example` to `false`, and choose `horizon`: `intraday`, `days_weeks`, or `months_years`. Leave `unconfirmed` until decided. Age limits are configurable research checks, not a claim that a feed is suitable for your trading horizon.

Set these environment variables locally; `.env.example` documents them but is not automatically loaded:

```powershell
$env:SEC_USER_AGENT = 'YourAppName your-real-contact-email'
$env:APCA_API_KEY_ID = 'your-key'
$env:APCA_API_SECRET_KEY = 'your-secret'
python -m stock_agent doctor --config config.local.json
python -m stock_agent collect --config config.local.json
```

Enter real values only on your machine. Avoid saving commands containing secrets in shared shell history. SEC requires an identifying user agent with contact details; it does not need an API key. Alpaca requires a separately eligible account and credentials. Account eligibility and access must be verified with an actual response. The app calls only market-data endpoints and never broker/order endpoints.

Collection works partially when a provider is missing. Exit code `2` means incomplete collection; reports still show the failure. Exit code `0` means the command finished without missing/error provider states, not that the research is complete or data is fresh. Inspect quality and coverage fields. `doctor` prints presence booleans, never credential values.

## What you receive

Each run creates a unique folder under `reports/`:

- `research.md`: readable evidence inventory, source dates, limitations and next research questions.
- `research.json`: structured evidence and provider status.
- `gemini_prompt.txt`: copyable instructions for reviewing that specific package.
- `index.html`: a portable, script-free local reading view.

Upload only the selected research files and prompt to Gemini or another assistant. Do not upload credentials, `.env` files, databases, or the whole project. Current packages contain public evidence and no portfolio holdings; inspect exports before adding private information later. Manual AI review is not automatically imported, executed, or validated by this version.

SQLite stores successful raw JSON snapshots, original fetch times, filing baselines, locally recorded events and report records. It is local application storage, not tamper-proof archival storage. First SEC collection establishes a baseline; later unseen accessions generate deduplicated **newly observed filing** events. The report shows at most 20 recent filing records. Older archive pagination and filing body analysis are pending.

## Operating limits

This is a one-shot command. It starts and stops with each run; no scheduler, phone/email notification or always-on monitoring exists yet. Run again to refresh. Cached prices keep their original observation time. A stale trade is flagged without guessing whether the market is open. Calendar-aware checks are a future milestone.

The HTTP client uses HTTPS provider allowlists, no redirects, 15-second request timeouts, a 30-request budget per run, a 10 MB response limit and a 0.6-second minimum interval within the process. It stops on HTTP 429 and retries transient server/network failures at most twice. Run only one collection process at a time; cross-process rate coordination is not implemented. Cached malformed JSON structures remain invalid until cache expiry; no stale fallback is silently substituted.

News, earnings, quantitative analytics, portfolio risk limits, strategy backtests, calibrated probabilities and forecasting are pending. A functioning collector does not demonstrate investment usefulness.

See [the execution plan](docs/EXECUTION_PLAN.md), [provider research](docs/PROVIDER_RESEARCH.md), and [project context](PROJECT_CONTEXT.md).
