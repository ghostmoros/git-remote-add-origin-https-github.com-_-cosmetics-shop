"""Donchian channel breakout — the classic "Turtle" trend entry.

Go long when price closes above the highest high of the prior N bars, short when
it closes below the lowest low. We use the channel shifted by one bar so the
breakout level excludes the current candle (no look-ahead).
"""
from __future__ import annotations

import pandas as pd

from bot.core.strategy import Strategy
from bot.data.indicators import donchian


class DonchianBreakout(Strategy):
    name = "donchian"
    style = "breakout"

    def __init__(self, period: int = 20, **extra):
        super().__init__(period=period, **extra)

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        p = self.params
        upper, lower = donchian(df["high"], df["low"], p["period"])
        prior_upper = upper.shift(1)
        prior_lower = lower.shift(1)
        signal = pd.Series(0, index=df.index, dtype="int64")
        signal[df["close"] > prior_upper] = 1
        signal[df["close"] < prior_lower] = -1
        return signal
