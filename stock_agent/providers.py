from __future__ import annotations

import json
import os
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler

from .core import utcnow


class ProviderError(Exception):
    """A safe error message without credentials or response bodies."""


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ProviderError("Unexpected provider redirect; request stopped")


class HttpClient:
    def __init__(self, store, budget=30, deadline_seconds=None):
        self.store, self.budget, self.used = store, budget, 0
        self.last_request = 0.0
        self.deadline = time.monotonic() + deadline_seconds if deadline_seconds else None
        self.opener = build_opener(NoRedirect())

    def get(self, url, headers, ttl=0):
        if urlparse(url).scheme != "https" or urlparse(url).hostname not in ("www.sec.gov", "data.sec.gov", "data.alpaca.markets"):
            raise ProviderError("Provider host is not allowed")
        cached = self.store.cache_get(url, ttl, utcnow())
        if cached:
            return cached[0], cached[1], True
        for attempt in range(3):
            if self.deadline and time.monotonic() + 16 > self.deadline:
                raise ProviderError("Per-run time budget exhausted")
            if self.used >= self.budget:
                raise ProviderError("Per-run request budget exhausted")
            time.sleep(max(0, 0.6 - (time.monotonic() - self.last_request)))
            self.used += 1
            self.last_request = time.monotonic()
            try:
                with self.opener.open(Request(url, headers={"Accept": "application/json", **headers}), timeout=15) as response:
                    raw = response.read(10_000_001)
                    if len(raw) > 10_000_000:
                        raise ProviderError("Provider response exceeds size limit")
                    payload = json.loads(raw)
                fetched = utcnow().isoformat()
                self.store.cache_put(url, payload, fetched)
                return payload, fetched, False
            except HTTPError as exc:
                exc.close()
                if exc.code == 429:
                    # Stop this provider request; do not evade Retry-After with a short retry.
                    raise ProviderError("HTTP 429: rate limited; retry on a later run") from None
                if exc.code in (500, 502, 503, 504) and attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                raise ProviderError(f"Provider HTTP {exc.code}; no response body exported") from None
            except (URLError, TimeoutError, OSError):
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                raise ProviderError("Provider network request failed after bounded retries") from None
            except (ValueError, UnicodeError):
                raise ProviderError("Provider returned invalid JSON") from None


class SEC:
    def __init__(self, client):
        self.client = client

    def filings(self, symbol, ttl):
        identity = os.getenv("SEC_USER_AGENT", "")
        if "@" not in identity or "\n" in identity or "\r" in identity:
            raise ProviderError("not_configured: set SEC_USER_AGENT to your application name and contact email locally")
        headers = {"User-Agent": identity}
        index, _, _ = self.client.get("https://www.sec.gov/files/company_tickers.json", headers, 86400)
        if not isinstance(index, dict):
            raise ProviderError("SEC ticker mapping has an invalid schema")
        matches = [v for v in index.values() if isinstance(v, dict) and v.get("ticker") == symbol]
        if len(matches) != 1:
            raise ProviderError("Symbol not uniquely mapped in SEC ticker index")
        cik = int(matches[0]["cik_str"])
        if not 0 < cik < 10**10:
            raise ProviderError("Invalid CIK mapping")
        return self.client.get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json", headers, ttl)


class Alpaca:
    def __init__(self, client):
        self.client = client

    def trades(self, symbols):
        key, secret = os.getenv("APCA_API_KEY_ID"), os.getenv("APCA_API_SECRET_KEY")
        if not key or not secret:
            raise ProviderError("not_configured: set APCA_API_KEY_ID and APCA_API_SECRET_KEY locally")
        url = "https://data.alpaca.markets/v2/stocks/trades/latest?" + urlencode({"symbols": ",".join(symbols), "feed": "iex"})
        return self.client.get(url, {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}, ttl=30)

    def headers(self):
        key, secret = os.getenv("APCA_API_KEY_ID"), os.getenv("APCA_API_SECRET_KEY")
        if not key or not secret:
            raise ProviderError("not_configured: set Alpaca credentials locally")
        return {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}

    def daily_bars(self, symbols, start, end):
        """Complete bounded pagination: never return a truncated ranking universe."""
        headers = self.headers()
        params = dict(symbols=",".join(symbols), timeframe="1Day", start=start, end=end,
                      feed="iex", adjustment="all", limit=10000, sort="asc")
        result, pages, seen = {s: [] for s in symbols}, [], set()
        for _ in range(10):
            payload, fetched, _ = self.client.get(
                "https://data.alpaca.markets/v2/stocks/bars?" + urlencode(params), headers, ttl=0)
            if not isinstance(payload, dict) or not isinstance(payload.get("bars"), dict):
                raise ProviderError("Historical bars response has an invalid schema")
            for symbol, bars in payload["bars"].items():
                if symbol not in result or not isinstance(bars, list):
                    raise ProviderError("Unexpected symbol or invalid bars in historical response")
                result[symbol].extend(bars)
                if len(result[symbol]) > 1000:
                    raise ProviderError("Historical bar count exceeds per-symbol bound")
            pages.append(fetched)
            token = payload.get("next_page_token")
            if token is None:
                return result, pages
            if not isinstance(token, str) or not token or token in seen or len(token) > 4096:
                raise ProviderError("Historical pagination token is invalid or repeated")
            seen.add(token)
            params["page_token"] = token
        raise ProviderError("Historical pagination limit reached; partial universe rejected")

    def snapshots(self, symbols):
        url = "https://data.alpaca.markets/v2/stocks/snapshots?" + urlencode(
            {"symbols": ",".join(symbols), "feed": "iex"})
        return self.client.get(url, self.headers(), ttl=0)
