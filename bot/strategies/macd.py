"""MACD trend following — long while the MACD line is above its signal line.

Classic momentum/trend filter. Persistent stance: the engine flips the position
when MACD crosses its signal line.
"""
from __future__ import annotations

import pandas as pd

from bot.core.strategy import Strategy
from bot.data.indicators import macd


class MACDStrategy(Strategy):
    name = "macd"
    style = "trend"

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9, **extra):
        super().__init__(fast=fast, slow=slow, signal=signal, **extra)

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        p = self.params
        macd_line, signal_line, _hist = macd(df["close"], p["fast"], p["slow"], p["signal"])
        signal = pd.Series(0, index=df.index, dtype="int64")
        signal[macd_line > signal_line] = 1
        signal[macd_line < signal_line] = -1
        signal[signal_line.isna()] = 0
        return signal
