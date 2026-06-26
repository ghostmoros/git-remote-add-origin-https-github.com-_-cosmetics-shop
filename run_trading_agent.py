"""AI Trading Agent with Computer Use — интерактивный агент с управлением экраном.

Использование:
    python run_trading_agent.py                  # запуск агента
    python run_trading_agent.py --no-screenshot  # без автоскриншота при старте
    python run_trading_agent.py --api-key KEY    # явный API-ключ

Примеры команд в чате:
    Нарисуй ордер блок на последнем хае               → Claude видит экран и рисует
    Отметь FVG между этими двумя свечами              → Claude кликает на TradingView
    Проанализируй текущий график и дай сетап          → SMC/ICT анализ + скриншот
    /screen   — принудительный новый скриншот         → сбросить контекст экрана
    /context  XAUUSD H1 NY сессия                     → установить торговый контекст
    /reset    — очистить историю диалога
    /help     — показать справку
    /exit     — выход
"""
from __future__ import annotations

import argparse
import sys

from bot.ai_agent.trading_agent_cu import TradingAgentCU


HELP_TEXT = """
Доступные команды:
  /screen             — сделать новый скриншот и отправить ИИ
  /context <текст>    — установить контекст (напр: "XAUUSD H1, NY сессия")
  /reset              — очистить историю диалога
  /help               — эта справка
  /exit или /quit     — выход

Примеры задач для агента:
  "Нарисуй ордер блок на последнем хае на TradingView"
  "Отметь все FVG на этом графике"
  "Проанализируй структуру рынка, есть ли сетап для входа?"
  "Сдвинь Stop Loss на уровень 50% ордер блока"
  "Открой браузер и перейди на TradingView"
"""

WELCOME = """
╔══════════════════════════════════════════════════════════════╗
║       AI TRADING AGENT — Computer Use + SMC/ICT             ║
╠══════════════════════════════════════════════════════════════╣
║  Агент ВИДИТ твой экран и УПРАВЛЯЕТ мышью/клавиатурой       ║
║  База знаний: SMC, ICT, TA, Risk Management                 ║
║  Модель: Claude Opus 4.8 (claude-opus-4-8)                  ║
║  Введи /help для списка команд                              ║
╚══════════════════════════════════════════════════════════════╝
"""


def run_interactive(agent: TradingAgentCU, auto_screenshot: bool = True) -> None:
    print(WELCOME)
    print("ВНИМАНИЕ: Агент будет управлять мышью и клавиатурой.")
    print("Для аварийной остановки переведи мышь в левый верхний угол экрана.\n")

    while True:
        try:
            user_input = input("Ты: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nВыход.")
            break

        if not user_input:
            continue

        low = user_input.lower()

        if low in ("/exit", "/quit"):
            print("Выход.")
            break

        if low == "/help":
            print(HELP_TEXT)
            continue

        if low == "/reset":
            agent.reset_conversation()
            continue

        if low == "/screen":
            print("Делаю скриншот и отправляю ИИ...")
            _run_task(agent, "Посмотри на текущий экран и опиши что видишь на графике.", include_screenshot=True)
            continue

        if low.startswith("/context "):
            ctx = user_input[9:].strip()
            agent.set_context(ctx)
            print(f"Контекст установлен: {ctx}")
            continue

        _run_task(agent, user_input, include_screenshot=auto_screenshot)


def _run_task(agent: TradingAgentCU, message: str, include_screenshot: bool = True) -> None:
    try:
        print("\nАгент работает...\n")
        reply = agent.run(message, include_screenshot=include_screenshot)
        if reply:
            print(f"\nИИ: {reply}\n")
        print("-" * 60)
    except Exception as e:
        print(f"Ошибка: {e}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Trading Agent with Computer Use")
    parser.add_argument("--no-screenshot", action="store_true",
                        help="Не делать автоскриншот при каждом сообщении")
    parser.add_argument("--api-key", type=str, default=None,
                        help="Anthropic API key")
    args = parser.parse_args()

    try:
        agent = TradingAgentCU(api_key=args.api_key)
    except ValueError as e:
        print(f"Ошибка: {e}")
        sys.exit(1)

    run_interactive(agent, auto_screenshot=not args.no_screenshot)


if __name__ == "__main__":
    main()
