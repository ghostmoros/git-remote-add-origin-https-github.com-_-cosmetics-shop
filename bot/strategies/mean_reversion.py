"""Bollinger-band mean reversion — tuned for a HIGH WIN RATE.

Core idea: a 2-sigma stretch away from the moving average usually snaps back at
least partway to the mean. So we fade extremes:
  - go LONG when price closes below the lower band (oversold), and
  - go SHORT when price closes above the upper band (overbought).

Optional confirmations make entries stricter (fewer, higher-quality trades):
  - require_rsi=True     -> also require RSI in oversold/overbought territory.
  - use_trend_filter=True-> only trade in the direction of the slow EMA
                            (buy dips in uptrends, sell rips in downtrends).

Why the win rate is high: paired with a *small* take-profit and a *wider*
stop-loss (set in the backtest config), most trades catch the small bounce back
to the mean before the rare big adverse move. Be honest, though: that same
small-TP/wide-SL profile means a high win rate does NOT guarantee profit — read
profit_factor and expectancy in the report, not just win_rate.
"""
from __future__ import annotations

import pandas as pd

from bot.core.strategy import Strategy
from bot.data.indicators import bollinger, ema, rsi


class MeanReversion(Strategy):
    name = "mean_reversion"
    style = "reversion"

    def __init__(
        self,
        bb_period: int = 20,
        bb_std: float = 2.0,
        require_rsi: bool = False,
        rsi_period: int = 14,
        rsi_oversold: float = 35.0,
        rsi_overbought: float = 65.0,
        use_trend_filter: bool = False,
        trend_ema: int = 200,
        **extra,
    ):
        super().__init__(
            bb_period=bb_period,
            bb_std=bb_std,
            require_rsi=require_rsi,
            rsi_period=rsi_period,
            rsi_oversold=rsi_oversold,
            rsi_overbought=rsi_overbought,
            use_trend_filter=use_trend_filter,
            trend_ema=trend_ema,
            **extra,
        )

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        p = self.params
        close = df["close"]

        _mid, upper, lower = bollinger(close, p["bb_period"], p["bb_std"])
        long_cond = close < lower
        short_cond = close > upper

        if p["require_rsi"]:
            r = rsi(close, p["rsi_period"])
            long_cond &= r < p["rsi_oversold"]
            short_cond &= r > p["rsi_overbought"]

        if p["use_trend_filter"]:
            trend = ema(close, p["trend_ema"])
            long_cond &= close > trend
            short_cond &= close < trend

        signal = pd.Series(0, index=df.index, dtype="int64")
        signal[long_cond] = 1
        signal[short_cond] = -1
        return signal
