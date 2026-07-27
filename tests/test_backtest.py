import math

import pandas as pd
import pytest

from src.backtest.engine import (
    buy_and_hold,
    compute_metrics,
    run_backtest,
    window_return,
)
from src.strategies.trend_filter import TrendFilter


def test_buy_and_hold_tracks_price_exactly_with_zero_cost(closes):
    result = buy_and_hold(closes, "UP", closes.index[0], cost_bps=0.0)
    expected = closes["UP"].iloc[-1] / closes["UP"].iloc[0]
    assert math.isclose(result.equity.iloc[-1], expected, rel_tol=1e-9)


def test_costs_strictly_reduce_returns(closes):
    weights = TrendFilter(symbol="FLAT", ma_days=200).target_weights(closes)
    free = run_backtest(closes, weights, cost_bps=0.0)
    costly = run_backtest(closes, weights, cost_bps=20.0)
    # FLAT crosses its MA repeatedly, so trades happen and costs must bite.
    assert costly.turnover.sum() > 0
    assert costly.equity.iloc[-1] < free.equity.iloc[-1]


def test_no_lookahead_first_day_earns_nothing():
    # Price doubles on day 2; a weight set at day 1's close must NOT capture
    # day 1's move, only day 2's.
    dates = pd.bdate_range("2024-01-01", periods=3)
    closes = pd.DataFrame({"X": [100.0, 100.0, 200.0]}, index=dates)
    weights = pd.DataFrame({"X": [1.0, 1.0, 1.0]}, index=dates)
    result = run_backtest(closes, weights, cost_bps=0.0)
    assert math.isclose(result.equity.iloc[0], 1.0)
    assert math.isclose(result.equity.iloc[-1], 2.0, rel_tol=1e-9)


def test_trend_filter_cuts_crash_drawdown():
    # Rise for 300 days, crash 45% over 60 days, recover slowly.
    dates = pd.bdate_range("2018-01-01", periods=700)
    prices = []
    value = 100.0
    for i in range(len(dates)):
        if i < 300:
            value *= 1.0015
        elif i < 360:
            value *= 0.99
        else:
            value *= 1.001
        prices.append(value)
    closes = pd.DataFrame({"IDX": prices}, index=dates)

    weights = TrendFilter(symbol="IDX", ma_days=200).target_weights(closes)
    strategy = run_backtest(closes, weights, cost_bps=5.0)
    bench = buy_and_hold(closes, "IDX", weights.index[0], cost_bps=5.0)

    # The whole justification for the strategy: materially smaller drawdown.
    assert strategy.metrics["max_drawdown"] > bench.metrics["max_drawdown"] + 0.15


def test_max_drawdown_hand_computed():
    equity = pd.Series([1.0, 1.5, 0.75, 0.9, 1.8])
    metrics = compute_metrics(equity)
    assert math.isclose(metrics["max_drawdown"], 0.75 / 1.5 - 1.0)
    assert math.isclose(metrics["total_return"], 0.8)


def test_window_return_none_outside_data(closes):
    result = buy_and_hold(closes, "UP", closes.index[0], cost_bps=0.0)
    assert window_return(result.equity, "1999-01-01", "1999-12-31") is None
    covered = window_return(result.equity, "2020-06-01", "2021-06-01")
    assert covered is not None


def test_empty_weights_raise(closes):
    with pytest.raises(ValueError):
        run_backtest(closes, pd.DataFrame(), cost_bps=5.0)
