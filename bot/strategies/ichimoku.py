"""Ichimoku Cloud trend strategy.

Go long when price is above the cloud (both leading spans) and the conversion
line is above the base line; go short on the mirror condition. A very popular
forex setup that bakes trend, momentum and support/resistance into one view.
"""
from __future__ import annotations

import pandas as pd

from bot.core.strategy import Strategy
from bot.data.indicators import ichimoku


class IchimokuStrategy(Strategy):
    name = "ichimoku"
    style = "trend"

    def __init__(self, tenkan: int = 9, kijun: int = 26, senkou_b: int = 52, shift: int = 26, **extra):
        super().__init__(tenkan=tenkan, kijun=kijun, senkou_b=senkou_b, shift=shift, **extra)

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        p = self.params
        conversion, base, span_a, span_b = ichimoku(
            df["high"], df["low"], df["close"], p["tenkan"], p["kijun"], p["senkou_b"], p["shift"]
        )
        cloud_top = pd.concat([span_a, span_b], axis=1).max(axis=1)
        cloud_bottom = pd.concat([span_a, span_b], axis=1).min(axis=1)

        long_cond = (df["close"] > cloud_top) & (conversion > base)
        short_cond = (df["close"] < cloud_bottom) & (conversion < base)

        signal = pd.Series(0, index=df.index, dtype="int64")
        signal[long_cond] = 1
        signal[short_cond] = -1
        return signal
