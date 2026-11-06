"""Market-data checks and exchange calendar used by ingestion and evaluation."""

import exchange_calendars as xcals
import numpy as np
import pandas as pd


def calendar(config):
    return xcals.get_calendar(config.calendar, start=config.warmup_start, end=config.data_end)


def validate_prices(prices, ticker, expected=None):
    required = {"ticker", "open", "high", "low", "close", "volume", "split"}
    if not required.issubset(prices.columns):
        raise ValueError(f"Missing columns: {sorted(required - set(prices.columns))}")
    if prices.empty or prices.index.has_duplicates or not prices.index.is_monotonic_increasing:
        raise ValueError("Prices must be nonempty, ordered and have unique dates")
    if set(prices.ticker) != {ticker}:
        raise ValueError("Price ticker mismatch")
    numeric = prices[["open", "high", "low", "close", "volume", "split"]]
    if not np.isfinite(numeric.to_numpy(dtype=float)).all():
        raise ValueError("Missing or nonfinite market data")
    if (prices[["open", "high", "low", "close"]] <= 0).any().any() or (prices.volume < 0).any():
        raise ValueError("Nonpositive price or negative volume")
    if ((prices.low > prices[["open", "close"]].min(axis=1)) |
        (prices.high < prices[["open", "close"]].max(axis=1)) |
        (prices.low > prices.high)).any():
        raise ValueError("Inconsistent OHLC")
    if (prices.split != 0).any():
        raise ValueError("Stock splits require a reviewed adjustment policy; this experiment rejects them")
    if expected is not None and not prices.index.equals(pd.DatetimeIndex(expected)):
        raise ValueError("Missing or unexpected trading sessions")


def read_prices(path):
    prices = pd.read_csv(path, parse_dates=["date"]).set_index("date")
    if prices.index.tz is not None:
        raise ValueError("Daily date labels must be timezone-free session dates")
    return prices
