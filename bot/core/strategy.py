"""Base strategy interface.

A strategy turns price data into *entry signals*. It does NOT decide position
size, stop-loss, take-profit or talk to a broker — that separation is what lets
the same strategy run in backtest, paper and live without changes.

Signal convention (one value per bar):
    +1  -> want to be long
    -1  -> want to be short
     0  -> no opinion / stay flat

The engine reads these, applies risk management and executes on the *next* bar
to avoid look-ahead bias.
"""
from __future__ import annotations

import pandas as pd


class Strategy:
    name = "base"
    # "trend" | "reversion" | "breakout" — hints the comparison tool which
    # stop/target profile is fair for this strategy (trend lets winners run,
    # reversion takes small profits, breakout sits in between).
    style = "trend"

    def __init__(self, **params):
        self.params = params

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """Return an int Series in {-1, 0, +1} aligned to df.index."""
        raise NotImplementedError
