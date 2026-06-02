"""Broker interface — the seam between the bot and a real trading venue.

Implement this once per venue (MetaTrader 5, OANDA, …) and nothing else in the
bot has to change. The backtest engine is effectively the 'simulated' broker;
MT5Broker is a live one. A strategy never imports a broker — it only emits
signals — so the same strategy runs in backtest, demo and live.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class Broker(ABC):
    @abstractmethod
    def connect(self) -> None:
        """Open the connection / log in."""

    @abstractmethod
    def get_candles(self, symbol: str, timeframe: str, count: int) -> pd.DataFrame:
        """Return the latest `count` candles as open/high/low/close[/volume]."""

    @abstractmethod
    def account_info(self) -> dict:
        """Account snapshot (login, server, balance, currency, demo/real…)."""

    @abstractmethod
    def positions(self, symbol: str | None = None) -> list[dict]:
        """Currently open positions, optionally filtered by symbol."""

    @abstractmethod
    def market_order(self, symbol: str, side: str, volume: float,
                     sl: float | None = None, tp: float | None = None,
                     comment: str = "") -> dict:
        """Send a market order. `side` is 'buy' or 'sell'; `volume` in lots."""

    @abstractmethod
    def close_position(self, ticket: int) -> dict:
        """Close an open position by its ticket id."""

    def shutdown(self) -> None:
        """Tear down the connection. Safe to override or leave as a no-op."""
