"""Download real candle history from your MT5 terminal into a CSV.

Runs on YOUR machine (needs the MT5 terminal + the MetaTrader5 package). The
output CSV plugs straight into the backtester:

    data:
      source: csv
      csv_path: data/EURUSD_H1.csv

Usage (on your PC, with MT5 creds in the environment):
    python fetch_history.py                   # symbol/timeframe from config
    python fetch_history.py EURUSD H1 5000     # symbol timeframe count override
"""
from __future__ import annotations

import sys

import yaml

from bot.brokers.mt5 import MT5Broker


def main(symbol: str | None = None, timeframe: str | None = None,
         count: int | None = None, config_path: str = "config/config.yaml") -> None:
    with open(config_path) as fh:
        cfg = yaml.safe_load(fh)
    broker_cfg = cfg.get("broker", {})

    symbol = symbol or broker_cfg.get("symbol", "EURUSD")
    timeframe = timeframe or broker_cfg.get("timeframe", "H1")
    count = int(count or broker_cfg.get("candles", 5000))

    broker = MT5Broker.from_env()
    broker.connect()
    try:
        df = broker.get_candles(symbol, timeframe, count)
    finally:
        broker.shutdown()

    out_path = f"data/{symbol}_{timeframe}.csv"
    df.to_csv(out_path, index_label="time")
    print(f"Saved {len(df)} candles -> {out_path}")
    print(f"Range: {df.index[0]} .. {df.index[-1]}")
    print("\nNow backtest on it:\n"
          "  set config.yaml -> data.source: csv, "
          f"data.csv_path: {out_path}\n"
          "  python compare.py")


if __name__ == "__main__":
    args = sys.argv[1:]
    main(
        symbol=args[0] if len(args) > 0 else None,
        timeframe=args[1] if len(args) > 1 else None,
        count=args[2] if len(args) > 2 else None,
    )
