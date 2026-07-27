"""Momentum rotation: monthly, hold the strongest ETFs in the universe.

On the last trading day of each month, rank the universe by blended trailing
returns (default 3/6/12 months) and target an equal weight in the top N.
Absolute-momentum safety valve: a symbol is only eligible if its score beats
the cash proxy's score (or zero when no proxy data exists) — in a broad bear
market the strategy holds cash rather than "the least-bad loser".

Weights persist unchanged between rebalance dates.
"""
from __future__ import annotations

import pandas as pd

from ..indicators import blended_momentum
from .base import Strategy


class MomentumRotation(Strategy):
    name = "momentum_rotation"

    def __init__(
        self,
        universe: list[str],
        cash_proxy: str = "",
        lookback_months: list[int] | None = None,
        top_n: int = 2,
        min_history_days: int = 260,
    ) -> None:
        self.universe = universe
        self.cash_proxy = cash_proxy
        self.lookback_months = lookback_months or [3, 6, 12]
        self.top_n = top_n
        self.min_history_days = min_history_days

    def target_weights(self, closes: pd.DataFrame) -> pd.DataFrame:
        held = [s for s in self.universe if s in closes.columns]
        if not held:
            raise ValueError("none of the universe symbols are present in price data")

        scores = blended_momentum(closes[held], self.lookback_months)
        hurdle = self._hurdle(closes)

        month_ends = closes.groupby(closes.index.to_period("M")).tail(1).index
        weights = pd.DataFrame(0.0, index=closes.index, columns=held)

        current = pd.Series(0.0, index=held)
        first_rebalance = None
        for ts in closes.index:
            if ts in month_ends and len(closes.loc[:ts]) >= self.min_history_days:
                row = scores.loc[ts].dropna()
                eligible = row[row > hurdle.get(ts, 0.0)]
                picks = eligible.nlargest(self.top_n).index
                current = pd.Series(0.0, index=held)
                if len(picks):
                    current[picks] = 1.0 / len(picks)
                first_rebalance = first_rebalance or ts
            if first_rebalance is not None:
                weights.loc[ts] = current

        # No opinion before the first rebalance with enough history.
        if first_rebalance is None:
            return weights.iloc[0:0]
        return weights.loc[weights.index >= first_rebalance]

    def _hurdle(self, closes: pd.DataFrame) -> pd.Series:
        """Per-date score the cash proxy sets; 0.0 where unavailable."""
        if self.cash_proxy and self.cash_proxy in closes.columns:
            proxy = blended_momentum(
                closes[[self.cash_proxy]], self.lookback_months
            )[self.cash_proxy]
            return proxy.fillna(0.0)
        return pd.Series(0.0, index=closes.index)
