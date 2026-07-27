"""Indicator math shared by strategies. All functions are pure pandas."""
from __future__ import annotations

import pandas as pd

TRADING_DAYS_PER_MONTH = 21


def sma(closes: pd.Series | pd.DataFrame, days: int):
    """Simple moving average; NaN until `days` observations exist."""
    return closes.rolling(days).mean()


def trailing_return(closes: pd.Series | pd.DataFrame, months: int):
    """Total return over the trailing N months (approximated in trading days)."""
    return closes.pct_change(months * TRADING_DAYS_PER_MONTH)


def blended_momentum(closes: pd.DataFrame, lookback_months: list[int]) -> pd.DataFrame:
    """Mean of trailing returns across the given lookbacks, per symbol.

    NaN addition propagates, so a symbol has no score until every lookback
    has full history — it can't be ranked on partial data.
    """
    total = trailing_return(closes, lookback_months[0])
    for months in lookback_months[1:]:
        total = total + trailing_return(closes, months)
    return total / len(lookback_months)
