"""Market data sources.

Every source returns the same shape: a DataFrame indexed by date with
columns [open, high, low, close, volume], oldest row first.
"""
from __future__ import annotations

import io
import os
import urllib.request
from datetime import date

import pandas as pd

BAR_COLUMNS = ["open", "high", "low", "close", "volume"]


class DataSourceError(RuntimeError):
    pass


def _normalize(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    df = df.rename(columns={c: c.lower() for c in df.columns})
    missing = [c for c in ["date", "open", "high", "low", "close"] if c not in df.columns]
    if missing:
        raise DataSourceError(f"{symbol}: response missing columns {missing}")
    if "volume" not in df.columns:
        df["volume"] = 0
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    return df[BAR_COLUMNS].astype(float)


class StooqSource:
    """Free daily bars from stooq.com, no API key. US tickers get a .us suffix."""

    URL = "https://stooq.com/q/d/l/?s={ticker}&i=d&d1={d1}&d2={d2}"

    def fetch_daily(self, symbol: str, start: date, end: date | None = None) -> pd.DataFrame:
        end = end or date.today()
        url = self.URL.format(
            ticker=f"{symbol.lower()}.us",
            d1=start.strftime("%Y%m%d"),
            d2=end.strftime("%Y%m%d"),
        )
        req = urllib.request.Request(url, headers={"User-Agent": "etf-trader/0.1"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                text = resp.read().decode("utf-8", errors="replace")
        except OSError as exc:
            raise DataSourceError(f"{symbol}: download failed: {exc}") from exc
        if not text.strip() or text.strip().lower().startswith("no data"):
            raise DataSourceError(f"{symbol}: stooq returned no data")
        df = pd.read_csv(io.StringIO(text))
        return _normalize(df, symbol)


class AlpacaSource:
    """Daily bars via Alpaca's market data API. Requires alpaca-py and env keys."""

    def __init__(self) -> None:
        key = os.environ.get("ALPACA_API_KEY")
        secret = os.environ.get("ALPACA_API_SECRET")
        if not key or not secret:
            raise DataSourceError(
                "AlpacaSource needs ALPACA_API_KEY and ALPACA_API_SECRET env vars"
            )
        try:
            from alpaca.data.historical import StockHistoricalDataClient
        except ImportError as exc:
            raise DataSourceError("pip install alpaca-py to use the alpaca source") from exc
        self._client = StockHistoricalDataClient(key, secret)

    def fetch_daily(self, symbol: str, start: date, end: date | None = None) -> pd.DataFrame:
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame

        request = StockBarsRequest(
            symbol_or_symbols=symbol, timeframe=TimeFrame.Day, start=start, end=end
        )
        bars = self._client.get_stock_bars(request).df
        if bars.empty:
            raise DataSourceError(f"{symbol}: alpaca returned no data")
        df = bars.reset_index()[["timestamp", "open", "high", "low", "close", "volume"]]
        df = df.rename(columns={"timestamp": "date"})
        df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None).dt.normalize()
        return _normalize(df, symbol)


def make_source(name: str):
    if name == "stooq":
        return StooqSource()
    if name == "alpaca":
        return AlpacaSource()
    raise DataSourceError(f"unknown data source: {name!r}")
