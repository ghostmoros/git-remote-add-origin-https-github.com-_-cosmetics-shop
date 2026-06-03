"""Paper-брокер + бэктест. Long-only (спот): BUY открывает, SELL закрывает позицию.

Long-only выбран намеренно для безопасной симуляции: эквити не может уйти в
минус (максимальный убыток позиции ограничен её стоимостью).
"""
from __future__ import annotations

from dataclasses import dataclass

from .data import Candle
from .metrics import TradeStats, compute_stats
from .strategy import Signal, Strategy


@dataclass
class Trade:
    side: str        # пока только "long"
    entry: float
    exit: float
    units: float
    pnl: float


@dataclass
class BacktestResult:
    symbol: str
    strategy: str
    trades: list[Trade]
    equity_curve: list[float]
    stats: TradeStats


def run_backtest(symbol: str, candles: list[Candle], strategy: Strategy,
                 start_equity: float, fee_pct: float = 0.04,
                 exposure: float = 0.95) -> BacktestResult:
    """Прогоняет стратегию по свечам и возвращает результат с метриками."""
    signals = strategy.generate(candles)
    fee = fee_pct / 100.0

    equity = start_equity
    in_pos = False
    entry_price = 0.0
    units = 0.0
    trades: list[Trade] = []
    equity_curve: list[float] = []

    def open_long(price: float) -> None:
        nonlocal in_pos, units, entry_price, equity
        notional = equity * exposure
        units = notional / price
        entry_price = price
        equity -= notional * fee     # комиссия на входе
        in_pos = True

    def close_long(price: float) -> None:
        nonlocal in_pos, units, entry_price, equity
        if not in_pos:
            return
        pnl = units * (price - entry_price) - units * price * fee
        equity += pnl
        trades.append(Trade("long", entry_price, price, units, pnl))
        in_pos = False
        units = 0.0
        entry_price = 0.0

    for i, c in enumerate(candles):
        sig = signals[i]
        price = c.close
        if sig == Signal.BUY and not in_pos:
            open_long(price)
        elif sig == Signal.SELL and in_pos:
            close_long(price)
        # отметка эквити по рынку (mark-to-market)
        if in_pos:
            equity_curve.append(equity + units * (price - entry_price))
        else:
            equity_curve.append(equity)

    if in_pos:                        # закрываем открытую позицию в конце прогона
        close_long(candles[-1].close)
    if equity_curve:
        equity_curve[-1] = equity

    stats = compute_stats([t.pnl for t in trades], equity_curve, start_equity)
    return BacktestResult(symbol, strategy.name, trades, equity_curve, stats)
