"""SQLite storage for daily bars.

One table, one row per (symbol, date). Backfill is idempotent: re-running
upserts and never duplicates.
"""
from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path

import pandas as pd

_SCHEMA = """
CREATE TABLE IF NOT EXISTS bars (
    symbol TEXT NOT NULL,
    date   TEXT NOT NULL,
    open   REAL, high REAL, low REAL, close REAL, volume REAL,
    PRIMARY KEY (symbol, date)
);
"""


class BarStore:
    def __init__(self, db_path: str | Path) -> None:
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path)
        self._conn.execute(_SCHEMA)
        self._conn.commit()

    def upsert(self, symbol: str, bars: pd.DataFrame) -> int:
        rows = [
            (symbol, idx.strftime("%Y-%m-%d"), r.open, r.high, r.low, r.close, r.volume)
            for idx, r in bars.iterrows()
        ]
        self._conn.executemany(
            "INSERT OR REPLACE INTO bars VALUES (?, ?, ?, ?, ?, ?, ?)", rows
        )
        self._conn.commit()
        return len(rows)

    def last_date(self, symbol: str) -> date | None:
        row = self._conn.execute(
            "SELECT MAX(date) FROM bars WHERE symbol = ?", (symbol,)
        ).fetchone()
        return datetime.strptime(row[0], "%Y-%m-%d").date() if row and row[0] else None

    def load_closes(self, symbols: list[str]) -> pd.DataFrame:
        """Wide close-price frame: date index, one column per symbol."""
        placeholders = ",".join("?" for _ in symbols)
        df = pd.read_sql_query(
            f"SELECT symbol, date, close FROM bars WHERE symbol IN ({placeholders})",
            self._conn,
            params=symbols,
        )
        if df.empty:
            return pd.DataFrame(columns=symbols)
        df["date"] = pd.to_datetime(df["date"])
        wide = df.pivot(index="date", columns="symbol", values="close").sort_index()
        return wide.reindex(columns=[s for s in symbols if s in wide.columns])

    def close(self) -> None:
        self._conn.close()


def backfill(store: BarStore, source, symbols: list[str], start: date) -> dict[str, int]:
    """Fetch missing daily bars for each symbol. Returns rows written per symbol."""
    written: dict[str, int] = {}
    for symbol in symbols:
        fetch_from = store.last_date(symbol) or start
        bars = source.fetch_daily(symbol, fetch_from)
        written[symbol] = store.upsert(symbol, bars)
    return written
