import pandas as pd

from src.indicators import blended_momentum, sma, trailing_return


def test_sma_matches_hand_computation():
    s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    result = sma(s, 3)
    assert result.iloc[:2].isna().all()
    assert result.iloc[2] == 2.0
    assert result.iloc[4] == 4.0


def test_trailing_return_is_total_return_over_window():
    s = pd.Series(range(1, 100), dtype=float)
    r = trailing_return(s, 1)  # 21 trading days
    assert abs(r.iloc[21] - (22.0 / 1.0 - 1)) < 1e-12


def test_blended_momentum_nan_until_longest_lookback(closes):
    scores = blended_momentum(closes, [3, 6, 12])
    longest = 12 * 21
    assert scores["UP"].iloc[:longest].isna().all()
    assert scores["UP"].iloc[longest:].notna().all()


def test_blended_momentum_ranks_up_over_down(closes):
    scores = blended_momentum(closes, [3, 6, 12]).dropna()
    assert (scores["UP"] > scores["DOWN"]).all()
    assert (scores["UP"] > scores["FLAT"]).all()
