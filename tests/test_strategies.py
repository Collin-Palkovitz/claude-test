from src.strategies.base import weights_to_signals
from src.strategies.momentum_rotation import MomentumRotation
from src.strategies.trend_filter import TrendFilter


def test_trend_filter_invested_in_uptrend_out_of_downtrend(closes):
    up = TrendFilter(symbol="UP", ma_days=200).target_weights(closes)
    down = TrendFilter(symbol="DOWN", ma_days=200).target_weights(closes)
    # After warm-up, a steady riser sits above its MA and a steady faller below.
    assert up["UP"].iloc[-50:].eq(1.0).all()
    assert down["DOWN"].iloc[-50:].eq(0.0).all()


def test_trend_filter_has_no_opinion_during_warmup(closes):
    weights = TrendFilter(symbol="UP", ma_days=200).target_weights(closes)
    assert len(weights) == len(closes) - 199


def test_momentum_rotation_picks_the_strongest(closes):
    strategy = MomentumRotation(
        universe=["UP", "DOWN", "FLAT"], cash_proxy="CASH", top_n=1
    )
    weights = strategy.target_weights(closes)
    latest = weights.iloc[-1]
    assert latest["UP"] == 1.0
    assert latest["DOWN"] == 0.0 and latest["FLAT"] == 0.0


def test_momentum_rotation_goes_to_cash_when_nothing_beats_the_proxy(closes):
    strategy = MomentumRotation(
        universe=["DOWN", "FLAT"], cash_proxy="CASH", top_n=2
    )
    weights = strategy.target_weights(closes)
    # Neither a faller nor a flat wobbler outruns even a T-bill proxy.
    assert weights.iloc[-1].eq(0.0).all()


def test_momentum_rotation_weights_are_valid_portfolio(closes):
    strategy = MomentumRotation(
        universe=["UP", "DOWN", "FLAT"], cash_proxy="CASH", top_n=2
    )
    weights = strategy.target_weights(closes)
    assert (weights.sum(axis=1) <= 1.0 + 1e-9).all()
    assert (weights >= 0).all().all()


def test_momentum_rotation_only_trades_at_month_ends(closes):
    strategy = MomentumRotation(
        universe=["UP", "DOWN", "FLAT"], cash_proxy="CASH", top_n=1
    )
    weights = strategy.target_weights(closes)
    changes = weights.diff().abs().sum(axis=1)
    change_dates = weights.index[changes > 1e-9]
    month_ends = weights.groupby(weights.index.to_period("M")).tail(1).index
    assert set(change_dates) <= set(month_ends)


def test_weights_to_signals_emits_enter_and_exit(closes):
    weights = TrendFilter(symbol="FLAT", ma_days=200).target_weights(closes)
    signals = weights_to_signals("trend_filter", weights)
    actions = {s.action for s in signals}
    # FLAT oscillates around its MA, so both entries and exits must appear.
    assert "ENTER" in actions and "EXIT" in actions
    for s in signals:
        assert s.symbol == "FLAT"
        assert s.weight_before != s.weight_after
