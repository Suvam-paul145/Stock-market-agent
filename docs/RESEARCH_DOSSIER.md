# Personal stock research advisor: research dossier

Research assessed 2026-09-11. Audience: the project owner and implementing engineer. Official documentation and original papers support the findings below. Proposed architecture and acceptance thresholds are engineering judgments. No provider account, deployed workload, model quota or trading advantage was validated by this research.

## 1. Conclusions

A useful personal advisor can be designed around periodic cloud research, a small watchlist and zero recurring service fees. It cannot responsibly promise exhaustive real-time news, uninterrupted service or precise profitable predictions under those constraints.

The recommended platform is a scheduled Python worker, Supabase PostgreSQL and private Storage, and a private Vercel dashboard. PostgreSQL replaces the earlier proposal to exchange SQLite database files through object storage. The change buys straightforward transactions, indexed queries, unique constraints and multiple safe readers while avoiding file checkpoint coordination.

The recommended intelligence design is deterministic collection and calculation, bounded fact extraction, one research synthesis pass and a conditional evidence challenge. Extra agents must earn their cost through measured improvement. The system should continue publishing source-backed facts when AI is unavailable.

## 2. What information actually matters

For days-to-weeks decisions, useful evidence includes earnings and guidance changes, financing, material contracts or losses, litigation/regulatory developments, capital actions, liquidity concerns and known upcoming events. Their relevance depends on the company's business and expectations already reflected in its price.

News polarity is not a return forecast. A favorable announcement may disappoint expectations, and a negative announcement may remove uncertainty. Analysis should compare new information with the prior public state, show plausible alternative interpretations, and keep observed price reaction separate from its causal explanation.

Financial facts require period, unit and basis context. A quarterly revenue value cannot be compared blindly with a year-to-date value; a restated figure must not replace what a historical observer knew. Management guidance is an assertion about the future, not an observed result.

## 3. Market and news sources

| Source | Documented usefulness | Limits and adoption decision |
| --- | --- | --- |
| SEC EDGAR | Keyless submissions and company-fact APIs; authoritative filing trail. | Declare application/contact identity and respect fair-access limits. Required foundation; metadata alone is not filing analysis. [S01-S02] |
| Issuer investor relations | Original earnings releases, presentations and events. | Feeds vary by company; verify canonical URLs and source terms individually. Required per-stock onboarding. NVIDIA is an example, not a selected stock. [S03] |
| Alpaca | Free Basic equities context from IEX; documented delayed historical SIP access under the required end-time restriction. | Confirm account and endpoint entitlements. IEX is not consolidated market volume or an executable NBBO quote. Use completed, explicitly labelled bars for comparisons. [S04-S05] |
| Alpaca news | Historical and streaming news endpoints are documented. | Free real-time news entitlement is not established by the equities plan table. REST documentation distinguishes real-time access from a delayed cutoff. Optional after account and rights checks. [S06] |
| Finnhub | Candidate company news and earnings calendar source; free pricing advertises personal use and request limits. | Current terms restrict third-party access to data and derived results. Cloud AI use remains unresolved; do not enable merely because a free key exists. [S07-S08] |
| Alpha Vantage | Potential low-frequency reference source. | Standard free quota is 25 requests/day; real-time/delayed US price products are premium. Defer as the monitoring backbone. [S09] |
| FRED/ALFRED | Structured macro context and historical vintages. | Not a breaking-news stream; vintage terminology is not low-latency delivery. Respect underlying-series rights. [S10-S11] |
| Federal Reserve releases | Direct monetary-policy and related publications. | Use release feeds as event evidence and structured data separately. [S12] |

Default source set: SEC, verified issuer sources, Alpaca where entitled, and selected Federal Reserve/FRED evidence. A commercial news adapter is not a release prerequisite for a narrowly labelled issuer/filing research pilot. Broad news coverage must remain visibly incomplete until a suitable source passes access and processing checks.

For each source, record allowed storage, quoting, retention, cloud processing and redistribution separately. Publicly reachable content is not automatically an unrestricted dataset. Public code and private provider data are distinct deliverables. Source permissions also govern exports and off-site backups.

### Latency and event identity

Track four milestones: original publication, first observed by the application, analysis completion, and dashboard publication. Provider ingestion time may be unknown; do not substitute the fetch time for it. An hourly schedule only describes intended polling while services operate; it does not bound the original-event-to-review delay.

Deduplicate exact source items by provider identity and content hash. Group syndication into an event family, retaining provenance rather than treating repeated headlines as independent confirmation. Corrections and amendments create revisions. A later discovery is labelled newly observed, even if the source is old.

### Coverage evaluation

Build a reviewed sample of material events for the selected companies from the declared authoritative sources. Measure detected events, misses, irrelevant events, duplicates, and publication-to-observation delay. A missed publisher outside that universe is a coverage limitation, not something to hide in a high recall score. Actual free-account and cloud-origin access remains NOT VERIFIED.

## 4. Financial-agent research and its limits

| Reference | Useful idea | What it does not establish |
| --- | --- | --- |
| TradingAgents | Structured specialist analysis and interaction. | The inspected paper's short benchmark and substantial model/tool-call workload do not prove durable, free predictive superiority. Filtering historical tool inputs does not eliminate knowledge already in model weights. [S13] |
| FinRobot | Financial retrieval and report-generation patterns. | Documented API dependencies and analyst roles are not proof of free operation or days-to-weeks trading value. [S14] |
| FinGPT | Financial NLP tasks such as entity and sentiment extraction. | Performance on an NLP benchmark is not trading profitability. Open-source inference still needs compute. [S15] |
| ALCE | Evaluating citation completeness and support separately from answer correctness. | A syntactically valid URL or cited source ID does not establish that the claim follows from the passage. [S16] |

Adopt focused responsibilities, not a theatrical bull/bear debate. A second model can repeat the same false assumption; agreement should never be converted into a probability of correctness. Test extraction plus synthesis against synthesis alone, with the same support-review/publication checks on both arms. Every generated material factual claim receives a bounded claim-to-passage support review; unsupported claims are omitted. Activate the separate challenger for high-impact factual conflicts and material thesis changes. Human audits test whether the automated support reviewer actually helps rather than assuming its verdict is correct.

Use code for arithmetic, time comparisons, source eligibility and publication rules. Models can propose interpretations and identify missing evidence, but they cannot bypass a failed data check, change permissions or execute commands from source text.

## 5. Model strategy

Benchmark standard API access to Gemini 3.5 Flash for synthesis and Flash-Lite for extraction. The inspected pricing lists free-tier access for these standard text paths, while Search grounding is unavailable on the free API tier. Free-tier material may be used to improve Google's products. Exact live limits and capacity must be checked in the owner's project. [S17-S18]

The owner has accepted permitted public-source excerpts as inputs. Keep identity, portfolio data, private notes and secrets out of prompts. Restrict retrieval to approved source connectors and record every passage used. Do not automate a consumer chat UI as a substitute for an API.

Consumer subscriptions and developer products must be checked individually. Google's subscriber announcement describes AI Studio benefits; it is not a guarantee of unlimited production API capacity. Do not assume either that the subscription grants no benefits or that it funds this service. [S19]

If free eligibility is absent or quota is exhausted, queue optional analysis and publish deterministic facts with an explicit analysis-unavailable state. Preserve manual Gemini export. Do not consume trial credits or substitute a paid endpoint silently.

Local models are a later optional experiment, not the cloud fallback: hardware is unverified and the owner selected cloud operation. Model choice should be decided by the project's evidence-grounded tasks, not only general benchmark rank.

## 6. Database decision

### Workload requirements

The database must relate companies, sources, evidence revisions, events, claims, research runs and evaluation observations. It needs atomic publication, idempotent ingestion, multiple readers, controlled credentials, indexed temporal queries and a practical backup path. A vector database is unnecessary initially; source filtering and PostgreSQL full-text search should be evaluated first.

| Option | Findings | Decision |
| --- | --- | --- |
| Supabase PostgreSQL + private Storage | Free hosted relational database and object storage in one service; inactivity pause and resource limits apply. | Selected: reduces separate storage/checkpoint plumbing and supports evidence relationships and transactional publication. [S20-S23] |
| Neon PostgreSQL | Strong Postgres alternative with idle scale-to-zero. Official sources inspected differed in age and historical quota details. | Retain as an alternative; verify actual current account terms before any switch. It would still require a separate object-storage choice for source bodies. [S24] |
| Cloudflare D1 | Managed SQL with SQLite semantics, daily row budgets, free database size limits and recovery features. | Viable for a Workers-oriented system; not selected for this Python/Vercel design. It is not a PostgreSQL replacement with equivalent transaction/driver behavior. [S25-S26] |
| SQLite snapshots in Blob | Works as a constrained single-writer checkpoint design. | Superseded: unnecessary bundle restore, pointer, concurrency and transfer complexity now that managed Postgres is acceptable. |

Supabase's inspected Free plan includes a 500 MB database, 1 GB file storage and 5 GB uncached egress; projects may pause after a week of inactivity. Free service does not include managed daily backups or an uptime SLA. These limits support a small pilot only with retention, monitoring and independent recovery exports. [S20-S21]

The detailed pausing policy says even some actively used projects can have insufficient activity; scheduled research must not be described as a guarantee against pausing. The database quota also differs from physical disk capacity: exceeding the free database allowance can make it read-only. Detect both conditions and preserve capacity for operational status rather than waiting for enforcement. [S35-S36]

Use private buckets for retained documents. Store typed facts, metadata and citation excerpts in PostgreSQL; keep larger source bodies as content-addressed objects. The database's backup does not include Storage objects, so recovery must state which document bodies are recoverable and which will require refetching. [S21-S23]

Connection pools matter for the hosted environment. Use the documented session pooler for IPv4 worker sessions/administrative export, and transaction pooling for short web reads; do not hold transactions open while fetching sources or waiting for a model. Actual connection strings and TLS certificates come from the account, not a guessed hostname. [S22]

This selects the target platform. It does not provision Supabase or migrate the current SQLite files.

## 7. Hosting and cost feasibility

GitHub Actions performs bounded research jobs; Vercel serves a private read-only dashboard; Supabase holds durable state and source objects. No local computer must be continuously available. Jobs can be delayed, missed or blocked by quota; report freshness must reflect that. [S27-S28]

Vercel Hobby cron jobs are restricted to daily execution. Render Free sleeps after inactivity and loses local filesystem changes across sleep/restarts; its free Postgres has a limited lifetime. Neither is selected as the primary periodic worker or durable database. [S29-S30]

Use Vercel Authentication with All Deployments and owner-only access; test production and generated URLs. A private repository does not make a deployment private. Supabase data credentials never reach browser bundles. [S31]

Initial workload estimate: up to 400 committed runs/month at roughly three billed runner minutes on average equals 1,200 minutes, before CI and maintenance. GitHub Free's private allowance is 2,000 minutes, shared with other usage. This arithmetic is a planning model, not a measured cost guarantee. Storage and egress have separate budgets. [S27]

Stay on explicit Free/Hobby plans. Check shared usage before scheduling. Never multiply accounts, manufacture keep-alive traffic, or shard tasks solely to evade service restrictions. If free capacity is insufficient, reduce scope or present the measured conflict.

## 8. Evaluation and risk of misleading results

Keep three questions separate: is the software functioning, is the research useful, and does a forecast add investment value? The prototype's offline tests answer a limited part of the first question only.

Historical tests must enforce information availability, not merely event dates. Filing acceptance, revised economic data, restated accounts and later source edits can all leak future information. Historical prompts can also be contaminated by model knowledge. Prospective research records are therefore the default evidence for evaluating the AI's usefulness.

For future financial experiments, preregister the event and horizon, record every strategy/prompt change, and use chronological splits with appropriate separation for overlapping labels. Include costs, spreads, slippage and FX assumptions; use execution prices available after a signal. Compare against simple baselines and report uncertainty. Backtest-overfitting methods address selection bias but do not repair contaminated inputs. [S32-S33]

Do not equate a lower Brier score with calibration alone. If probabilities are introduced later, inspect reliability curves, counts and uncertainty as well as proper scoring rules, using temporally separate calibration data. [S34]

For the first release, the measurable gates are source/claim audits, material-event coverage, paired research comparisons and operational observation. See [requirements](REQUIREMENTS_AND_ASSUMPTIONS.md) and [implementation gates](IMPLEMENTATION_BLUEPRINT.md). Future profitability remains UNKNOWN.

## 9. Sources

All references were inspected in this conversation on 2026-09-11 unless noted. Dates on pages may describe earlier publication or updates. Exact free-account access is untested. Sources establish only the claims attributed above.

- S01 — SEC, [EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces).
- S02 — SEC, [Accessing EDGAR data](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data).
- S03 — NVIDIA Investor Relations, [RSS and event sources](https://investor.nvidia.com/investor-resources/rss/default.aspx).
- S04 — Alpaca, [Market data plans](https://docs.alpaca.markets/us/docs/about-market-data-api).
- S05 — Alpaca, [Market data FAQ](https://docs.alpaca.markets/us/docs/market-data-faq).
- S06 — Alpaca, [News endpoint](https://docs.alpaca.markets/us/reference/news-3).
- S07 — Finnhub, [Pricing](https://finnhub.io/pricing) and [API documentation](https://finnhub.io/docs/api).
- S08 — Finnhub, [Terms of service](https://finnhub.io/terms-of-service).
- S09 — Alpha Vantage, [Support and free-access limits](https://www.alphavantage.co/support/).
- S10 — Federal Reserve Bank of St. Louis, [FRED real-time periods and vintages](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html).
- S11 — Federal Reserve Bank of St. Louis, [FRED API terms](https://fred.stlouisfed.org/docs/api/terms_of_use.html).
- S12 — Federal Reserve, [Feed directory](https://www.federalreserve.gov/feeds/feeds.htm).
- S13 — Xiao et al., [TradingAgents, inspected version 5](https://arxiv.org/html/2412.20138v5).
- S14 — AI4Finance Foundation, [FinRobot repository](https://github.com/AI4Finance-Foundation/FinRobot).
- S15 — AI4Finance Foundation, [FinGPT repository](https://github.com/AI4Finance-Foundation/FinGPT).
- S16 — Gao et al., [Enabling Large Language Models to Generate Text with Citations](https://arxiv.org/abs/2305.14627).
- S17 — Google, [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing).
- S18 — Google, [Gemini rate limits](https://ai.google.dev/gemini-api/docs/rate-limits).
- S19 — Google, [AI Studio subscriber benefits announcement](https://blog.google/innovation-and-ai/technology/developers-tools/google-one-ai-studio/) and [API billing](https://ai.google.dev/gemini-api/docs/billing).
- S20 — Supabase, [Pricing and Free plan](https://supabase.com/pricing).
- S21 — Supabase, [Database backups](https://supabase.com/docs/guides/platform/backups).
- S22 — Supabase, [Connecting to PostgreSQL](https://supabase.com/docs/guides/database/connecting-to-postgres).
- S23 — Supabase, [Storage bucket fundamentals](https://supabase.com/docs/guides/storage/buckets/fundamentals).
- S24 — Neon, [Free plan guidance](https://neon.com/blog/how-to-make-the-most-of-neons-free-plan) and [pricing](https://neon.com/pricing). Direct pricing fetch failed; official search-index material was available but dated. Exact present quotas are not relied upon for the decision.
- S25 — Cloudflare, [D1 overview](https://developers.cloudflare.com/d1/) and [limits](https://developers.cloudflare.com/d1/platform/limits/).
- S26 — Cloudflare, [D1 pricing and quota behavior](https://developers.cloudflare.com/d1/platform/pricing/).
- S27 — GitHub, [Included product usage](https://docs.github.com/en/billing/reference/product-usage-included).
- S28 — GitHub, [Workflow schedule behavior](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows).
- S29 — Vercel, [Cron pricing and limits](https://vercel.com/docs/cron-jobs/usage-and-pricing).
- S30 — Render, [Free instance restrictions](https://render.com/docs/free).
- S31 — Vercel, [Deployment protection](https://vercel.com/docs/deployment-protection).
- S32 — Bailey et al., [The Probability of Backtest Overfitting](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf).
- S33 — Bailey and Lopez de Prado, [The Deflated Sharpe Ratio](https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf).
- S34 — Scikit-learn, [Probability calibration](https://scikit-learn.org/stable/modules/calibration.html).
- S35 — Supabase, [Free project pausing](https://supabase.com/docs/guides/platform/free-project-pausing).
- S36 — Supabase, [Database size and read-only behavior](https://supabase.com/docs/guides/platform/database-size).
- S37 — Supabase, [API hardening](https://supabase.com/docs/guides/api/securing-your-api).
- S38 — Vercel, [Blob pricing for the independent backup store](https://vercel.com/docs/vercel-blob/usage-and-pricing).
