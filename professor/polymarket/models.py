"""Модель рынка Polymarket."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PMMarket:
    market_id: str
    question: str
    category: str
    yes_price: float          # цена доли YES (≈ вероятность по рынку), 0..1
    no_price: float           # цена доли NO
    volume: float             # торговый объём, $
    liquidity: float = 0.0    # ликвидность, $
    # «честная» оценка вероятности YES (модель/эксперт). В симуляции
    # генерируется; в live по умолчанию None (= нет своего мнения, берём рынок).
    fair_yes: float | None = None
