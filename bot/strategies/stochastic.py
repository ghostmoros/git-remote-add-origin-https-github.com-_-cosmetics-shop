"""Stochastic oscillator mean reversion.

Go long when %K is in oversold territory, short when overbought. Often paired
with RSI for confirmation; kept standalone here so its behaviour is easy to read
in the comparison.
"""
from __future__ import annotations

import pandas as pd

from bot.core.strategy import Strategy
from bot.data.indicators import stochastic


class StochasticStrategy(Strategy):
    name = "stochastic"
    style = "reversion"

    def __init__(self, k_period: int = 14, d_period: int = 3, oversold: float = 20.0, overbought: float = 80.0, **extra):
        super().__init__(k_period=k_period, d_period=d_period, oversold=oversold, overbought=overbought, **extra)

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        p = self.params
        percent_k, _percent_d = stochastic(df["high"], df["low"], df["close"], p["k_period"], p["d_period"])
        signal = pd.Series(0, index=df.index, dtype="int64")
        signal[percent_k < p["oversold"]] = 1
        signal[percent_k > p["overbought"]] = -1
        return signal
