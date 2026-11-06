import numpy as np
import pandas as pd
import pytest

from glm_trading.indicators import indicators, wilder_rsi


def test_sma_hand_calculation_and_prefix_invariance():
    prices = pd.DataFrame({"close": np.arange(1., 71.)})
    values = indicators(prices)
    assert values.sma20.iloc[19] == 10.5
    assert values.sma50.iloc[49] == 25.5
    assert values.sma50.iloc[:49].isna().all()
    pd.testing.assert_frame_equal(values.iloc[:60], indicators(prices.iloc[:60]))


def test_wilder_arithmetic_seed_and_recurrence():
    # Deltas +1,+2,-1 seed average gain=1, loss=1/3: RSI=75.
    # Next delta -2: gain=2/3, loss=8/9: RSI=300/7.
    result = wilder_rsi(pd.Series([10., 11., 13., 12., 10.]), 3)
    assert result.iloc[:3].isna().all()
    assert result.iloc[3] == pytest.approx(75)
    assert result.iloc[4] == pytest.approx(300 / 7)


@pytest.mark.parametrize("values,expected", [(list(range(20)),100), (list(range(20,0,-1)),0), ([5]*20,50)])
def test_rsi_edge_cases(values, expected):
    assert wilder_rsi(pd.Series(values)).iloc[-1] == expected
