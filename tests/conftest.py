"""Deterministic synthetic price data — no network, no randomness."""
from __future__ import annotations

import math

import pandas as pd
import pytest


def _series(dates: pd.DatetimeIndex, start: float, daily_growth: float, wobble: float = 0.0):
    prices = []
    value = start
    for i in range(len(dates)):
        value *= 1.0 + daily_growth
        prices.append(value * (1.0 + wobble * math.sin(i / 9.0)))
    return pd.Series(prices, index=dates)


@pytest.fixture
def dates() -> pd.DatetimeIndex:
    # ~3 years of business days, fixed range so tests are reproducible.
    return pd.bdate_range("2020-01-01", periods=780)


@pytest.fixture
def closes(dates) -> pd.DataFrame:
    """Four synthetic ETFs with unmistakable personalities.

    UP    grinds higher (~+0.08%/day), DOWN grinds lower, FLAT oscillates
    around its start, CASH creeps up a hair like a T-bill fund.
    """
    return pd.DataFrame(
        {
            "UP": _series(dates, 100, 0.0008, wobble=0.01),
            "DOWN": _series(dates, 100, -0.0008, wobble=0.01),
            "FLAT": _series(dates, 100, 0.0, wobble=0.02),
            "CASH": _series(dates, 100, 0.00008),
        }
    )
