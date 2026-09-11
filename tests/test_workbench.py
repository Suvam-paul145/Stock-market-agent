import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import HTTPError

from stock_agent.core import Store, load_config, normalize_filings, normalize_trade, timestamp
from stock_agent.providers import HttpClient, ProviderError
from stock_agent.research import collect, export


NOW = datetime(2026, 9, 10, 12, tzinfo=timezone.utc)


def filing_payload():
    return {"name": "Synthetic test company", "cik": 1, "tickers": ["TEST"], "filings": {"recent": {
        "accessionNumber": ["0000000001-26-000001"], "form": ["8-K"], "filingDate": ["2026-09-09"],
        "acceptanceDateTime": ["2026-09-09T12:00:00Z"], "primaryDocument": ["test.htm"]}}}


class ValidationTests(unittest.TestCase):
    def test_naive_time_rejected(self):
        with self.assertRaises(ValueError):
            timestamp("2026-09-10T12:00:00")

    def test_stale_trade_uses_observation_time(self):
        payload = {"trades": {"TEST": {"p": 100, "t": (NOW - timedelta(hours=1)).isoformat()}}}
        self.assertEqual(normalize_trade(payload, "TEST", NOW, 900)["quality"], "stale")

    def test_nonfinite_negative_boolean_and_future_prices_rejected(self):
        for price in (float("nan"), float("inf"), -1, 0, True, "100"):
            with self.subTest(price=price), self.assertRaises(ValueError):
                normalize_trade({"trades": {"TEST": {"p": price, "t": NOW.isoformat()}}}, "TEST", NOW, 900)
        with self.assertRaises(ValueError):
            normalize_trade({"trades": {"TEST": {"p": 1, "t": (NOW + timedelta(minutes=2)).isoformat()}}}, "TEST", NOW, 900)

    def test_filings_require_consistent_columns_and_symbol(self):
        p = filing_payload()
        self.assertEqual(normalize_filings(p, "TEST")["filings"][0]["form"], "8-K")
        with self.assertRaises(ValueError):
            normalize_filings(p, "WRONG")
        p["filings"]["recent"]["form"] = []
        with self.assertRaises(ValueError):
            normalize_filings(p, "TEST")

    def test_duplicate_accessions_rejected(self):
        p = filing_payload()
        for values in p["filings"]["recent"].values():
            values.extend(values[:])
        with self.assertRaises(ValueError):
            normalize_filings(p, "TEST")

    def test_config_rejects_paths_duplicate_symbols_and_negative_ttl(self):
        config = load_config("config.example.json")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            for change in ({"watchlist": ["../../secret"]}, {"watchlist": ["AAPL", "AAPL"]}, {"filings_cache_seconds": -1}):
                path.write_text(json.dumps(config | change))
                with self.assertRaises(ValueError):
                    load_config(path)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / "test.sqlite3")
        self.config = load_config("config.example.json")

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_baseline_then_deduplicated_events_persist(self):
        rows = normalize_filings(filing_payload(), "TEST")["filings"]
        events, baseline = self.store.record_filings("TEST", rows, NOW.isoformat())
        self.assertTrue(baseline)
        self.assertEqual(events, [])
        next_filing = rows[0] | {"id": "0000000001-26-000002"}
        events, baseline = self.store.record_filings("TEST", rows + [next_filing], NOW.isoformat())
        self.assertEqual(len(events), 1)
        self.assertFalse(baseline)
        self.assertEqual(self.store.record_filings("TEST", [next_filing], NOW.isoformat())[0], [])
        self.assertEqual(self.store.db.execute("SELECT count(*) FROM events").fetchone()[0], 1)

    def test_cache_expiry_and_original_fetch_time(self):
        self.store.cache_put("test", {"ok": True}, NOW.isoformat())
        self.assertEqual(self.store.cache_get("test", 60, NOW)[1], NOW.isoformat())
        self.assertIsNone(self.store.cache_get("test", 60, NOW + timedelta(seconds=60)))
        self.assertIsNone(self.store.cache_get("test", 60, NOW - timedelta(seconds=1)))

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_credentials_are_visible_and_no_network_used(self):
        with patch("stock_agent.providers.HttpClient.get", side_effect=AssertionError("network must not run")):
            result = collect(self.config, self.store)
        self.assertEqual(result["request_count"], 0)
        self.assertFalse(result["forecasts_enabled"])
        self.assertTrue(all(p["status"] == "not_configured" for s in result["symbols"] for p in s["providers"].values()))

    def test_demo_export_is_synthetic_escaped_and_has_no_network(self):
        with patch("stock_agent.providers.HttpClient.get", side_effect=AssertionError("network must not run")):
            result = collect(self.config, self.store, demo=True)
        self.assertEqual(result["mode"], "synthetic_demo")
        result["symbols"][0]["company"] = "<script>alert('x')</script>"
        directory = export(result, Path(self.tmp.name) / "reports")
        page = (directory / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("<script>", page)
        self.assertEqual(json.loads((directory / "research.json").read_text())["mode"], "synthetic_demo")
        self.assertTrue((directory / "gemini_prompt.txt").exists())
        with self.assertRaises(FileExistsError):
            export(result, Path(self.tmp.name) / "reports")

    def test_rate_limit_no_retry_and_error_body_redacted(self):
        client = HttpClient(self.store)
        client.opener.open = Mock(side_effect=HTTPError("https://data.sec.gov/test", 429, "SECRET", {}, None))
        with self.assertRaises(ProviderError) as caught:
            client.get("https://data.sec.gov/test", {})
        self.assertNotIn("SECRET", str(caught.exception))
        self.assertEqual(client.used, 1)

    def test_request_budget_stops_network(self):
        client = HttpClient(self.store, budget=0)
        client.opener.open = Mock()
        with self.assertRaises(ProviderError):
            client.get("https://data.sec.gov/test", {})
        client.opener.open.assert_not_called()

    def test_unapproved_host_rejected(self):
        with self.assertRaises(ProviderError):
            HttpClient(self.store).get("https://example.com", {})

    def test_partial_provider_failure_keeps_valid_other_evidence(self):
        self.config["watchlist"] = ["TEST"]
        with patch("stock_agent.research.SEC.filings", return_value=(filing_payload(), NOW.isoformat(), False)), \
             patch("stock_agent.research.Alpaca.trades", side_effect=ProviderError("network unavailable")):
            result = collect(self.config, self.store)
        row = result["symbols"][0]
        self.assertEqual(row["providers"]["sec"]["status"], "ok")
        self.assertEqual(row["providers"]["alpaca"]["status"], "error")
        self.assertEqual(len(row["filings"]), 1)


if __name__ == "__main__":
    unittest.main()
