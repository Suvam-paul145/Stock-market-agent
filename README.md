# Stock Market Agent

A local research workbench for Suvam's personal US-stock research. Trades remain manual in INDmoney. It now produces up to five provisional candidates for 1–7 days, one month and six months, plus observed session leaders. These are explainable technical screens, not evaluated investment recommendations.

## Run the four-view research screen

```powershell
uv sync --frozen --cache-dir .uv-cache
.venv\Scripts\python -m stock_agent doctor
.venv\Scripts\python -m stock_agent screen
```

The main CLI now loads `.env` automatically; existing shell variables take precedence. Set `SEC_USER_AGENT`, `APCA_API_KEY_ID` and `APCA_API_SECRET_KEY` locally. Never commit `.env`. Each run saves HTML, Markdown, JSON and its public market inputs under a dated folder such as `reports/2026-10-01_14-30-25_IST_screen/`. Dates use the report's original generation time in India Standard Time. Runs in the same second get a numbered suffix to avoid overwriting. Open `reports/index.html` for the report history, with the newest report always first, or open an individual report's `index.html`. In Windows Explorer, sort folder names descending for newest first. Reports are snapshots; run again to refresh.

The default configuration screens a labelled 30-company starter universe using free IEX data. Copy `screening.example.json` to `screening.local.json` to edit symbols, sectors and risk limits, then pass `--config screening.local.json`; `scripts/run-research.ps1` selects that local file automatically when present. A list can contain fewer than five or be unavailable when gates fail. Exit code 2 means an unavailable board or run failure; exit code 0 is not evidence of investment usefulness.

Each candidate displays its ticker beside the full company name from SEC metadata, for example `AAPL — Apple Inc.`. You can optionally add a `company_names` mapping to the screening configuration for use when SEC metadata is unavailable or filings are skipped. Unresolved names are explicitly marked unavailable.

Read [the multi-horizon implementation and two-year operating plan](docs/MULTI_HORIZON_IMPLEMENTATION.md) for formulas, limitations and remaining work. [PostgreSQL setup](docs/POSTGRES_FOUNDATION.md) is separate: the local screen requires no database and does not publish into the cloud. News, earnings and fundamentals still need review before trade-oriented recommendations.

## Current project direction

The 2026-09-11 research stage is documented separately:

- [Requirements and resolved assumptions](docs/REQUIREMENTS_AND_ASSUMPTIONS.md)
- [Research findings and source register](docs/RESEARCH_DOSSIER.md)
- [Implementation blueprint and acceptance gates](docs/IMPLEMENTATION_BLUEPRINT.md)

The selected target is Supabase PostgreSQL with private Storage, a scheduled Python worker and private Vercel dashboard. Free recurring services remain required. The September 17 addendum supersedes older horizon/universe limits. Cloud deployment is **planned, not implemented**. The commands below describe the original SQLite collector, available separately.

## Run on Windows

Use Python 3.12–3.14 and the locked environment above. Run from this project folder:

```powershell
.venv\Scripts\python -m stock_agent doctor
.venv\Scripts\python -m stock_agent demo
.venv\Scripts\python -m pytest -q --basetemp .pytest_cache/test-temp
```

`demo` uses synthetic prices, makes no network requests and writes to a separate demonstration database. Open the printed report folder's `index.html` or `research.md`. Its prices are not market observations.

## Configure real collection

Copy `config.example.json` to `config.local.json`. Replace its watchlist, set `watchlist_is_example` to `false`, and choose `horizon`: `intraday`, `days_weeks`, or `months_years`. Leave `unconfirmed` until decided. Age limits are configurable research checks, not a claim that a feed is suitable for your trading horizon.

Set these environment variables locally, or place them in `.env` using `.env.example` as a template:

```powershell
$env:SEC_USER_AGENT = 'YourAppName your-real-contact-email'
$env:APCA_API_KEY_ID = 'your-key'
$env:APCA_API_SECRET_KEY = 'your-secret'
.venv\Scripts\python -m stock_agent doctor --config config.local.json
.venv\Scripts\python -m stock_agent collect --config config.local.json
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
