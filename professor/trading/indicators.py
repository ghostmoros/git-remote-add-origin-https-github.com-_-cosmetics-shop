"""Технические индикаторы на чистом Python (без numpy/pandas)."""
from __future__ import annotations


def sma(values: list[float], period: int) -> list[float | None]:
    """Простая скользящая средняя. Первые (period-1) значений — None."""
    out: list[float | None] = []
    s = 0.0
    for i, v in enumerate(values):
        s += v
        if i >= period:
            s -= values[i - period]
        out.append(s / period if i >= period - 1 else None)
    return out


def ema(values: list[float], period: int) -> list[float | None]:
    """Экспоненциальная скользящая средняя (seed по SMA)."""
    out: list[float | None] = []
    k = 2 / (period + 1)
    prev: float | None = None
    for i, v in enumerate(values):
        if i < period - 1:
            out.append(None)
            continue
        if prev is None:
            prev = sum(values[i - period + 1:i + 1]) / period
        else:
            prev = v * k + prev * (1 - k)
        out.append(prev)
    return out


def rsi(values: list[float], period: int = 14) -> list[float | None]:
    """Индекс относительной силы (RSI), сглаживание по Уайлдеру."""
    out: list[float | None] = [None] * len(values)
    if len(values) <= period:
        return out
    gains = losses = 0.0
    for i in range(1, period + 1):
        d = values[i] - values[i - 1]
        gains += max(d, 0.0)
        losses += max(-d, 0.0)
    avg_gain = gains / period
    avg_loss = losses / period
    rs = avg_gain / avg_loss if avg_loss > 0 else float("inf")
    out[period] = 100 - 100 / (1 + rs)
    for i in range(period + 1, len(values)):
        d = values[i] - values[i - 1]
        avg_gain = (avg_gain * (period - 1) + max(d, 0.0)) / period
        avg_loss = (avg_loss * (period - 1) + max(-d, 0.0)) / period
        rs = avg_gain / avg_loss if avg_loss > 0 else float("inf")
        out[i] = 100 - 100 / (1 + rs)
    return out
