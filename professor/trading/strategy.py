"""Торговые стратегии. Сигнал на каждой свече: BUY / SELL / HOLD."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .data import Candle
from .indicators import rsi, sma


class Signal(Enum):
    BUY = 1
    SELL = -1
    HOLD = 0


class Strategy:
    """Базовый класс стратегии."""

    name = "base"

    def generate(self, candles: list[Candle]) -> list[Signal]:
        raise NotImplementedError


@dataclass
class SmaRsiStrategy(Strategy):
    """Пересечение SMA с фильтром по RSI.

    BUY  — быстрая SMA пересекает медленную снизу вверх и RSI не перегрет.
    SELL — быстрая SMA пересекает медленную сверху вниз и RSI не перепродан.
    """

    fast: int = 20
    slow: int = 50
    rsi_period: int = 14
    rsi_ob: float = 70.0
    rsi_os: float = 30.0
    name: str = "SMA-cross + RSI"

    def generate(self, candles: list[Candle]) -> list[Signal]:
        closes = [c.close for c in candles]
        fast = sma(closes, self.fast)
        slow = sma(closes, self.slow)
        r = rsi(closes, self.rsi_period)
        signals: list[Signal] = [Signal.HOLD] * len(candles)
        for i in range(1, len(candles)):
            f, s, fp, sp = fast[i], slow[i], fast[i - 1], slow[i - 1]
            if None in (f, s, fp, sp):
                continue
            ri = r[i] if r[i] is not None else 50.0
            crossed_up = fp <= sp and f > s
            crossed_down = fp >= sp and f < s
            if crossed_up and ri < self.rsi_ob:
                signals[i] = Signal.BUY
            elif crossed_down and ri > self.rsi_os:
                signals[i] = Signal.SELL
        return signals
