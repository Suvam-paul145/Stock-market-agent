"""Transparent screening heuristics. Scores are relative ranks, not probabilities."""
import math
from collections import Counter
from statistics import mean, stdev

from stock_agent.core import timestamp
from .calendar import NY


HORIZONS = {
    "short_term": ("1–7 calendar days", 21, {"return_5": .35, "excess_20": .30, "volatility_quality": .20, "drawdown": .15}),
    "one_month": ("Within 1 calendar month", 64, {"excess_20": .35, "excess_63": .30, "trend_50": .15, "volatility_quality": .20}),
    "six_months": ("Next 6 calendar months", 253, {"excess_126": .30, "excess_252": .25, "trend_200": .20, "volatility_quality": .15, "drawdown": .10}),
}
RISK_CAP = {"conservative": .35, "balanced": .60, "aggressive": 1.0}
GAPS = [
    "Unvalidated price-based research screen; scores are not probabilities or expected returns.",
    "News, earnings dates, filing contents, valuation and financial health have not been reviewed.",
    "IEX-only prices and volume; the configured universe is not the entire US market.",
    "Execution spread, fees, slippage and INR/USD costs are not included.",
]


def number(value, positive=False):
    if type(value) not in (int, float) or not math.isfinite(value) or (positive and value <= 0):
        raise ValueError("Invalid numeric market value")
    return float(value)


def validate_bar(bar):
    stamp = timestamp(bar["t"])
    values = {k: number(bar[k], positive=True) for k in ("o", "h", "l", "c")}
    volume = number(bar["v"])
    if volume < 0 or not values["l"] <= min(values["o"], values["c"]) <= max(values["o"], values["c"]) <= values["h"]:
        raise ValueError("Inconsistent OHLC or volume")
    return dict(**values, v=volume, day=stamp.astimezone(NY).date().isoformat(), t=stamp)


def normalize_bars(raw, now, context):
    if not isinstance(raw, list):
        raise ValueError("Invalid bar series")
    normalized = {}
    for source in raw:
        bar = validate_bar(source)
        if bar["t"] > now or bar["day"] in normalized:
            raise ValueError("Future or duplicate daily bar")
        normalized[bar["day"]] = bar
    return normalized


def series_features(series, benchmark, dates):
    rows = [series[d] for d in dates]
    base = [benchmark[d] for d in dates]
    closes = [r["c"] for r in rows]
    returns = [b / a - 1 for a, b in zip(closes[-21:-1], closes[-20:])]
    volatility = stdev(returns) * math.sqrt(252)
    high, drawdown = closes[0], 0.0
    for close in closes:
        high = max(high, close)
        drawdown = min(drawdown, close / high - 1)
    features = dict(volatility=volatility, volatility_quality=-volatility, drawdown=drawdown,
                    price=closes[-1], average_iex_dollar_volume=mean(r["c"] * r["v"] for r in rows[-20:]),
                    average_iex_volume=mean(r["v"] for r in rows[-20:]))
    for n in (5, 20, 63, 126, 252):
        if len(rows) > n:
            features[f"return_{n}"] = closes[-1] / closes[-1-n] - 1
            features[f"excess_{n}"] = features[f"return_{n}"] - (base[-1]["c"] / base[-1-n]["c"] - 1)
    for n in (50, 200):
        if len(rows) >= n:
            features[f"trend_{n}"] = closes[-1] / mean(closes[-n:]) - 1
    return features


def percentile(value, values):
    # Midranks give ties equal scores. All tied -> 50, including a singleton.
    return 100 * (sum(v < value for v in values) + .5 * sum(v == value for v in values)) / len(values)


def rank_candidates(candidates, weights, config):
    for row in candidates:
        row["components"] = {key: round(percentile(row["metrics"][key], [r["metrics"][key] for r in candidates]), 4)
                             for key in weights}
        row["score"] = round(sum(row["components"][k] * weight for k, weight in weights.items()), 2)
    ordered = sorted(candidates, key=lambda r: (-r["score"], r["symbol"]))
    selected, sectors = [], Counter()
    for row in ordered:
        if sectors[row["sector"]] >= config.max_per_sector:
            continue
        sectors[row["sector"]] += 1
        selected.append(row | {"rank": len(selected) + 1})
        if len(selected) == config.top_n:
            break
    return selected


def eligible(metrics, config):
    if metrics["price"] < config.minimum_price_usd:
        return "Below minimum adjusted price"
    if metrics["average_iex_dollar_volume"] < config.minimum_iex_daily_dollar_volume:
        return "Below minimum observed IEX dollar volume"
    if metrics["volatility"] > RISK_CAP[config.risk_profile]:
        return "Above risk-profile volatility limit"
    return None


def horizon_boards(config, bars, now, context):
    series, errors = {}, {}
    for symbol in config.symbols + [config.benchmark]:
        try:
            series[symbol] = normalize_bars(bars.get(symbol, []), now, context)
        except (KeyError, ValueError, TypeError, AttributeError):
            errors[symbol] = "Invalid historical market data"
    boards = {}
    for key, (label, count, weights) in HORIZONS.items():
        dates = context["expected_sessions"][-count:]
        board = dict(label=label, status="unavailable", candidates=[], exclusions={}, coverage=0,
                     price_basis="Alpaca IEX daily bars, all corporate-action adjustments",
                     as_of_session=context["completed_session"], score_weights=weights,
                     recommendation_status="withheld_pending_evidence_and_forward_evaluation")
        boards[key] = board
        if len(dates) != count or any(d not in series.get(config.benchmark, {}) for d in dates):
            board["reason"] = "Benchmark history missing or invalid; no comparable ranking"
            continue
        candidates, covered = [], 0
        for symbol in config.symbols:
            source = series.get(symbol, {})
            if symbol in errors or any(d not in source for d in dates):
                board["exclusions"][symbol] = errors.get(symbol, "Missing required completed market sessions")
                continue
            covered += 1
            metrics = series_features(source, series[config.benchmark], dates)
            reason = eligible(metrics, config)
            period = {"short_term": 5, "one_month": 20, "six_months": 126}[key]
            if not reason and metrics[f"return_{period}"] <= 0:
                reason = "Non-positive momentum for this screen"
            if reason:
                board["exclusions"][symbol] = reason
                continue
            candidates.append(dict(symbol=symbol, sector=config.sectors[symbol], metrics=metrics,
                thesis=f"Positive trailing {period}-session momentum; compare the benchmark and risk measures below.",
                invalidation=f"Re-screen if trailing {period}-session return turns non-positive or data/risk gates fail.",
                missing_evidence=list(GAPS)))
        board["coverage"] = covered / len(config.symbols)
        if board["coverage"] < config.minimum_universe_coverage:
            board["reason"] = "Insufficient universe coverage; avoid ranking a biased partial response"
            continue
        board["status"] = "research_only"
        board["candidates"] = rank_candidates(candidates, weights, config)
        board["reason"] = ("Provisional technical shortlist; fundamental and catalyst review required" if candidates
                           else "No stock passed the configured data, momentum and risk gates")
    return boards, series


def leaders_board(config, snapshots, series, now, context):
    label = "Today's observed leaders" if context["is_today"] else "Latest completed session leaders (not today)"
    board = dict(label=label, status="unavailable", candidates=[], exclusions={}, coverage=0,
                 as_of_session=context["session"], recommendation_status="observation_only",
                 price_basis=("IEX minute close with running daily range/volume; corporate-action effects need review"
                              if context["market_open"] else "Completed IEX daily bars, all corporate-action adjustments"))
    dates = [d for d in context["expected_sessions"] if d < context["session"]][-20:]
    weights = {"session_change": .50, "volume_fraction": .30, "intraday_strength": .20}
    board["score_weights"] = weights
    candidates, covered = [], 0
    for symbol in config.symbols:
        try:
            if context["market_open"]:
                snap = snapshots[symbol]
                daily, previous = validate_bar(snap["dailyBar"]), validate_bar(snap["prevDailyBar"])
                minute = validate_bar(snap["minuteBar"])
                if daily["day"] != context["session"] or previous["day"] != dates[-1] or minute["day"] != context["session"]:
                    raise ValueError("Snapshot is from another session")
                age = (now - minute["t"]).total_seconds()
                if not 0 <= age <= config.max_snapshot_age_seconds or minute["t"] < timestamp(context["session_open"]):
                    raise ValueError("Snapshot is stale, future-dated or outside regular session")
                if not daily["l"] <= minute["c"] <= daily["h"]:
                    raise ValueError("Minute price is inconsistent with daily range")
                price, price_time = minute["c"], minute["t"]
                price_kind = "Minute bar close; timestamp denotes interval start"
            else:
                if context["completed_session"] != context["session"]:
                    raise ValueError("Awaiting completed daily data after the close")
                daily = series[symbol][context["session"]]
                previous = series[symbol][dates[-1]]
                price, price_time = daily["c"], daily["t"]
                price_kind = "Completed daily bar close; timestamp denotes session bucket, not last trade"
            # At least 20 historical full sessions, strictly before the observed session.
            history = [series[symbol][d] for d in dates]
            if len(history) != 20 or any(b["t"] > now for b in (daily, previous)):
                raise ValueError("Missing baseline or future timestamp")
            avg_volume = mean(r["v"] for r in history)
            if avg_volume <= 0:
                raise ValueError("No usable historical volume")
            covered += 1
            metrics = dict(session_change=price / previous["c"] - 1,
                volume_fraction=daily["v"] / avg_volume,
                intraday_strength=(price - daily["l"]) / (daily["h"] - daily["l"]) if daily["h"] > daily["l"] else .5,
                price=price, volume=daily["v"], price_observed_at=price_time.isoformat(), price_kind=price_kind)
            if metrics["price"] < config.minimum_price_usd or mean(r["v"] * r["c"] for r in history) < config.minimum_iex_daily_dollar_volume:
                board["exclusions"][symbol] = "Below observed liquidity or price threshold"
            elif metrics["session_change"] <= 0:
                board["exclusions"][symbol] = "No positive session price change"
            else:
                candidates.append(dict(symbol=symbol, sector=config.sectors[symbol], metrics=metrics,
                    thesis="Positive session price change, ranked with observed activity and position in the daily range.",
                    invalidation="Observations change with each refresh; leadership is not a buy signal.",
                    missing_evidence=[("Volume fraction compares partial session volume with 20 prior full sessions; not time-adjusted relative volume."
                                       if context["market_open"] else
                                       "Volume fraction compares completed daily volume with 20 prior full sessions; IEX coverage only."), *GAPS]))
        except (ValueError, KeyError, TypeError, IndexError, AttributeError):
            board["exclusions"][symbol] = "Missing, stale, inconsistent or invalid snapshot/history"
    board["coverage"] = covered / len(config.symbols)
    if board["coverage"] >= config.minimum_universe_coverage:
        board["status"] = "observations"
        board["candidates"] = rank_candidates(candidates, weights, config)
        board["reason"] = "Observed leaders within the configured universe; no prediction of further gains"
    else:
        board["reason"] = ("Insufficient fresh snapshot coverage; no current leaders published" if context["market_open"] else
                           "Insufficient completed-session coverage; no leaders published")
    return board
