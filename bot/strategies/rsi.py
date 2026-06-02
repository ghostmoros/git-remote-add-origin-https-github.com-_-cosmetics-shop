"""RSI mean reversion — buy oversold, sell overbought.

The simplest high-win-rate idea: when RSI < oversold the market is stretched
down and often bounces; when RSI > overbought it's stretched up. Small targets
turn the frequent bounces into a high win rate (mind the expectancy, though).
"""
from __future__ import annotations

import pandas as pd

from bot.core.strategy import Strategy
from bot.data.indicators import rsi


class RSIStrategy(Strategy):
    name = "rsi"
    style = "reversion"

    def __init__(self, period: int = 14, oversold: float = 30.0, overbought: float = 70.0, **extra):
        super().__init__(period=period, oversold=oversold, overbought=overbought, **extra)

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        p = self.params
        r = rsi(df["close"], p["period"])
        signal = pd.Series(0, index=df.index, dtype="int64")
        signal[r < p["oversold"]] = 1
        signal[r > p["overbought"]] = -1
        return signal
