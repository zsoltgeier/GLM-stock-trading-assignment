"""Past-only SMA and Wilder RSI, with explicit arithmetic-mean RSI seeding."""

import numpy as np
import pandas as pd


def wilder_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    if period < 1:
        raise ValueError("RSI period must be positive")
    result = pd.Series(np.nan, index=close.index, dtype=float)
    if len(close) <= period:
        return result
    delta = close.diff()
    gains, losses = delta.clip(lower=0), -delta.clip(upper=0)
    gain, loss = gains.iloc[1:period + 1].mean(), losses.iloc[1:period + 1].mean()
    for i in range(period, len(close)):
        if i > period:
            gain = (gain * (period - 1) + gains.iloc[i]) / period
            loss = (loss * (period - 1) + losses.iloc[i]) / period
        result.iloc[i] = 50 if gain == loss == 0 else (100 if loss == 0 else 100 - 100 / (1 + gain / loss))
    return result


def indicators(prices):
    close = prices.close
    return pd.DataFrame({
        "sma20": close.rolling(20, min_periods=20).mean(),
        "sma50": close.rolling(50, min_periods=50).mean(),
        "rsi14": wilder_rsi(close),
    })
