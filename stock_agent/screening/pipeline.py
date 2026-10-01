import hashlib
import json
from datetime import timedelta

from stock_agent.core import normalize_filings, timestamp, utcnow
from stock_agent.providers import Alpaca, HttpClient, ProviderError, SEC
from . import STRATEGY_VERSION
from .analytics import GAPS, horizon_boards, leaders_board
from .calendar import market_context


class RunCache:
    """Bounded process-only cache. Screening never implicitly opens a SQLite DB."""
    def __init__(self):
        self.items = {}

    def cache_get(self, source, ttl, now):
        item = self.items.get(source)
        if item and 0 <= (now - timestamp(item[1])).total_seconds() < ttl:
            return item
        return None

    def cache_put(self, source, payload, fetched):
        self.items[source] = (payload, fetched)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def run_screen(config, *, client=None, now=None, include_filings=True):
    started = now or utcnow()
    context = market_context(started)
    client = client or HttpClient(RunCache(), budget=30, deadline_seconds=150)
    provider, statuses, inputs = Alpaca(client), {}, {}
    bars, snapshots = {}, {}
    # Request only previous dates; current partial daily bars must never enter a horizon signal.
    first = context["expected_sessions"][0]
    end = context["completed_session"] + "T23:59:59Z"
    try:
        bars, times = provider.daily_bars(config.symbols + [config.benchmark], first, end)
        inputs["bars"] = bars
        inputs["bar_pages_fetched_at"] = times
        statuses["history"] = dict(status="ok", fetched_at=times[-1], feed="iex", adjustment="all")
    except (ProviderError, ValueError, KeyError, TypeError, AttributeError):
        statuses["history"] = dict(status="unavailable", message="Historical data unavailable or incomplete; inspect credentials, connectivity and entitlements")
    try:
        snapshots, fetched, _ = provider.snapshots(config.symbols)
        if not isinstance(snapshots, dict) or any(s not in config.symbols for s in snapshots):
            raise ValueError("Invalid snapshot mapping")
        inputs["snapshots"] = snapshots
        inputs["snapshots_fetched_at"] = fetched
        statuses["snapshots"] = dict(status="ok", fetched_at=fetched, feed="iex")
    except (ProviderError, ValueError, KeyError, TypeError, AttributeError):
        snapshots = {}
        statuses["snapshots"] = dict(status="unavailable", message="Snapshots unavailable; no current leadership claim")
    # Analysis cutoff follows collection; original market timestamps remain the freshness authority.
    cutoff = now or utcnow()
    context = market_context(cutoff)
    boards, normalized = horizon_boards(config, bars, cutoff, context)
    boards["today"] = leaders_board(config, snapshots, normalized, cutoff, context)
    # Filing metadata is enrichment only; titles/form types cannot establish an investment thesis.
    symbols = list(dict.fromkeys(c["symbol"] for b in boards.values() for c in b["candidates"]))
    filings = {}
    if include_filings:
        sec = SEC(client)
        for symbol in symbols:
            try:
                payload, fetched, _ = sec.filings(symbol, 86400)
                normalized_filings = normalize_filings(payload, symbol)
                if any(timestamp(f["accepted_at"]) > cutoff for f in normalized_filings["filings"]):
                    raise ValueError("Filing beyond evidence cutoff")
                filings[symbol] = dict(status="ok", fetched_at=fetched, company=normalized_filings["company"],
                    filings=normalized_filings["filings"][:5], coverage="Recent SEC metadata only; filing bodies not analyzed")
            except (ProviderError, ValueError, KeyError, TypeError, AttributeError):
                filings[symbol] = dict(status="unavailable", coverage="No inference about absence of filings")
    inputs["filings"] = filings
    for board in boards.values():
        for candidate in board["candidates"]:
            symbol = candidate["symbol"]
            source_name = filings.get(symbol, {}).get("company")
            candidate["company"] = source_name or config.company_names.get(symbol) or "Company name unavailable"
            candidate["company_name_source"] = ("SEC submissions" if source_name else
                                                "configuration" if symbol in config.company_names else "unavailable")
    report = dict(schema_version=1, strategy_version=STRATEGY_VERSION, mode="live_research_screen",
        started_at=started.isoformat(), generated_at=cutoff.isoformat(), expires_at=(cutoff + timedelta(minutes=60)).isoformat(),
        universe=config.model_dump(), universe_hash=digest(config.model_dump()), context=context,
        boards=boards, providers=statuses, filings=filings, request_count=client.used,
        evidence_hash=digest(inputs), limitations=GAPS,
        deployment="Local on-demand screening; no background monitoring or cloud publication",
        evaluation="Forward evaluation not yet completed; no expected-return or success-probability estimate",
        assumptions=["Starter universe and sector labels are curated configuration, not verified index membership.",
                     "Balanced risk defaults apply unless changed in the screening configuration."])
    return report, inputs
