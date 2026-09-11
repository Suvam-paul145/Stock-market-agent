# Provider decisions

> Historical 2026-09-10 source notes for the local prototype. The expanded [research dossier](RESEARCH_DOSSIER.md) is the current decision reference; it includes model processing rights, database comparisons, cloud constraints and updated source findings. Preserve these notes as historical context rather than a current architecture specification.

Official documentation inspected on 2026-09-10. These are documentation findings, not proof of access from this machine. Recheck terms and account entitlements before changing providers or usage.

| Source | Finding | Decision |
| --- | --- | --- |
| SEC EDGAR | Submissions and XBRL APIs require no API key; submissions expose recent filing metadata. | First authoritative filing source. Implement recent submissions now; add filing bodies and XBRL analysis later. |
| SEC access policy | Identify the application/contact in User-Agent; published maximum is 10 requests/second. | Use a conservative sequential client, cache the ticker mapping and avoid broad crawling. |
| Alpaca Basic | Free individual plan provides real-time equities data from IEX; authentication required. | Optional price adapter explicitly selects IEX. Do not imply consolidated market coverage. Eligibility and credentials pending. |
| Alpha Vantage | Standard free access is 25 requests/day; verified educational/open-source exceptions require verification. Real-time and 15-minute delayed US data are premium. | Defer; do not use as a claimed free real-time primary feed. |
| Gemini API | Free-tier access is model/quota dependent; billing attaches to API projects. | No API integration in v0.1. Manual report upload avoids application API charges. |

Sources:

- [SEC APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
- [SEC access guidance](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data)
- [Alpaca market data plans and authentication](https://docs.alpaca.markets/us/docs/about-market-data-api)
- [Alpaca latest trades endpoint](https://docs.alpaca.markets/us/reference/stocklatesttrades-1)
- [Alpha Vantage support and limits](https://www.alphavantage.co/support/)
- [Gemini API billing](https://ai.google.dev/gemini-api/docs/billing)

## Remaining research

Before news integration, compare permitted personal use, headline/full-text rights, publication timestamps, historical retention, free quotas, coverage and account eligibility. Finnhub is a candidate from the handoff, not an approved or verified selection. Evaluate earnings dates against company investor-relations pages and record confirmed versus estimated dates.

For historical evaluation, establish adjusted/unadjusted price semantics, split/dividend events, survivorship limitations, calendar alignment and point-in-time availability before selecting a dataset. No price provider was proven sufficient for a backtest in this milestone.

No paid subscription, external account, API billing, or deployment was created.
