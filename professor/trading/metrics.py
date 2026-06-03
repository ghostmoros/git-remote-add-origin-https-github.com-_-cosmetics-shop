"""Метрики результата бэктеста. Считаем то, что реально определяет прибыльность."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TradeStats:
    n_trades: int
    win_rate: float          # доля прибыльных сделок
    profit_factor: float     # сумма прибылей / сумма убытков
    expectancy: float        # средний результат сделки, $
    total_return: float      # доходность от стартового капитала, доля
    max_drawdown: float      # максимальная просадка, доля
    final_equity: float


def compute_stats(trade_pnls: list[float], equity_curve: list[float],
                  start_equity: float) -> TradeStats:
    n = len(trade_pnls)
    wins = [p for p in trade_pnls if p > 0]
    losses = [p for p in trade_pnls if p < 0]
    win_rate = len(wins) / n if n else 0.0
    gross_win = sum(wins)
    gross_loss = -sum(losses)
    if gross_loss > 0:
        profit_factor = gross_win / gross_loss
    else:
        profit_factor = float("inf") if gross_win > 0 else 0.0
    expectancy = (sum(trade_pnls) / n) if n else 0.0
    final_equity = equity_curve[-1] if equity_curve else start_equity
    total_return = (final_equity - start_equity) / start_equity if start_equity else 0.0

    peak = -float("inf")
    max_dd = 0.0
    for e in equity_curve:
        peak = max(peak, e)
        if peak > 0:
            max_dd = max(max_dd, (peak - e) / peak)

    return TradeStats(n, win_rate, profit_factor, expectancy,
                      total_return, max_dd, final_equity)
