"""Trend filter: hold the index ETF above its long moving average, else cash.

The most-studied systematic rule there is. Its job is not to beat the market
in good times; it's to sidestep the deep bear markets.
"""
from __future__ import annotations

import pandas as pd

from ..indicators import sma
from .base import Strategy


class TrendFilter(Strategy):
    name = "trend_filter"

    def __init__(self, symbol: str = "SPY", ma_days: int = 200) -> None:
        self.symbol = symbol
        self.ma_days = ma_days

    def target_weights(self, closes: pd.DataFrame) -> pd.DataFrame:
        if self.symbol not in closes.columns:
            raise ValueError(f"{self.symbol} not present in price data")
        price = closes[self.symbol].dropna()
        average = sma(price, self.ma_days)
        invested = (price > average).astype(float)
        weights = invested.where(average.notna(), 0.0).to_frame(self.symbol)
        # Drop the warm-up period entirely: no opinion until the MA exists.
        return weights[average.notna()]
