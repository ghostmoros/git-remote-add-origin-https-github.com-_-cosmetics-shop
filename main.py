#!/usr/bin/env python3
"""Профессор — запуск симуляции: крипто-трейдинг + поиск возможностей на Polymarket.

Использование:
    python3 main.py                 # режим СИМУЛЯЦИИ (по умолчанию: без сети/ключей)
    python3 main.py --live          # реальные публичные API (при блокировке — откат)
    python3 main.py --wf            # walk-forward анализ Donchian breakout
    python3 main.py --csv FILE      # запуск на реальных данных из CSV-файла
    python3 main.py --wf --csv FILE # walk-forward на реальных данных из CSV
"""
from __future__ import annotations

import sys

from professor import __version__
from professor.config import Config
from professor.engine import run_polymarket, run_trading, run_walkforward
from professor.report import render_polymarket, render_trading, render_walkforward


def main(argv: list[str]) -> int:
    cfg = Config()
    if "--live" in argv:
        cfg.mode = "live"
    if "--csv" in argv:
        i = argv.index("--csv")
        if i + 1 < len(argv):
            cfg.csv_path = argv[i + 1]

    if cfg.csv_path:
        mode_label = "РЕАЛЬНЫЕ ДАННЫЕ (CSV)"
    elif cfg.mode == "live":
        mode_label = "LIVE (реальные публичные API)"
    else:
        mode_label = "СИМУЛЯЦИЯ (paper, без риска)"
    print("=" * 66)
    print(f"  ПРОФЕССОР v{__version__}  —  крипто-трейдинг + Polymarket")
    print("=" * 66)
    print(f"Режим: {mode_label}  ·  капитал на символ: ${cfg.capital:,.0f}\n")

    if "--wf" in argv:           # режим walk-forward анализа
        wf_results, wf_src = run_walkforward(cfg)
        print(render_walkforward(wf_results))
        print(f"Источник данных: {wf_src}\n")
        print("─" * 66)
        print("⚠️  Бэктест ≠ гарантия. OOS-результат — реалистичный ориентир,")
        print("    но вживую добавятся проскальзывание и задержки. Не финсовет.")
        return 0

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
