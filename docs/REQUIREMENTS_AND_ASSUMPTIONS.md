# Personal stock research advisor: requirements and assumptions

Status: confirmed product direction and proposed release criteria, 2026-09-11. This document specifies the intended system; it does not claim those capabilities exist today.

**Superseding scope, 2026-09-17:** The user requests five candidates for 1–7 days, one month and six months, today's leaders and a two-year operating target. Read [the addendum](MULTI_HORIZON_IMPLEMENTATION.md). It supersedes R02/R03 and the broad-screening deferral below; free-cost, privacy and evidence requirements remain in force.

## 1. Purpose

Help Suvam make better-informed personal decisions about a small US-stock watchlist over days to weeks. The advisor should explain what changed, why it may matter, what evidence challenges the interpretation, and what to investigate next. Trades remain manual in INDmoney.

An excellent result is a useful, timely, traceable research process that saves effort and catches material risks. Predictive superiority is a separate empirical question. More agents, longer reports, or confident language do not establish an advantage.

## 2. Confirmed decisions

| ID | Decision | Consequence |
| --- | --- | --- |
| R01 | Personal use only | Single owner; private dashboard; no public research distribution. |
| R02 | US equities, days to weeks | Prioritize catalysts, earnings, guidance, financial condition, sector context and material risks. |
| R03 | User-selected stocks; exact symbols remain configurable | Support one to five pilot stocks; do not treat demonstration tickers as selected investments. |
| R04 | Decision quality is the first success measure | Evaluate factual support, important-event coverage, useful counterevidence and time saved before claiming predictive value. |
| R05 | Automatic research, manual trades | Data collection and bounded analysis may run unattended; broker execution is excluded. |
| R06 | Strictly free recurring services | No paid API fallback, expiring trial dependency, paid hosting upgrade or assumed education credits. Existing internet/electricity are not claimed to be economically free. |
| R07 | Cloud operation with possible delays | The owner's computer is optional; do not require a local machine to remain on. |
| R08 | 30-60 minute target during US market hours | Start at the hourly end, measure performance, and display provider/scheduler lag. This is a target, not a guaranteed publication-to-alert delay. |
| R09 | Private dashboard first | No outbound email, Telegram or phone notifications in the initial release. |
| R10 | Research only initially | Do not request balances or holdings, size positions, or implement personalized portfolio exposure rules. |
| R11 | Permitted public evidence may go to a verified free Gemini API project | Exclude secrets, balances, holdings, private notes and sources with unresolved processing rights. |
| R12 | Other databases are acceptable | Select Supabase PostgreSQL for the target cloud architecture; SQLite remains only in the historical prototype until a deliberate migration. |
| R13 | Research and documentation precede further coding | Deliver the dossier and implementation blueprint now; implementing application features is the following stage. |

The original shared ChatGPT URL failed to fetch. The available "Stock Prediction Software Feasibility" conversation and project handoff supplied earlier context. This is not a claim of access to every past conversation. Decisions confirmed directly in the current task supersede older assumptions in that handoff.

## 3. User experience

On opening the dashboard, the owner sees:

1. When collection last succeeded, when the next run is expected, and which sources or AI functions are unavailable.
2. Material changes since the previous review, grouped by company and event rather than duplicated headlines.
3. A concise company review with evidence links, supporting passages, dates, interpretations, counterevidence and missing information.
4. The conditions that would weaken a hypothesis and the events that should trigger another review.
5. A research history showing what was believed at the time, what later changed, and any correction.

Reading a report must not automatically launch expensive analysis. The initial refresh control is GitHub's manual workflow dispatch; an authenticated in-app dispatch button is a later convenience, not a second writer.

### Example behavior — entirely hypothetical

A fictional company raises revenue guidance but lowers its margin outlook. The advisor identifies both changes from the original announcement, retrieves the preceding guidance on a comparable basis, and flags a possible conflict between growth and profitability. It distinguishes management's projections from realized results. It shows whether the price response is from delayed consolidated bars or a single-exchange observation.

The review does not infer that positive revenue news guarantees a rising share price. If previous guidance or the underlying document is missing, it states that the comparison is incomplete. A corrected release creates a revision and a visible correction to the earlier note.

## 4. First-release boundaries

Included: source provenance, filings and selected financial facts, issuer announcements, verified price context, macro context, permitted news when available, event grouping, bounded AI research with claim-to-passage support review, private reports, failure visibility, exports and an evaluation journal. Automated support checks are evaluated through human source audits; they are not a guarantee of correctness.

Deferred: broad market screening, options/shorting/leverage, execution, holdings ingestion, personalized sizing, arbitrary target prices, calibrated forecasts, social-media sentiment, alternative data, self-training, outbound alerts and public access. These require new evidence or a separate scope decision, not merely another agent role.

An absent analysis is not a hold recommendation. Source freshness, coverage and analysis quality are separate dimensions. A recent fetch of an old price does not make the price current. A report may be complete for a narrow filing question while remaining inadequate for a trading decision.

## 5. Success and release criteria

The following are proposed engineering targets, not measured results or statistical guarantees:

| Dimension | Initial assessment |
| --- | --- |
| Extraction | Review 100 varied source documents; at least 95% required-field accuracy and no undetected critical entity/date/currency/unit error in the release set. |
| Claim support | Review 200 material claims; all have resolvable evidence IDs, at least 98% have genuinely supporting evidence, and no unsupported decision-critical numerical claim passes. |
| Coverage | Compare against a manually reviewed event sample from the declared source universe; report misses, discovery lag and unavailable sources. Never report whole-market recall. |
| Research utility | Paired, blinded comparisons with the same evidence and similar token budgets; retain specialist passes only when they improve support, useful coverage or review time without increasing critical errors. |
| Operations | Observe 20 market sessions; record expected runs, successful/degraded/missed runs, p50/p95 delays, source age, model quota and storage growth. |
| Financial usefulness | Unproven in the research release. Future forecasts need a separate preregistered forward evaluation after costs. |

Always report sample size, disagreements and uncertainty. A small reviewed sample cannot establish an error-free system.

## 6. Assumptions register

| Assumption | Risk | Resolution and default |
| --- | --- | --- |
| Free source coverage is sufficient for these stocks | High | Measure issuer/SEC event coverage during the pilot. Leave commercial news disabled until entitlement and processing rights are clear. |
| Free Gemini entitlement supports automatic reviews | High | Verify the exact API project, model, quotas and billing before activation. If unavailable, publish facts and export a manual review package. |
| Free cloud capacity fits the schedule | High | Measure runner time, database/storage/egress use. Reduce optional analysis and clearly mark missed service targets before approaching caps. |
| AI specialists outperform one synthesis pass | High | Use controlled comparisons. Remove unnecessary roles. |
| Database account and one free project are available | Medium | Check the owner's actual Supabase plan/project allowance during setup. Do not create duplicate accounts or silently buy capacity. |
| Provider endpoints work from hosted runners | Medium | Test a small real request from the eventual worker; source documentation and local mocks do not establish cloud access. |
| Actual stock symbols fit source mappings | Medium | Resolve each ticker, issuer CIK, exchange and canonical investor-relations sources before enabling it. |
| Historical evidence supports forecasting evaluation | High | Audit availability times, revisions and universe history. Mark historical LLM contamination and missing delistings explicitly. |
| Research quality implies profitable trades | High | Do not assume it. Keep investment outcomes as a separate future evaluation. |

## 7. Questions intentionally deferred

Exact tickers and account entitlements are required at onboarding, not to write the design. No capital, holdings, risk-tolerance or loss-limit questions are needed for this research-only release. Ask those only if portfolio-aware or trade-setup functionality is later requested.

Ask again if strict zero spend cannot coexist with the chosen service target, permitted news proves inadequate, private access cannot be established, or the objective expands to personalized recommendations. Present the measured shortfall and concrete choices, not a generic permission request.

## 8. Reading order

Read this document first, then [the research dossier](RESEARCH_DOSSIER.md), then [the implementation blueprint](IMPLEMENTATION_BLUEPRINT.md). The prototype's [verification record](VERIFICATION.md) remains historical evidence only.
