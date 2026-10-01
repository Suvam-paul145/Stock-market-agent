# Multi-horizon implementation and two-year operating plan

Updated 2026-09-17. This addendum supersedes the older days-to-weeks-only and five-stock boundaries. User request: five ranked candidates for 1–7 days, within one month, and the next six months, plus stocks dominating the latest US session. Trades remain manual in INDmoney.

## Implemented workflow

`python -m stock_agent screen` loads local credentials, requests adjusted daily history and current snapshots, computes separate research lists, enriches selected companies with SEC filing metadata, and saves HTML/Markdown/JSON plus public inputs. This is an explicit local screening workflow, not the production PostgreSQL publisher. The PostgreSQL foundation is independently implemented and tested; see [its setup guide](POSTGRES_FOUNDATION.md). No cloud resources or recurring bills were created.

Reports identify the universe, risk profile, strategy/calendar versions, feed, timestamps, data coverage, exclusions, score components and evidence hash. Runs get new directories rather than overwriting prior results. Saved JSON inputs support recomputation. Files are not tamper-proof: the hash is a reproducibility aid, not an independent signature. Reports expire for refresh after one hour and do not update themselves.

The main CLI now loads local `.env`, accepts only documented provider/database names, never interpolates variables or executes file contents, and preserves existing shell values. Secrets stay outside exports. Database subcommands retain their documented shell-environment setup.

## Assumptions and limits

Defaults pending answers: a curated 30-company US-stock universe, balanced risk, and leadership defined by price/activity. These are implementation assumptions, not confirmed investment preferences. Copy `screening.example.json` to ignored `screening.local.json` to edit symbols, sector labels and risk rules. The universe is not an index-membership list, a complete list of INDmoney instruments, or recommended holdings. Recheck symbol availability, sectors, mergers and delistings monthly. More than 50 stocks requires new quota/coverage measurements.

Each list returns **up to five** candidates. Never fill a slot with a failing stock. Require at least 80% valid universe data, complete benchmark history, no missing required sessions for eligible companies, finite/consistent OHLCV, and a sector cap of two. Data coverage and investment eligibility are distinct: a valid negative return counts toward coverage but can fail the momentum gate.

Trade recommendations remain explicitly withheld pending evidence and forward evaluation. These are provisional technical research shortlists. Price rankings cannot establish valuation, a company thesis or earnings risk. Six-month recommendations especially need dated financials and counterevidence. Scores compare eligible peers; they are not expected returns or confidence probabilities. The four lists can overlap.

## Reproducible rules

User-facing horizons use calendar days/months; feature lookbacks use completed exchange sessions. These are unvalidated design choices, not claims that historical momentum predicts a future horizon.

| View | Required observations | Weighted percentile score |
| --- | --- | --- |
| 1–7 calendar days | 21 consecutive completed sessions | 35% five-session return; 30% twenty-session return minus SPY; 20% lower volatility; 15% smaller drawdown |
| Within one calendar month | 64 consecutive completed sessions | 35% twenty-session excess return; 30% sixty-three-session excess return; 15% distance above 50-session mean; 20% lower volatility |
| Next six calendar months | 253 consecutive completed sessions | 30% 126-session excess return; 25% 252-session excess return; 20% distance above 200-session mean; 15% lower volatility; 10% smaller drawdown |
| Session leaders | Fresh snapshot and 20 prior full sessions; completed daily data outside regular hours | 50% positive session price change; 30% observed volume / prior average; 20% position within daily range |

Midrank percentiles give ties equal values. Sort weighted scores descending, use symbol as deterministic tie-breaker, then apply the sector cap. Return = close / earlier close − 1. Excess return subtracts SPY's return over identical dates. Volatility = sample standard deviation of the last twenty daily returns × sqrt(252). Drawdown is the worst peak-to-trough close decline in that view's required observations. Moving-average distance = latest close / N-session mean − 1. The IEX dollar-volume proxy is mean(close × volume) over twenty sessions, not consolidated turnover.

Defaults: adjusted price at least $5; average observed IEX dollar-volume proxy at least $1 million; positive trailing 5/20/126-session return for the respective horizon. Annualized volatility caps: conservative 35%, balanced 60%, aggressive 100%. These thresholds are unvalidated heuristics, not optimized parameters or personal risk-tolerance measurements. Session leaders are observations and can include volatile stocks excluded from horizon screens.

Intraday volume fraction is **partial volume / prior full-session average**, not same-time relative volume or an unusual-volume statistical test. Intraday prices use their actual minute-bar timestamp; inconsistent daily/minute ranges are rejected. Outside regular hours, use completed daily bars and label prior-day/weekend results “latest completed session,” never live today. A twenty-minute post-close settling interval can temporarily leave leaders unavailable. XNYS calendars handle scheduled holidays, early closes and daylight saving; unscheduled closures still require maintenance. Provider daily aggregates may reflect extended trading and revisions; they are not guaranteed regular-session-only consolidated closes.

## Sources verified on 2026-09-17

- [Alpaca data plans/authentication](https://docs.alpaca.markets/us/docs/about-market-data-api): personal Basic accounts have free IEX coverage; no upgrade or paid fallback.
- [Historical bars](https://docs.alpaca.markets/us/reference/stockbars): batched symbols, explicit `feed=iex`, `adjustment=all`, chronological pages and full pagination. Results sort by symbol first, so one truncated page can hide later stocks. Repeated tokens or more than ten pages reject incomplete history.
- [Snapshots](https://docs.alpaca.markets/us/reference/stocksnapshots-1): daily, previous daily and minute bars have distinct meanings; timestamps/prices cannot be treated as interchangeable.
- [SEC access](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data): identifying contact User-Agent, bounded requests and cached ticker mapping. This increment reads recent filing metadata; filing bodies are not analyzed.
- [Exchange calendars](https://github.com/gerrymanoim/exchange_calendars): maintained calendar dependency with locked version and schedule provenance.

Requests are allowlisted HTTPS GETs. No order endpoint is reachable through this client. Thirty-request run budget, bounded retries, no immediate 429 retry, response-size limit and 150-second collection deadline constrain work; report writing follows. Missing optional SEC metadata cannot become a verified thesis. Free-service terms and retention/processing rights must be checked again before cloud publication.

## Next implementation gates

1. **Evidence:** Connect permitted news, earnings calendars, SEC company facts/selected filing bodies, issuer announcements and macro context. Record event time, fetch time, revisions and provider gaps. Demonstrate free entitlements; do not assume this key grants every news product.
2. **Fundamentals:** Assemble valuation context, cash flow, debt, margins, revenue trends and scheduled catalysts for shortlisted stocks. Six-month research needs dated financials and counterevidence; short-term research needs event proximity and liquidity. Missing required evidence withholds validated recommendations.
3. **Bounded AI:** Implement extraction, thesis, counterargument and claim-support review using the previously agreed free-only model setup. Numeric features remain deterministic; external content cannot issue instructions. Keep the prior 100-document/200-claim evaluation gates.
4. **PostgreSQL publication:** Extend the schema explicitly for ranking runs and evidence; do not force them into the existing source-excerpt contract. Use transactional publication/leases and separate writer/reader roles. Preserve source rights and capacity budgets.
5. **Private cloud:** Connect worker, authenticated dashboard, schedule and encrypted backups after integration, stale-state and restore tests. On-demand refresh plus the planned hourly cadence; hosting alone does not create a scheduler.
6. **Prospective evaluation:** Save rankings before outcomes, compare against SPY and simple momentum/equal-weight baselines separately for each horizon. No price targets, win probabilities or automatic buy/sell orders before evidence justifies them.

## Two-year operation: September 2026–September 2028

This is an operating target, not a promise of uninterrupted free services, profitability or permanent accuracy.

| Cadence | Required operation |
| --- | --- |
| Every run | Freshness, calendar, coverage and budget checks; original timestamps; visible provider failures; strategy/universe identifiers; withhold affected output on failure. |
| Daily after cloud setup | Check jobs, data growth, API/model quotas, publication and encrypted backups. Dashboard computes stale status independently of worker success. |
| Weekly | Review latency, errors, source changes, credential failures and forward-outcome availability. |
| Monthly | Revalidate free terms/entitlements, universe/sector membership, ticker changes and dependencies; test patches and measure drift against frozen baselines. |
| Quarterly | Restore into disposable PostgreSQL; rehearse outage, quota exhaustion and key rotation; review calendar coverage and statistical evidence. |
| Before ranking/model changes | Version, regress, evaluate on held-out data, record reasons and preserve original results. Never retroactively rewrite recommendations. |

Proposed prospective convention: freeze the signal at report creation and use the next tradable session's observed open as entry, with explicit spread/slippage/FX assumptions. Evaluate seven-calendar-day, one-calendar-month and six-calendar-month targets on the first session on/after each date. Track one-day results separately rather than selecting a profitable exit retrospectively. The outcome evaluator and cost model remain pending; saved reports alone do not implement them.

Account for delistings, symbol changes, dividends and splits. Preserve point-in-time universe records to avoid survivor-only backtests. Refetched adjusted history can change; never mix old unadjusted entry prices with newly adjusted exits. Report returns, drawdown, turnover, sample count, missing outcomes and benchmark performance. Overlapping six-month outcomes are correlated and require dependence-aware uncertainty. Twenty sessions test operations, not six-month predictive ability. Calendar tests through September 2028 validate date handling only.

Cloud backups, quotas, access controls and retention remain specified in the [blueprint](IMPLEMENTATION_BLUEPRINT.md).
