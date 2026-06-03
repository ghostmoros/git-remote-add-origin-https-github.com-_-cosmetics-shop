"""Сканер возможностей Polymarket: арбитраж + value-ставки (edge vs честная оценка).

Логика prediction-маркета: доля YES/NO стоит от 0 до 1 и при выигрыше
выплачивает 1$. Цена ≈ вероятность исхода по мнению рынка.
"""
from __future__ import annotations

from dataclasses import dataclass

from .models import PMMarket


@dataclass
class Opportunity:
    market: PMMarket
    kind: str            # "arbitrage" | "value-yes" | "value-no"
    side: str            # "YES" | "NO" | "YES+NO"
    price: float         # цена входа
    fair_prob: float     # оценка вероятности выигрыша выбранной стороны
    edge: float          # преимущество (fair - price), в долях
    ev_per_dollar: float # ожидаемая прибыль на $1 ставки
    kelly: float         # рекомендуемая доля банка (дробный Келли)


def _kelly(p: float, price: float) -> float:
    """Доля банка по Келли для бинарного исхода с выплатой 1 за цену `price`.

    Прибыль при выигрыше b = (1-price)/price. f* = (p - price) / (1 - price).
    """
    if price <= 0 or price >= 1:
        return 0.0
    return max(0.0, (p - price) / (1 - price))


def scan(markets: list[PMMarket], min_edge: float = 0.05, min_volume: float = 0.0,
         kelly_fraction: float = 0.25) -> list[Opportunity]:
    """Находит и ранжирует возможности по ожидаемой прибыли на $1."""
    opps: list[Opportunity] = []
    for m in markets:
        if m.volume < min_volume:
            continue

        # 1) Арбитраж: YES + NO < 1 → гарантированная прибыль на любом исходе.
        total = m.yes_price + m.no_price
        if total < 1.0:
            profit = (1.0 - total) / total            # прибыль на вложенный $
            if profit >= 0.005:                       # порог, чтобы перекрыть комиссии
                opps.append(Opportunity(m, "arbitrage", "YES+NO", round(total, 3),
                                        1.0, round(1.0 - total, 3), profit, 1.0))

        # 2) Value: сравниваем «честную» вероятность с рыночной ценой.
        fair = m.fair_yes if m.fair_yes is not None else m.yes_price

        edge_yes = fair - m.yes_price                 # покупка YES
        if edge_yes >= min_edge and m.yes_price > 0:
            opps.append(Opportunity(m, "value-yes", "YES", m.yes_price, fair, edge_yes,
                                    edge_yes / m.yes_price,
                                    _kelly(fair, m.yes_price) * kelly_fraction))

        fair_no = 1 - fair                            # покупка NO
        edge_no = fair_no - m.no_price
        if edge_no >= min_edge and m.no_price > 0:
            opps.append(Opportunity(m, "value-no", "NO", m.no_price, fair_no, edge_no,
                                    edge_no / m.no_price,
                                    _kelly(fair_no, m.no_price) * kelly_fraction))

    opps.sort(key=lambda o: o.ev_per_dollar, reverse=True)
    return opps
