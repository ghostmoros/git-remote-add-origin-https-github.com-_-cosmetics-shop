"""Walk-forward анализ: честная out-of-sample проверка с переоптимизацией параметров.

Идея: на каждом шаге оптимизируем параметры на обучающем окне (in-sample), затем
проверяем их на следующем окне (out-of-sample), которого оптимизация не видела.
Склеенные OOS-результаты — реалистичная оценка. Разрыв между «оптимизация на всех
данных» (in-sample) и OOS показывает цену переобучения.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .backtest import run_backtest
from .data import Candle
from .metrics import TradeStats, compute_stats
from .strategy import Strategy


@dataclass
class WalkForwardResult:
    symbol: str
    n_segments: int
    chosen_params: list[dict]
    oos_stats: TradeStats        # честный out-of-sample
    insample_stats: TradeStats   # лучшие параметры на ВСЕХ данных (переобучение)
    buyhold_return: float


def buy_and_hold_return(candles: list[Candle]) -> float:
    if len(candles) < 2 or candles[0].close == 0:
        return 0.0
    return candles[-1].close / candles[0].close - 1.0


def _optimize(symbol: str, candles: list[Candle], factory: Callable[[dict], Strategy],
              grid: list[dict], start_equity: float, fee_pct: float) -> dict:
    """Подбирает параметры по максимальной доходности на переданных данных."""
    best_params, best_ret = grid[0], -float("inf")
    for params in grid:
        res = run_backtest(symbol, candles, factory(params), start_equity, fee_pct)
        if res.stats.total_return > best_ret:
            best_ret, best_params = res.stats.total_return, params
    return best_params


def walk_forward(symbol: str, candles: list[Candle], factory: Callable[[dict], Strategy],
                 grid: list[dict], start_equity: float = 1000.0, fee_pct: float = 0.04,
                 in_size: int = 300, out_size: int = 120,
                 warmup: int = 60) -> WalkForwardResult:
    """Прогоняет walk-forward и возвращает OOS-метрики + переобученный бенчмарк."""
    oos_pnls: list[float] = []
    oos_equity: list[float] = []
    chosen: list[dict] = []
    equity = start_equity

    start = 0
    while start + in_size + out_size <= len(candles):
        train = candles[start:start + in_size]
        best = _optimize(symbol, train, factory, grid, start_equity, fee_pct)

        # OOS-окно с прогревом: индикаторы видят историю до окна, сделки — только в окне
        lo = max(0, start + in_size - warmup)
        eff_warmup = (start + in_size) - lo
        test = candles[lo:start + in_size + out_size]
        res = run_backtest(symbol, test, factory(best), equity, fee_pct, warmup=eff_warmup)

        oos_pnls.extend(t.pnl for t in res.trades)
        oos_equity.extend(res.equity_curve)
        equity = res.stats.final_equity
        chosen.append(best)
        start += out_size

    oos_stats = compute_stats(oos_pnls, oos_equity or [start_equity], start_equity)

    # «оптимистичный» бенчмарк: лучшие параметры на ВСЕЙ истории (переобучение)
    best_full = _optimize(symbol, candles, factory, grid, start_equity, fee_pct)
    insample_stats = run_backtest(symbol, candles, factory(best_full),
                                  start_equity, fee_pct).stats

    return WalkForwardResult(symbol, len(chosen), chosen, oos_stats, insample_stats,
                             buy_and_hold_return(candles))
