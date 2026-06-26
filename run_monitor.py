"""Live market monitor — бот сам следит за графиком и алертит при сетапе.

Использование:
    python run_monitor.py                        # мониторинг каждые 60 сек
    python run_monitor.py --interval 30          # каждые 30 сек
    python run_monitor.py --interval 120 --min-cf 4   # каждые 2 мин, 4+ confluences
    python run_monitor.py --context "XAUUSD H1 NY"    # задать контекст инструмента
    python run_monitor.py --region 0 0 1920 1080       # конкретная область экрана

Бот:
  1. Делает скриншот экрана автоматически
  2. Быстро проверяет — есть ли сетап
  3. Если нашёл 3+ confluences — делает полный SMC анализ
  4. Выводит детальный алерт и пищит
  5. Ждёт interval секунд и повторяет
"""
from __future__ import annotations

import argparse
import sys

from bot.ai_agent.market_monitor import MarketMonitor


def main() -> None:
    parser = argparse.ArgumentParser(description="Live Market Monitor")
    parser.add_argument("--interval", type=int, default=60,
                        help="Интервал между сканами в секундах (default: 60)")
    parser.add_argument("--min-cf", type=int, default=3, dest="min_cf",
                        help="Минимальное кол-во confluences для алерта (default: 3)")
    parser.add_argument("--context", type=str, default="",
                        help="Контекст торговли: инструмент, таймфрейм, сессия")
    parser.add_argument("--region", type=int, nargs=4, default=None,
                        metavar=("LEFT", "TOP", "WIDTH", "HEIGHT"),
                        help="Область экрана для захвата (px)")
    parser.add_argument("--api-key", type=str, default=None,
                        help="Anthropic API key")
    args = parser.parse_args()

    region = None
    if args.region:
        left, top, width, height = args.region
        region = {"left": left, "top": top, "width": width, "height": height}

    try:
        monitor = MarketMonitor(
            interval=args.interval,
            min_confluences=args.min_cf,
            api_key=args.api_key,
            region=region,
        )
    except ValueError as e:
        print(f"Ошибка: {e}")
        sys.exit(1)

    if args.context:
        monitor.set_context(args.context)
        print(f"Контекст: {args.context}")

    monitor.run()


if __name__ == "__main__":
    main()
