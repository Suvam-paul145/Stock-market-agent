import copy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from stock_agent.environment import load_local_environment
from stock_agent.providers import Alpaca, ProviderError
from stock_agent.screening.analytics import horizon_boards, leaders_board, percentile
from stock_agent.screening.calendar import market_context, NY
from stock_agent.screening.config import load_screen_config
from stock_agent.screening.pipeline import run_screen, digest
from stock_agent.screening.report import export_screen

NOW = datetime(2026, 9, 17, 18, 0, tzinfo=timezone.utc)


@pytest.fixture
def fixture():
    config = load_screen_config("screening.example.json")
    context = market_context(NOW)
    bars = {}
    for index, symbol in enumerate(config.symbols + [config.benchmark]):
        rows = []
        for i, day in enumerate(context["expected_sessions"]):
            price = 100 * (1 + .0003 + index * .00002) ** i
            stamp = datetime.fromisoformat(day).replace(tzinfo=NY).isoformat()
            rows.append(dict(t=stamp, o=price, h=price*1.01, l=price*.99, c=price, v=1000000))
        bars[symbol] = rows
    snapshots = {}
    for index, symbol in enumerate(config.symbols):
        previous = bars[symbol][-1]
        price = previous["c"] * (1 + .005 * (index+1))
        day = datetime.fromisoformat(context["session"]).replace(tzinfo=NY).isoformat()
        daily = dict(t=day, o=price*.99, h=price*1.01, l=price*.98, c=price, v=500000)
        snapshots[symbol] = dict(dailyBar=daily, prevDailyBar=previous,
                                minuteBar=daily | {"t": (NOW-timedelta(minutes=1)).isoformat()})
    return config, context, bars, snapshots


def test_distinct_horizons_and_sector_caps(fixture):
    config, context, bars, snapshots = fixture
    boards, series = horizon_boards(config, bars, NOW, context)
    boards["today"] = leaders_board(config, snapshots, series, NOW, context)
    for board in boards.values():
        assert board["coverage"] == 1
        assert len(board["candidates"]) == 5
        sectors = [r["sector"] for r in board["candidates"]]
        assert all(sectors.count(s) <= 2 for s in sectors)
    assert boards["short_term"]["score_weights"] != boards["six_months"]["score_weights"]
    assert boards["six_months"]["recommendation_status"].startswith("withheld")


def test_hand_calculated_metrics_and_ties(fixture):
    config, context, bars, _ = fixture
    boards, _ = horizon_boards(config, bars, NOW, context)
    row = boards["short_term"]["candidates"][0]
    source = bars[row["symbol"]]
    assert row["metrics"]["return_5"] == pytest.approx(source[-1]["c"] / source[-6]["c"] - 1)
    assert row["metrics"]["return_20"] == pytest.approx(source[-1]["c"] / source[-21]["c"] - 1)
    assert percentile(7, [7, 7, 7]) == 50


def test_missing_benchmark_stops_all_horizon_rankings(fixture):
    config, context, bars, _ = fixture
    bars["SPY"].pop()
    boards, _ = horizon_boards(config, bars, NOW, context)
    assert all(not b["candidates"] and b["status"] == "unavailable" for b in boards.values())


@pytest.mark.parametrize("corruption", ["future", "duplicate", "nan", "ohlc", "negative_volume", "missing_session"])
def test_invalid_universe_cannot_silently_rank_partial_data(fixture, corruption):
    config, context, bars, _ = fixture
    for symbol in config.symbols[:8]:
        if corruption == "future":
            bars[symbol][-1]["t"] = (NOW+timedelta(days=1)).isoformat()
        elif corruption == "duplicate":
            bars[symbol].append(copy.deepcopy(bars[symbol][-1]))
        elif corruption == "nan":
            bars[symbol][-1]["c"] = float("nan")
        elif corruption == "ohlc":
            bars[symbol][-1]["h"] = 1
        elif corruption == "negative_volume":
            bars[symbol][-1]["v"] = -1
        else:
            bars[symbol].pop(-2)
    boards, _ = horizon_boards(config, bars, NOW, context)
    assert all(b["status"] == "unavailable" for b in boards.values())


def test_current_partial_day_does_not_change_horizon_scores(fixture):
    config, context, bars, snapshots = fixture
    expected, _ = horizon_boards(config, bars, NOW, context)
    for symbol in config.symbols:
        bars[symbol].append(snapshots[symbol]["dailyBar"])
    actual, _ = horizon_boards(config, bars, NOW, context)
    assert actual == expected


def test_short_history_can_qualify_only_for_short_horizon(fixture):
    config, context, bars, _ = fixture
    bars = {s: rows[-21:] for s, rows in bars.items()}
    boards, _ = horizon_boards(config, bars, NOW, context)
    assert boards["short_term"]["status"] == "research_only"
    assert boards["one_month"]["status"] == "unavailable"
    assert boards["six_months"]["status"] == "unavailable"


def test_stale_snapshots_do_not_publish_todays_leaders(fixture):
    config, context, bars, snapshots = fixture
    _, series = horizon_boards(config, bars, NOW, context)
    for snap in snapshots.values():
        snap["minuteBar"]["t"] = (NOW-timedelta(hours=1)).isoformat()
    result = leaders_board(config, snapshots, series, NOW, context)
    assert result["status"] == "unavailable"
    assert result["candidates"] == []


def test_inconsistent_snapshot_prices_cannot_inherit_fresh_timestamp(fixture):
    config, context, bars, snapshots = fixture
    _, series = horizon_boards(config, bars, NOW, context)
    for snap in snapshots.values():
        snap["dailyBar"].update(o=200, c=200, h=201, l=199)
        snap["minuteBar"].update(o=100, c=100, h=101, l=99)
    result = leaders_board(config, snapshots, series, NOW, context)
    assert result["status"] == "unavailable" and not result["candidates"]


def test_latest_completed_session_works_without_extended_hours_snapshots(fixture):
    config, _, bars, _ = fixture
    before_open = datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc)
    context = market_context(before_open)
    _, series = horizon_boards(config, bars, before_open, context)
    result = leaders_board(config, {}, series, before_open, context)
    assert result["status"] == "observations" and len(result["candidates"]) == 5
    assert result["as_of_session"] == "2026-09-16"
    assert "not today" in result["label"]
    assert "completed daily volume" in result["candidates"][0]["missing_evidence"][0]


def test_downward_market_does_not_force_five_candidates(fixture):
    config, context, bars, _ = fixture
    for rows in bars.values():
        for i, bar in enumerate(rows):
            price = 200 - i * .1
            bar.update(o=price, c=price, h=price+1, l=price-1)
    boards, _ = horizon_boards(config, bars, NOW, context)
    assert all(b["status"] == "research_only" and b["candidates"] == [] for b in boards.values())


@pytest.mark.parametrize("moment,session,is_today,open_time", [
    ("2026-09-19T18:00:00+00:00", "2026-09-18", False, "13:30"),
    ("2026-12-25T18:00:00+00:00", "2026-12-24", False, "14:30"),
    ("2027-03-15T15:00:00+00:00", "2027-03-15", True, "13:30"),
    ("2028-09-15T18:00:00+00:00", "2028-09-15", True, "13:30"),
])
def test_calendar_holidays_dst_and_two_year_horizon(moment, session, is_today, open_time):
    context = market_context(datetime.fromisoformat(moment))
    assert context["session"] == session and context["is_today"] == is_today
    assert open_time in context["session_open"]
    assert len(context["expected_sessions"]) == 253


def test_early_close_and_completion_delay():
    context = market_context(datetime.fromisoformat("2026-11-27T18:10:00+00:00"))
    assert "18:00" in context["session_close"]
    assert context["completed_session"] == "2026-11-25"
    assert not context["market_open"]


class FakeClient:
    used = 0

    def __init__(self, responses):
        self.responses = iter(responses)
        self.urls = []

    def get(self, url, headers, ttl=0):
        self.used += 1
        self.urls.append(url)
        return next(self.responses), NOW.isoformat(), False


def test_pagination_includes_later_symbols_and_forces_free_feed():
    client = FakeClient([{"bars": {"AAPL": [{"fixture": 1}]}, "next_page_token": "next"},
                         {"bars": {"MSFT": [{"fixture": 2}]}, "next_page_token": None}])
    with patch.object(Alpaca, "headers", return_value={}):
        bars, pages = Alpaca(client).daily_bars(["AAPL", "MSFT"], "2025-01-01", "2026-01-01")
    assert len(bars["MSFT"]) == 1 and len(pages) == 2
    assert all("feed=iex" in u and "adjustment=all" in u for u in client.urls)
    assert "page_token=next" in client.urls[1]


def test_repeated_pagination_token_rejected():
    client = FakeClient([{"bars": {}, "next_page_token": "again"}] * 2)
    with patch.object(Alpaca, "headers", return_value={}), pytest.raises(ProviderError):
        Alpaca(client).daily_bars(["AAPL"], "2025-01-01", "2026-01-01")


def test_local_env_does_not_override_or_interpolate(monkeypatch, tmp_path):
    monkeypatch.setenv("APCA_API_KEY_ID", "shell-value")
    monkeypatch.delenv("APCA_API_SECRET_KEY", raising=False)
    monkeypatch.delenv("UNTRUSTED_SETTING", raising=False)
    path = tmp_path / ".env"
    path.write_text("APCA_API_KEY_ID=file-value\nAPCA_API_SECRET_KEY='${APCA_API_KEY_ID}'\nUNTRUSTED_SETTING=x\n")
    load_local_environment(path)
    import os
    assert os.getenv("APCA_API_KEY_ID") == "shell-value"
    assert os.getenv("APCA_API_SECRET_KEY") == "${APCA_API_KEY_ID}"
    assert os.getenv("UNTRUSTED_SETTING") is None


def test_complete_pipeline_export_keeps_inputs_and_escapes_text(fixture, tmp_path):
    config, _, bars, snapshots = fixture
    config = config.model_copy(update={"universe_name": "<script>alert('bad')</script>"})
    client = FakeClient([{"bars": bars, "next_page_token": None}, snapshots])
    with patch.object(Alpaca, "headers", return_value={}):
        report, inputs = run_screen(config, client=client, now=NOW, include_filings=False)
    directory = export_screen(report, inputs, tmp_path)
    assert report["evidence_hash"] == digest(inputs)
    assert len(report["boards"]["six_months"]["candidates"]) == 5
    document = (directory / "index.html").read_text(encoding="utf-8")
    assert "<script>" not in document and "&lt;script&gt;" in document
    assert "Research shortlists, not validated trade recommendations" in document
    assert len(list(Path(directory).iterdir())) == 4
