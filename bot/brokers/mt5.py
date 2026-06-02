"""MetaTrader 5 broker adapter — works with RoboForex and any other MT5 broker.

IMPORTANT — where this runs:
    The `MetaTrader5` Python package talks to a MetaTrader 5 terminal over local
    IPC, so it ONLY works on a machine (Windows) where the MT5 terminal is
    installed and running. It does NOT work in a cloud/Linux sandbox. Run this
    on YOUR computer with your RoboForex terminal open.

Credentials come from environment variables and never touch the repo:
    MT5_LOGIN     your account number (e.g. 12345678)
    MT5_PASSWORD  your account password
    MT5_SERVER    your broker server, e.g. RoboForex-Demo / RoboForex-Pro / RoboForex-ECN
    MT5_PATH      (optional) full path to terminal64.exe if auto-detect fails

Always start on a DEMO account.
"""
from __future__ import annotations

import os

import pandas as pd

from bot.brokers.base import Broker


class MT5Broker(Broker):
    def __init__(self, login: int, password: str, server: str, path: str | None = None):
        self.login = int(login)
        self.password = password
        self.server = server
        self.path = path
        self._mt5 = None  # the MetaTrader5 module, imported lazily

    @classmethod
    def from_env(cls) -> "MT5Broker":
        try:
            login = os.environ["MT5_LOGIN"]
            password = os.environ["MT5_PASSWORD"]
            server = os.environ["MT5_SERVER"]
        except KeyError as exc:
            raise RuntimeError(
                f"Missing environment variable {exc}. Set MT5_LOGIN, MT5_PASSWORD "
                "and MT5_SERVER (e.g. RoboForex-Demo) before running."
            ) from exc
        return cls(login, password, server, os.environ.get("MT5_PATH"))

    # -- internals -----------------------------------------------------------
    def _lib(self):
        if self._mt5 is None:
            try:
                import MetaTrader5 as mt5
            except ImportError as exc:
                raise RuntimeError(
                    "The MetaTrader5 package isn't available here. It is Windows-only "
                    "and must run where the MT5 terminal is installed:\n"
                    "    pip install -r requirements-live.txt"
                ) from exc
            self._mt5 = mt5
        return self._mt5

    def _timeframe(self, name: str):
        mt5 = self._lib()
        table = {
            "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15,
            "M30": mt5.TIMEFRAME_M30, "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1, "W1": mt5.TIMEFRAME_W1,
        }
        if name not in table:
            raise ValueError(f"Unsupported timeframe {name!r}. Choose from {sorted(table)}.")
        return table[name]

    # -- Broker interface ----------------------------------------------------
    def connect(self) -> None:
        mt5 = self._lib()
        kwargs = {"login": self.login, "password": self.password, "server": self.server}
        if self.path:
            kwargs["path"] = self.path
        if not mt5.initialize(**kwargs):
            raise RuntimeError(f"MT5 initialize/login failed: {mt5.last_error()}")

    def get_candles(self, symbol: str, timeframe: str, count: int) -> pd.DataFrame:
        mt5 = self._lib()
        rates = mt5.copy_rates_from_pos(symbol, self._timeframe(timeframe), 0, count)
        if rates is None or len(rates) == 0:
            raise RuntimeError(f"No candles for {symbol} {timeframe}: {mt5.last_error()}")
        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        df = df.set_index("time").rename(columns={"tick_volume": "volume"})
        cols = ["open", "high", "low", "close"] + (["volume"] if "volume" in df.columns else [])
        return df[cols]

    def account_info(self) -> dict:
        mt5 = self._lib()
        info = mt5.account_info()
        if info is None:
            raise RuntimeError(f"Could not read account info: {mt5.last_error()}")
        return info._asdict()

    def is_demo(self) -> bool:
        # MT5: ACCOUNT_TRADE_MODE_DEMO == 0, CONTEST == 1, REAL == 2.
        return self.account_info().get("trade_mode", 2) == 0

    def symbol_info(self, symbol: str) -> dict:
        """Contract specs incl. trade_tick_value/size and volume_min/max/step."""
        mt5 = self._lib()
        info = mt5.symbol_info(symbol)
        if info is None:
            raise RuntimeError(f"No symbol info for {symbol}: {mt5.last_error()}")
        return info._asdict()

    def positions(self, symbol: str | None = None) -> list[dict]:
        mt5 = self._lib()
        raw = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()
        return [p._asdict() for p in (raw or [])]

    def market_order(self, symbol: str, side: str, volume: float,
                     sl: float | None = None, tp: float | None = None,
                     comment: str = "forexbot") -> dict:
        mt5 = self._lib()
        if side not in ("buy", "sell"):
            raise ValueError("side must be 'buy' or 'sell'")
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            raise RuntimeError(f"No tick for {symbol}: {mt5.last_error()}")
        price = tick.ask if side == "buy" else tick.bid
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(volume),
            "type": mt5.ORDER_TYPE_BUY if side == "buy" else mt5.ORDER_TYPE_SELL,
            "price": price,
            "deviation": 20,
            "magic": 424242,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_FOK,
        }
        if sl is not None:
            request["sl"] = float(sl)
        if tp is not None:
            request["tp"] = float(tp)
        return mt5.order_send(request)._asdict()

    def close_position(self, ticket: int) -> dict:
        mt5 = self._lib()
        pos = next((p for p in self.positions() if p["ticket"] == ticket), None)
        if pos is None:
            raise RuntimeError(f"Position {ticket} not found")
        symbol = pos["symbol"]
        tick = mt5.symbol_info_tick(symbol)
        is_long = pos["type"] == 0  # 0 = buy, 1 = sell
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(pos["volume"]),
            "type": mt5.ORDER_TYPE_SELL if is_long else mt5.ORDER_TYPE_BUY,
            "position": ticket,
            "price": tick.bid if is_long else tick.ask,
            "deviation": 20,
            "magic": 424242,
            "comment": "forexbot-close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_FOK,
        }
        return mt5.order_send(request)._asdict()

    def shutdown(self) -> None:
        if self._mt5 is not None:
            self._mt5.shutdown()
