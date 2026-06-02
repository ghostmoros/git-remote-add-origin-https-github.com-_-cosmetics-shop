"""Grid-search the stop-loss / take-profit multiples.

Data and strategy come from the config; only the risk parameters (sl_atr,
tp_atr) are swept so you can see the win-rate vs expectancy trade-off and pick a
sensible operating point. Results are ranked two ways: by expectancy (what makes
money) and by win rate (what feels good).

Usage:
    python3 optimize.py [config.yaml]
"""
from __future__ import annotations

import math
import sys

import yaml

from bot.backtest.engine import BacktestEngine
from bot.backtest.metrics import compute
from bot.data.feed import load_data
from bot.strategies import build_strategy

SL_GRID = [1.5, 2.0, 2.5, 3.0]
TP_GRID = [0.5, 1.0, 1.5, 2.0]


def main(config_path: str = "config/config.yaml") -> None:
    with open(config_path) as fh:
        cfg = yaml.safe_load(fh)

    df = load_data(cfg["data"])
    strategy = build_strategy(cfg["strategy"]["name"], cfg["strategy"].get("params"))
    signals = strategy.generate_signals(df)
    base = dict(cfg["backtest"])

    print(f"\nStrategy: {strategy.name} | candles: {len(df)} | "
          f"raw signals: {int((signals != 0).sum())}\n")

    rows = []
    for sl in SL_GRID:
        for tp in TP_GRID:
            engine = BacktestEngine(**{**base, "sl_atr": sl, "tp_atr": tp})
            metrics = compute(engine.run(df, signals))
            rows.append({"sl": sl, "tp": tp, **metrics})

    header = (f'{"sl":>4} {"tp":>4} {"R:R":>5} | {"trades":>6} {"win%":>6} '
              f'{"PF":>6} {"exp_R":>7} {"ret%":>8} {"maxDD%":>7}')
    print(header)
    print("-" * len(header))
    for r in rows:
        pf = 99.99 if math.isinf(r["profit_factor"]) else r["profit_factor"]
        print(f'{r["sl"]:4.1f} {r["tp"]:4.1f} {r["tp"] / r["sl"]:5.2f} | '
              f'{r["trades"]:6d} {r["win_rate"] * 100:6.1f} {pf:6.2f} '
              f'{r["expectancy_r"]:+7.3f} {r["total_return"] * 100:+8.1f} '
              f'{r["max_drawdown"] * 100:7.1f}')

    best_exp = max(rows, key=lambda r: r["expectancy_r"])
    best_win = max(rows, key=lambda r: r["win_rate"])
    print("\nMost profitable (max expectancy): "
          f'sl={best_exp["sl"]}, tp={best_exp["tp"]} -> '
          f'{best_exp["win_rate"] * 100:.1f}% win, {best_exp["expectancy_r"]:+.3f} R, '
          f'{best_exp["total_return"] * 100:+.1f}%')
    print("Highest win rate                : "
          f'sl={best_win["sl"]}, tp={best_win["tp"]} -> '
          f'{best_win["win_rate"] * 100:.1f}% win, {best_win["expectancy_r"]:+.3f} R, '
          f'{best_win["total_return"] * 100:+.1f}%')
    print("\nNote: highest win rate is rarely the most profitable. "
          "Optimise expectancy, then pick a win rate you can stomach.\n")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "config/config.yaml")
