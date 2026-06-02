"""Trend pullback with an ADX strength filter — built for GOLD (XAUUSD).

Gold trends hard and whipsaws in ranges, so this strategy:
  1. defines the trend with two EMAs (fast over slow, price above slow = up),
  2. only acts when ADX confirms the trend is strong (skips the chop),
  3. enters on a *pullback*: price dips to/below the fast EMA and then reclaims
     it in the trend direction — a higher-probability entry than chasing.

It's a trend style, so pair it with a wide take-profit (let winners run); the
config_gold.yaml profile does exactly that. Mean reversion, by contrast, tends
to get run over by gold's trends — hence this dedicated strategy.
"""
from __future__ import annotations

import pandas as pd

from bot.core.strategy import Strategy
from bot.data.indicators import adx, ema


class TrendPullback(Strategy):
    name = "trend_pullback"
    style = "trend"

    def __init__(self, ema_fast: int = 21, ema_slow: int = 50,
                 adx_period: int = 14, adx_min: float = 20.0, **extra):
        super().__init__(ema_fast=ema_fast, ema_slow=ema_slow,
                         adx_period=adx_period, adx_min=adx_min, **extra)

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        p = self.params
        close = df["close"]

        fast = ema(close, p["ema_fast"])
        slow = ema(close, p["ema_slow"])
        strength, _plus_di, _minus_di = adx(df["high"], df["low"], close, p["adx_period"])
        strong = strength > p["adx_min"]

        uptrend = (fast > slow) & (close > slow) & strong
        downtrend = (fast < slow) & (close < slow) & strong

        # Pullback entry: price was below the fast EMA last bar and reclaims it now
        # (mirror for shorts), i.e. buy the dip / sell the rally within the trend.
        reclaim_up = (close.shift(1) < fast.shift(1)) & (close > fast)
        reclaim_down = (close.shift(1) > fast.shift(1)) & (close < fast)

        signal = pd.Series(0, index=df.index, dtype="int64")
        signal[uptrend & reclaim_up] = 1
        signal[downtrend & reclaim_down] = -1
        return signal
