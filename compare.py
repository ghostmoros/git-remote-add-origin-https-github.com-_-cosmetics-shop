"""Backtest every registered strategy and rank them in one table.

Each strategy is run with a stop/target profile that's *fair* for its style
(trend strategies let winners run; reversion strategies take small profits;
breakouts sit in between), so we compare apples to apples. Data and base risk
settings come from the config; only sl_atr/tp_atr are overridden per style.

Usage:
    python3 compare.py [config.yaml]
"""
from __future__ import annotations

import math
import sys

import yaml

from bot.backtest.engine import BacktestEngine
from bot.backtest.metrics import compute
from bot.data.feed import load_data
from bot.strategies import REGISTRY, build_strategy

# Fair stop/target profile per strategy style (ATR multiples).
STYLE_RISK = {
    "trend": {"sl_atr": 2.0, "tp_atr": 4.0},
    "reversion": {"sl_atr": 2.5, "tp_atr": 1.0},
    "breakout": {"sl_atr": 1.5, "tp_atr": 3.0},
}


def main(config_path: str = "config/config.yaml") -> None:
    with open(config_path) as fh:
        cfg = yaml.safe_load(fh)

    df = load_data(cfg["data"])
    base = dict(cfg["backtest"])
    print(f"\nData: {len(df)} candles ({df.index[0]:%Y-%m-%d} -> {df.index[-1]:%Y-%m-%d})\n")

    rows = []
    for name in REGISTRY:
        strategy = build_strategy(name)  # default params for a fair bake-off
        signals = strategy.generate_signals(df)
        risk = {**base, **STYLE_RISK.get(strategy.style, {})}
        metrics = compute(BacktestEngine(**risk).run(df, signals))
        rows.append({
            "name": name,
            "style": strategy.style,
            "sl": risk["sl_atr"],
            "tp": risk["tp_atr"],
            **metrics,
        })

    rows.sort(key=lambda r: r["expectancy_r"], reverse=True)

    header = (f'{"strategy":<16}{"style":<11}{"sl/tp":>8} | {"trades":>6} {"win%":>6} '
              f'{"PF":>6} {"exp_R":>7} {"ret%":>9} {"maxDD%":>7}')
    print(header)
    print("-" * len(header))
    for r in rows:
        pf = 99.99 if math.isinf(r["profit_factor"]) else r["profit_factor"]
        sltp = f'{r["sl"]:.1f}/{r["tp"]:.1f}'
        print(f'{r["name"]:<16}{r["style"]:<11}{sltp:>8} | '
              f'{r["trades"]:6d} {r["win_rate"] * 100:6.1f} {pf:6.2f} '
              f'{r["expectancy_r"]:+7.3f} {r["total_return"] * 100:+9.1f} '
              f'{r["max_drawdown"] * 100:7.1f}')

    print("\nRanked by expectancy (R per trade) — the metric that actually compounds.")
    best = rows[0]
    print(f'Best here: {best["name"]} ({best["win_rate"] * 100:.1f}% win, '
          f'{best["expectancy_r"]:+.3f} R, {best["total_return"] * 100:+.1f}%).')
    print("Reminder: these are SYNTHETIC results — confirm any edge on real data.\n")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "config/config.yaml")
