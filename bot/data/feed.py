"""Data feed: load OHLC candles from CSV or generate synthetic data.

The rest of the bot only cares about a DataFrame with a DatetimeIndex and the
columns: open, high, low, close (volume optional). Where the data comes from is
an implementation detail, so swapping in a real broker feed later is trivial.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def load_data(cfg: dict) -> pd.DataFrame:
    """Build a candle DataFrame from a config dict (the `data:` section)."""
    source = cfg.get("source", "synthetic")
    if source == "csv":
        return load_csv(cfg["csv_path"])
    if source == "synthetic":
        return synthetic(
            bars=int(cfg.get("synthetic_bars", 5000)),
            seed=int(cfg.get("seed", 42)),
            start_price=float(cfg.get("start_price", 1.10)),
        )
    raise ValueError(f"Unknown data source: {source!r}")


def load_csv(path: str) -> pd.DataFrame:
    """Load candles from a CSV with a time column + open/high/low/close."""
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    time_col = next((c for c in ("time", "date", "datetime", "timestamp") if c in df.columns), None)
    if time_col is None:
        raise ValueError("CSV must contain a time/date/datetime/timestamp column")
    df[time_col] = pd.to_datetime(df[time_col])
    df = df.set_index(time_col).sort_index()
    required = {"open", "high", "low", "close"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing required columns: {sorted(missing)}")
    return df[["open", "high", "low", "close"] + (["volume"] if "volume" in df.columns else [])]


def synthetic(bars: int = 5000, seed: int = 42, start_price: float = 1.10) -> pd.DataFrame:
    """Generate realistic-ish OHLC data: a slow trend + a mean-reverting wobble.

    Price = trend + deviation, where:
      - trend     is a gentle random walk (so up/down regimes appear), and
      - deviation is an AR(1) / Ornstein-Uhlenbeck process that keeps pulling
        back toward the trend (so short-term dips and rips revert to the mean).

    This is NOT a market simulator — it just gives the backtester and the
    mean-reversion logic realistic structure to chew on. Confirm any real edge
    on real historical data before trusting it.
    """
    rng = np.random.default_rng(seed)

    # 1) Slow trend: a gentle random walk in log-price.
    trend = np.cumsum(rng.normal(0.0, 0.00025, bars))

    # 2) Mean-reverting deviation around the trend (AR(1) with phi < 1).
    phi = 0.94
    shocks = rng.normal(0.0, 0.0016, bars)
    deviation = np.empty(bars)
    deviation[0] = shocks[0]
    for i in range(1, bars):
        deviation[i] = phi * deviation[i - 1] + shocks[i]

    log_price = trend + deviation
    close = start_price * np.exp(log_price)
    open_ = np.concatenate([[start_price], close[:-1]])

    # Intrabar wick size scales with price.
    wick = close * 0.0006
    high = np.maximum(open_, close) + rng.uniform(0.0, 1.0, bars) * wick
    low = np.minimum(open_, close) - rng.uniform(0.0, 1.0, bars) * wick

    index = pd.date_range("2020-01-01", periods=bars, freq="h", name="time")
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close},
        index=index,
    )
