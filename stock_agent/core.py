from __future__ import annotations

import json
import math
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def utcnow():
    return datetime.now(timezone.utc)


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def load_config(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    symbols = data.get("watchlist")
    if not isinstance(symbols, list) or not 1 <= len(symbols) <= 20:
        raise ValueError("Configure 1 to 20 watchlist symbols")
    if any(not isinstance(s, str) or not re.fullmatch(r"[A-Z][A-Z0-9.-]{0,9}", s) for s in symbols):
        raise ValueError("Use uppercase US stock symbols")
    if len(set(symbols)) != len(symbols):
        raise ValueError("Watchlist contains duplicate symbols")
    if data.get("horizon") not in ("unconfirmed", "intraday", "days_weeks", "months_years"):
        raise ValueError("Choose a supported horizon")
    for key, lower, upper in (("price_max_age_seconds", 1, 86400), ("filings_cache_seconds", 60, 86400)):
        value = data.get(key)
        if type(value) is not int or not lower <= value <= upper:
            raise ValueError(f"Invalid {key}")
    return data


def normalize_filings(payload, symbol):
    if not isinstance(payload, dict) or symbol not in payload.get("tickers", []):
        raise ValueError("SEC company symbol mismatch")
    cik = int(payload["cik"])
    if not 0 < cik < 10**10:
        raise ValueError("Invalid CIK")
    recent = payload["filings"]["recent"]
    columns = ("accessionNumber", "form", "filingDate", "acceptanceDateTime", "primaryDocument")
    if any(not isinstance(recent.get(k), list) for k in columns):
        raise ValueError("Missing filing columns")
    if len({len(recent[k]) for k in columns}) != 1:
        raise ValueError("Mismatched filing columns")
    rows = []
    seen = set()
    for accession, form, filed, accepted, document in zip(*(recent[k] for k in columns)):
        if not re.fullmatch(r"\d{10}-\d{2}-\d{6}", accession):
            raise ValueError("Invalid accession")
        if accession in seen:
            raise ValueError("Duplicate accession")
        seen.add(accession)
        datetime.strptime(filed, "%Y-%m-%d")
        timestamp(accepted)
        if not isinstance(form, str) or not isinstance(document, str):
            raise ValueError("Invalid filing metadata")
        # Link to SEC's filing index; do not trust a provider-supplied URL/path.
        url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession.replace('-', '')}/{accession}-index.html"
        rows.append(dict(id=accession, form=form, filed_at=filed, accepted_at=accepted, url=url))
    return dict(company=str(payload["name"]), cik=cik, filings=sorted(rows, key=lambda r: timestamp(r["accepted_at"]), reverse=True))


def normalize_trade(payload, symbol, now, max_age):
    trade = payload["trades"][symbol]
    price = trade["p"]
    if type(price) not in (float, int) or not math.isfinite(price) or price <= 0:
        raise ValueError("Invalid trade price")
    observed = timestamp(trade["t"])
    age = (now - observed).total_seconds()
    if age < -5:
        raise ValueError("Trade timestamp is in the future")
    return dict(price_usd=price, observed_at=trade["t"], age_seconds=max(0, round(age)),
                quality="stale" if age > max_age else "fresh", feed="IEX only", kind="latest trade; not an executable quote")


class Store:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY, source TEXT NOT NULL, fetched_at TEXT NOT NULL, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS cache (source TEXT PRIMARY KEY, snapshot_id INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS seen_filings (symbol TEXT, accession TEXT, PRIMARY KEY(symbol, accession));
            CREATE TABLE IF NOT EXISTS baselines (symbol TEXT PRIMARY KEY);
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY, symbol TEXT, accession TEXT, detected_at TEXT, payload TEXT,
                UNIQUE(symbol, accession));
            CREATE TABLE IF NOT EXISTS reports (id TEXT PRIMARY KEY, created_at TEXT, payload TEXT);
        """)

    def close(self):
        self.db.close()

    def cache_get(self, source, ttl, now):
        row = self.db.execute("SELECT s.fetched_at,s.payload FROM cache c JOIN snapshots s ON s.id=c.snapshot_id WHERE c.source=?", (source,)).fetchone()
        if row and 0 <= (now - timestamp(row[0])).total_seconds() < ttl:
            return json.loads(row[1]), row[0]
        return None

    def cache_put(self, source, payload, fetched_at):
        with self.db:
            cur = self.db.execute("INSERT INTO snapshots(source,fetched_at,payload) VALUES (?,?,?)", (source, fetched_at, json.dumps(payload)))
            self.db.execute("INSERT OR REPLACE INTO cache VALUES (?,?)", (source, cur.lastrowid))

    def record_filings(self, symbol, filings, detected_at):
        events = []
        with self.db:
            initialized = self.db.execute("SELECT 1 FROM baselines WHERE symbol=?", (symbol,)).fetchone()
            for filing in filings:
                cur = self.db.execute("INSERT OR IGNORE INTO seen_filings VALUES (?,?)", (symbol, filing["id"]))
                if initialized and cur.rowcount:
                    event = dict(symbol=symbol, type="newly_observed_filing", detected_at=detected_at,
                                 delivery="recorded_locally", **filing)
                    self.db.execute("INSERT INTO events(symbol,accession,detected_at,payload) VALUES (?,?,?,?)",
                                    (symbol, filing["id"], detected_at, json.dumps(event)))
                    events.append(event)
            self.db.execute("INSERT OR IGNORE INTO baselines VALUES (?)", (symbol,))
        return events, not bool(initialized)

    def save_report(self, report):
        with self.db:
            self.db.execute("INSERT INTO reports VALUES (?,?,?)", (report["id"], report["generated_at"], json.dumps(report, allow_nan=False)))
