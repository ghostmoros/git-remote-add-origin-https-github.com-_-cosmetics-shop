"""Entry point: load config -> data -> strategy -> backtest -> report.

Usage:
    python3 main.py                 # uses config/config.yaml
    python3 main.py my_config.yaml  # custom config
"""
from __future__ import annotations

import sys

import yaml

from bot.backtest.engine import BacktestEngine
from bot.backtest.metrics import compute, format_report
from bot.data.feed import load_data
from bot.strategies import build_strategy


def run(config_path: str = "config/config.yaml") -> dict:
    with open(config_path) as fh:
        cfg = yaml.safe_load(fh)

    df = load_data(cfg["data"])
    strategy = build_strategy(cfg["strategy"]["name"], cfg["strategy"].get("params"))
    signals = strategy.generate_signals(df)

    engine = BacktestEngine(**cfg["backtest"])
    result = engine.run(df, signals)

    metrics = compute(result)
    print(f"\nLoaded {len(df)} candles "
          f"({df.index[0]:%Y-%m-%d} -> {df.index[-1]:%Y-%m-%d}), "
          f"generated {int((signals != 0).sum())} raw signals.")
    print(format_report(strategy.name, metrics))
    return metrics


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "config/config.yaml")
