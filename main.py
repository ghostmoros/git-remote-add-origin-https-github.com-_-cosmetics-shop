#!/usr/bin/env python3
"""Профессор — запуск симуляции: крипто-трейдинг + поиск возможностей на Polymarket.

Использование:
    python3 main.py            # режим СИМУЛЯЦИИ (по умолчанию: без сети и ключей)
    python3 main.py --live     # попытаться использовать реальные публичные API
                               # (Binance / Polymarket Gamma); при блокировке —
                               # автоматический откат на симуляцию
"""
from __future__ import annotations

import sys

from professor import __version__
from professor.config import Config
from professor.engine import run_polymarket, run_trading
from professor.report import render_polymarket, render_trading


def main(argv: list[str]) -> int:
    cfg = Config()
    if "--live" in argv:
        cfg.mode = "live"

    mode_label = ("LIVE (реальные публичные API)" if cfg.mode == "live"
                  else "СИМУЛЯЦИЯ (paper, без риска)")
    print("=" * 66)
    print(f"  ПРОФЕССОР v{__version__}  —  крипто-трейдинг + Polymarket")
    print("=" * 66)
    print(f"Режим: {mode_label}  ·  капитал на символ: ${cfg.capital:,.0f}\n")

    tr_results, tr_src = run_trading(cfg)
    print(render_trading(tr_results, cfg.capital))
    print(f"Источник данных: {tr_src}\n")

    pm_opps, pm_src = run_polymarket(cfg)
    print(render_polymarket(pm_opps, cfg.polymarket.max_results))
    print(f"Источник данных: {pm_src}\n")

    print("─" * 66)
    print("⚠️  Это СИМУЛЯЦИЯ и НЕ финансовый совет. Перед реальными деньгами")
    print("    тестируйте на демо и осознавайте риски — можно потерять весь капитал.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
