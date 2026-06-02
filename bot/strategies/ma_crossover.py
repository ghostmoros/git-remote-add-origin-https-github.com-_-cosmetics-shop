"""Moving-average crossover — a trend-following baseline for comparison.

Lower win rate than mean reversion but bigger winners (lets trends run). Kept
around so you can see the win-rate vs reward trade-off side by side.

Stance is persistent: long while the fast EMA is above the slow EMA, short while
below. The engine flips the position when the stance flips.
"""
from __future__ import annotations

import pandas as pd

from bot.core.strategy import Strategy
from bot.data.indicators import ema


class MACrossover(Strategy):
    name = "ma_crossover"

    def __init__(self, fast: int = 20, slow: int = 50, **extra):
        super().__init__(fast=fast, slow=slow, **extra)

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        p = self.params
        close = df["close"]
        fast = ema(close, p["fast"])
        slow = ema(close, p["slow"])

        signal = pd.Series(0, index=df.index, dtype="int64")
        signal[fast > slow] = 1
        signal[fast < slow] = -1
        # Don't trade until both EMAs are defined.
        signal[slow.isna()] = 0
        return signal
