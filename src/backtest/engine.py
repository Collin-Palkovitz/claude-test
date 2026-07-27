"""Backtest engine: replay target weights against historical closes.

Honesty rules baked in:
- Weights decided at the close of day T earn day T+1's return, never T's
  (no lookahead).
- Every change of weights pays `cost_bps` per side on the traded notional
  (spread + slippage; commissions are zero at Alpaca).
- Unallocated weight is cash earning zero — a deliberately harsh assumption.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

TRADING_DAYS_PER_YEAR = 252


@dataclass
class BacktestResult:
    name: str
    equity: pd.Series          # growth of $1, daily
    net_returns: pd.Series
    turnover: pd.Series        # fraction of portfolio traded per day

    @property
    def metrics(self) -> dict[str, float]:
        return compute_metrics(self.equity)


def run_backtest(
    closes: pd.DataFrame,
    target_weights: pd.DataFrame,
    cost_bps: float = 5.0,
    name: str = "strategy",
) -> BacktestResult:
    if target_weights.empty:
        raise ValueError(f"{name}: no weights to backtest")

    window = closes.loc[closes.index >= target_weights.index[0]]
    returns = window.pct_change().fillna(0.0)

    weights = (
        target_weights.reindex(window.index).ffill().fillna(0.0)
    )
    held = weights.shift(1).fillna(0.0)

    gross = (held * returns[weights.columns]).sum(axis=1)
    turnover = (weights - held).abs().sum(axis=1)
    net = gross - turnover * (cost_bps / 10_000.0)

    equity = (1.0 + net).cumprod()
    return BacktestResult(name=name, equity=equity, net_returns=net, turnover=turnover)


def buy_and_hold(
    closes: pd.DataFrame, symbol: str, start: pd.Timestamp, cost_bps: float = 5.0
) -> BacktestResult:
    """Benchmark: buy the symbol on `start`, never touch it again."""
    index = closes.index[closes.index >= start]
    weights = pd.DataFrame(1.0, index=index, columns=[symbol])
    return run_backtest(closes, weights, cost_bps=cost_bps, name=f"hold {symbol}")


def compute_metrics(equity: pd.Series) -> dict[str, float]:
    total = float(equity.iloc[-1] / equity.iloc[0] - 1.0)
    years = len(equity) / TRADING_DAYS_PER_YEAR
    cagr = float((equity.iloc[-1] / equity.iloc[0]) ** (1.0 / years) - 1.0) if years > 0 else 0.0
    drawdown = equity / equity.cummax() - 1.0
    daily = equity.pct_change().dropna()
    volatility = float(daily.std() * TRADING_DAYS_PER_YEAR**0.5)
    sharpe = float(daily.mean() / daily.std() * TRADING_DAYS_PER_YEAR**0.5) if daily.std() > 0 else 0.0
    return {
        "total_return": total,
        "cagr": cagr,
        "max_drawdown": float(drawdown.min()),
        "volatility": volatility,
        "sharpe": sharpe,
        "years": years,
    }


def window_return(equity: pd.Series, start: str, end: str) -> float | None:
    """Return over a calendar window, or None if the data doesn't cover it."""
    sliced = equity.loc[start:end]
    if len(sliced) < 2:
        return None
    return float(sliced.iloc[-1] / sliced.iloc[0] - 1.0)


# The stress windows that matter for a trend/momentum system.
BEAR_WINDOWS = {
    "2008 GFC": ("2007-10-01", "2009-03-09"),
    "2020 COVID crash": ("2020-02-19", "2020-04-30"),
    "2022 bear": ("2022-01-03", "2022-10-14"),
}
