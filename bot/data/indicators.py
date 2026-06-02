"""Technical indicators implemented on top of pandas.

All functions take/return pandas Series so they compose cleanly and keep the
original DatetimeIndex. Wilder's smoothing is used for RSI/ATR to match what
most charting platforms (TradingView, MT5) show.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def sma(series: pd.Series, period: int) -> pd.Series:
    """Simple moving average."""
    return series.rolling(window=period, min_periods=period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential moving average."""
    return series.ewm(span=period, adjust=False).mean()


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index (Wilder's smoothing). Range 0..100."""
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average True Range (Wilder's smoothing). Measures volatility in price units."""
    prev_close = close.shift(1)
    true_range = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()


def bollinger(close: pd.Series, period: int = 20, num_std: float = 2.0):
    """Bollinger Bands. Returns (middle, upper, lower)."""
    middle = close.rolling(window=period, min_periods=period).mean()
    std = close.rolling(window=period, min_periods=period).std(ddof=0)
    upper = middle + num_std * std
    lower = middle - num_std * std
    return middle, upper, lower


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """MACD. Returns (macd_line, signal_line, histogram)."""
    macd_line = ema(close, fast) - ema(close, slow)
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def stochastic(high: pd.Series, low: pd.Series, close: pd.Series, k_period: int = 14, d_period: int = 3):
    """Stochastic oscillator. Returns (%K, %D), both in 0..100."""
    lowest = low.rolling(k_period, min_periods=k_period).min()
    highest = high.rolling(k_period, min_periods=k_period).max()
    percent_k = 100.0 * (close - lowest) / (highest - lowest)
    percent_d = percent_k.rolling(d_period, min_periods=d_period).mean()
    return percent_k, percent_d


def donchian(high: pd.Series, low: pd.Series, period: int = 20):
    """Donchian channel. Returns (upper, lower) = rolling max high / min low."""
    upper = high.rolling(period, min_periods=period).max()
    lower = low.rolling(period, min_periods=period).min()
    return upper, lower


def supertrend(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 10, multiplier: float = 3.0):
    """SuperTrend. Returns (direction, line).

    direction is +1 in an uptrend, -1 in a downtrend, 0 during warmup. The
    computation is inherently iterative because each band depends on the
    previous bar's band, so we loop in numpy.
    """
    atr_values = atr(high, low, close, period)
    hl2 = (high + low) / 2.0
    upper = (hl2 + multiplier * atr_values).to_numpy(float)
    lower = (hl2 - multiplier * atr_values).to_numpy(float)
    c = close.to_numpy(float)
    av = atr_values.to_numpy(float)
    n = len(c)

    final_upper = np.full(n, np.nan)
    final_lower = np.full(n, np.nan)
    direction = np.zeros(n)
    line = np.full(n, np.nan)

    if np.isnan(av).all():
        return pd.Series(direction, index=close.index), pd.Series(line, index=close.index)

    start = int(np.argmax(~np.isnan(av)))  # first bar with a valid ATR
    final_upper[start] = upper[start]
    final_lower[start] = lower[start]
    direction[start] = 1
    line[start] = final_lower[start]

    for i in range(start + 1, n):
        final_upper[i] = upper[i] if (upper[i] < final_upper[i - 1] or c[i - 1] > final_upper[i - 1]) else final_upper[i - 1]
        final_lower[i] = lower[i] if (lower[i] > final_lower[i - 1] or c[i - 1] < final_lower[i - 1]) else final_lower[i - 1]
        if c[i] > final_upper[i - 1]:
            direction[i] = 1
        elif c[i] < final_lower[i - 1]:
            direction[i] = -1
        else:
            direction[i] = direction[i - 1]
        line[i] = final_lower[i] if direction[i] == 1 else final_upper[i]

    return pd.Series(direction, index=close.index), pd.Series(line, index=close.index)


def ichimoku(high: pd.Series, low: pd.Series, close: pd.Series,
             tenkan: int = 9, kijun: int = 26, senkou_b: int = 52, shift: int = 26):
    """Ichimoku components. Returns (conversion, base, span_a, span_b).

    Leading spans are shifted forward by `shift` bars (the "cloud"), so at any
    bar they reflect values already known — no look-ahead. Chikou (lagging span)
    is intentionally omitted because it would peek into the future.
    """
    conversion = (high.rolling(tenkan).max() + low.rolling(tenkan).min()) / 2.0
    base = (high.rolling(kijun).max() + low.rolling(kijun).min()) / 2.0
    span_a = ((conversion + base) / 2.0).shift(shift)
    span_b = ((high.rolling(senkou_b).max() + low.rolling(senkou_b).min()) / 2.0).shift(shift)
    return conversion, base, span_a, span_b
