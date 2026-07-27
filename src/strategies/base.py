"""Strategy interface.

A strategy's whole job is one thing: given a wide close-price frame
(date index, symbol columns), return a target-weights frame of the same
index where each row sums to <= 1.0 (the remainder is cash).

Everything downstream — the Phase 1 signal log, the Phase 2 backtester,
the Phase 3+ brokers — consumes weights. Strategies never see orders,
accounts, or money.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date

import pandas as pd

WEIGHT_EPSILON = 1e-9


@dataclass(frozen=True)
class Signal:
    """A human-readable record of a target-weight change."""

    strategy: str
    date: date
    symbol: str
    action: str  # ENTER | EXIT | REBALANCE
    weight_before: float
    weight_after: float


class Strategy(ABC):
    name: str = "base"

    @abstractmethod
    def target_weights(self, closes: pd.DataFrame) -> pd.DataFrame:
        """Target portfolio weights for every date with enough history."""


def weights_to_signals(name: str, weights: pd.DataFrame) -> list[Signal]:
    """Diff a weights frame into discrete ENTER/EXIT/REBALANCE events."""
    signals: list[Signal] = []
    previous = weights.shift(1).fillna(0.0)
    changed = (weights - previous).abs() > WEIGHT_EPSILON
    for ts in weights.index[changed.any(axis=1)]:
        for symbol in weights.columns[changed.loc[ts]]:
            before = float(previous.at[ts, symbol])
            after = float(weights.at[ts, symbol])
            if before <= WEIGHT_EPSILON:
                action = "ENTER"
            elif after <= WEIGHT_EPSILON:
                action = "EXIT"
            else:
                action = "REBALANCE"
            signals.append(
                Signal(name, ts.date(), symbol, action, round(before, 4), round(after, 4))
            )
    return signals
