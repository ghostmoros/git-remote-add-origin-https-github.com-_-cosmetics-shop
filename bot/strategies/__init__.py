"""Strategy registry — look up a strategy class by its config name."""
from __future__ import annotations

from bot.core.strategy import Strategy
from bot.strategies.ma_crossover import MACrossover
from bot.strategies.mean_reversion import MeanReversion

REGISTRY = {
    MeanReversion.name: MeanReversion,
    MACrossover.name: MACrossover,
}


def build_strategy(name: str, params: dict | None = None) -> Strategy:
    if name not in REGISTRY:
        raise ValueError(f"Unknown strategy {name!r}. Available: {sorted(REGISTRY)}")
    return REGISTRY[name](**(params or {}))
