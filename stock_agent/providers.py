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
    def __init__(self, store, budget=30):
        self.store, self.budget, self.used = store, budget, 0
        self.last_request = 0.0
        self.opener = build_opener(NoRedirect())

    def get(self, url, headers, ttl=0):
        if urlparse(url).scheme != "https" or urlparse(url).hostname not in ("www.sec.gov", "data.sec.gov", "data.alpaca.markets"):
            raise ProviderError("Provider host is not allowed")
        cached = self.store.cache_get(url, ttl, utcnow())
        if cached:
            return cached[0], cached[1], True
        for attempt in range(3):
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
