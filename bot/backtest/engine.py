"""Event-driven backtest engine with risk-based position sizing.

Responsibilities (kept separate from the strategy on purpose):
  - turn a strategy's signals into trades,
  - size each position so a stop-loss hit loses exactly `risk_pct` of equity,
  - place ATR-based stop-loss / take-profit,
  - simulate fills bar-by-bar without look-ahead bias.

No-look-ahead rule: a signal computed from bar i's close is acted on at bar
i+1's open (we shift signals by one). Stops/targets are sized from the ATR of
the last *closed* bar.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import numpy as np
import pandas as pd

from bot.data.indicators import atr as atr_indicator


@dataclass
class Trade:
    direction: int  # +1 long, -1 short
    entry_time: datetime
    entry_price: float
    exit_time: datetime
    exit_price: float
    size: float
    pnl: float
    r_multiple: float  # pnl expressed in units of risk (1R = the planned loss)
    risk: float
    exit_reason: str  # 'tp' | 'sl' | 'signal' | 'eod'


@dataclass
class BacktestResult:
    trades: list[Trade]
    equity_curve: pd.Series
    initial_balance: float
    final_balance: float


class BacktestEngine:
    def __init__(
        self,
        initial_balance: float = 10_000.0,
        risk_pct: float = 0.01,
        atr_period: int = 14,
        sl_atr: float = 2.0,
        tp_atr: float = 1.5,
        spread: float = 0.0001,
        **extra,
    ):
        self.initial_balance = float(initial_balance)
        self.risk_pct = float(risk_pct)
        self.atr_period = int(atr_period)
        self.sl_atr = float(sl_atr)
        self.tp_atr = float(tp_atr)
        self.spread = float(spread)  # round-trip cost in price units

    def run(self, df: pd.DataFrame, signals: pd.Series) -> BacktestResult:
        n = len(df)
        atr_prev = atr_indicator(df["high"], df["low"], df["close"], self.atr_period).shift(1)
        # Act on the bar AFTER the signal -> no look-ahead.
        entry_sig = signals.shift(1).fillna(0).astype(int)

        o = df["open"].to_numpy(float)
        h = df["high"].to_numpy(float)
        low = df["low"].to_numpy(float)
        c = df["close"].to_numpy(float)
        ap = atr_prev.to_numpy(float)
        es = entry_sig.to_numpy(int)
        idx = df.index

        equity = self.initial_balance
        trades: list[Trade] = []
        equity_curve = np.empty(n, dtype=float)

        in_pos = False
        direction = 0
        entry_price = sl = tp = size = risk = 0.0
        entry_time = None

        def close_trade(exit_price: float, reason: str, exit_i: int) -> None:
            nonlocal equity, in_pos
            pnl = direction * (exit_price - entry_price) * size - self.spread * size
            equity += pnl
            trades.append(
                Trade(
                    direction=direction,
                    entry_time=entry_time,
                    entry_price=entry_price,
                    exit_time=idx[exit_i],
                    exit_price=exit_price,
                    size=size,
                    pnl=pnl,
                    r_multiple=pnl / risk if risk > 0 else 0.0,
                    risk=risk,
                    exit_reason=reason,
                )
            )
            in_pos = False

        for i in range(n):
            # 1) Manage an open position on this bar.
            if in_pos:
                if es[i] == -direction:
                    # Strategy flipped its view -> exit at the open.
                    close_trade(o[i], "signal", i)
                elif direction == 1:
                    if low[i] <= sl:  # assume SL fills first if both touched
                        close_trade(sl, "sl", i)
                    elif h[i] >= tp:
                        close_trade(tp, "tp", i)
                else:  # short
                    if h[i] >= sl:
                        close_trade(sl, "sl", i)
                    elif low[i] <= tp:
                        close_trade(tp, "tp", i)

            # 2) Open a new position if flat and we have a valid signal + ATR.
            if (not in_pos) and es[i] != 0 and not np.isnan(ap[i]) and ap[i] > 0:
                direction = int(es[i])
                entry_price = o[i]
                stop_dist = self.sl_atr * ap[i]
                tp_dist = self.tp_atr * ap[i]
                if direction == 1:
                    sl = entry_price - stop_dist
                    tp = entry_price + tp_dist
                else:
                    sl = entry_price + stop_dist
                    tp = entry_price - tp_dist
                risk = equity * self.risk_pct
                size = risk / stop_dist  # so a full stop = exactly `risk`
                entry_time = idx[i]
                in_pos = True

            # 3) Mark-to-market equity at this bar's close.
            equity_curve[i] = equity + (direction * (c[i] - entry_price) * size if in_pos else 0.0)

        if in_pos:
            close_trade(c[-1], "eod", n - 1)

        return BacktestResult(
            trades=trades,
            equity_curve=pd.Series(equity_curve, index=idx, name="equity"),
            initial_balance=self.initial_balance,
            final_balance=equity,
        )
