"""London Breakout — a forex-specific session strategy.

Forex moves in sessions (Sydney/Tokyo/London/New York). This strategy measures
the range built during the quiet pre-London window (by default the Asian hours)
and trades the breakout of that range once London opens, when liquidity and
volatility surge.

  - range window  [range_start, range_end)  -> record the high/low
  - trading window [range_end, session_end)  -> long above range high,
                                                short below range low

Requires intraday data with real timestamps (e.g. H1). On daily bars there's no
intraday session, so it produces no signals.
"""
from __future__ import annotations

import pandas as pd

from bot.core.strategy import Strategy


class LondonBreakout(Strategy):
    name = "london_breakout"
    style = "breakout"

    def __init__(self, range_start: int = 0, range_end: int = 7, session_end: int = 16, **extra):
        super().__init__(range_start=range_start, range_end=range_end, session_end=session_end, **extra)

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        p = self.params
        idx = df.index
        hour = idx.hour
        day = idx.normalize()  # group bars by calendar day

        in_range_window = pd.Series((hour >= p["range_start"]) & (hour < p["range_end"]), index=idx)
        range_high = df["high"].where(in_range_window).groupby(day).transform("max")
        range_low = df["low"].where(in_range_window).groupby(day).transform("min")

        in_session = pd.Series((hour >= p["range_end"]) & (hour < p["session_end"]), index=idx)

        signal = pd.Series(0, index=idx, dtype="int64")
        signal[in_session & (df["close"] > range_high)] = 1
        signal[in_session & (df["close"] < range_low)] = -1
        return signal
