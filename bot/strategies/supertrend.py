"""SuperTrend following — trade in the direction of the SuperTrend line.

Very popular in forex/MT5. The ATR-based trailing line flips between bull and
bear regimes; we simply ride whichever side it's on.
"""
from __future__ import annotations

import pandas as pd

from bot.core.strategy import Strategy
from bot.data.indicators import supertrend


class SuperTrendStrategy(Strategy):
    name = "supertrend"
    style = "trend"

    def __init__(self, period: int = 10, multiplier: float = 3.0, **extra):
        super().__init__(period=period, multiplier=multiplier, **extra)

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        p = self.params
        direction, _line = supertrend(df["high"], df["low"], df["close"], p["period"], p["multiplier"])
        return direction.astype("int64")
