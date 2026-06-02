"""Strategy registry — look up a strategy class by its config name."""
from __future__ import annotations

from bot.core.strategy import Strategy
from bot.strategies.donchian import DonchianBreakout
from bot.strategies.ichimoku import IchimokuStrategy
from bot.strategies.london_breakout import LondonBreakout
from bot.strategies.ma_crossover import MACrossover
from bot.strategies.macd import MACDStrategy
from bot.strategies.mean_reversion import MeanReversion
from bot.strategies.rsi import RSIStrategy
from bot.strategies.stochastic import StochasticStrategy
from bot.strategies.supertrend import SuperTrendStrategy
from bot.strategies.trend_pullback import TrendPullback

REGISTRY = {
    cls.name: cls
    for cls in (
        MeanReversion,
        RSIStrategy,
        StochasticStrategy,
        MACrossover,
        MACDStrategy,
        SuperTrendStrategy,
        IchimokuStrategy,
        DonchianBreakout,
        LondonBreakout,
        TrendPullback,
    )
}


def build_strategy(name: str, params: dict | None = None) -> Strategy:
    if name not in REGISTRY:
        raise ValueError(f"Unknown strategy {name!r}. Available: {sorted(REGISTRY)}")
    return REGISTRY[name](**(params or {}))
