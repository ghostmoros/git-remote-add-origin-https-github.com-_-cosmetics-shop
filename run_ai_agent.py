"""AI Trading Assistant — интерактивный чат с анализом графиков.

Использование:
    python run_ai_agent.py                    # просто чат
    python run_ai_agent.py --screen           # захват экрана при каждом запросе
    python run_ai_agent.py --image chart.png  # анализ конкретного файла

Команды в чате:
    /screen          — сделать скриншот и проанализировать
    /image <путь>    — загрузить изображение для анализа
    /context <текст> — установить контекст (символ, сессия)
    /reset           — очистить историю диалога
    /help            — показать команды
    /exit или /quit  — выход
"""
from __future__ import annotations

import argparse
import sys

from bot.ai_agent.trading_assistant import TradingAssistant


HELP_TEXT = """
Доступные команды:
  /screen           — скриншот экрана → анализ
  /image <путь>     — отправить изображение ИИ
  /context <текст>  — доп. контекст (напр: "Торгую XAUUSD H1, NY сессия")
  /reset            — очистить историю диалога
  /help             — эта справка
  /exit или /quit   — выход
"""

WELCOME = """
╔══════════════════════════════════════════════════════════╗
║          AI TRADING ASSISTANT — SMC/ICT анализ          ║
╠══════════════════════════════════════════════════════════╣
║  База знаний: SMC, ICT, TA, Risk Management             ║
║  Возможности: анализ графиков, OB, FVG, Liquidity       ║
║  Введи /help для списка команд                          ║
╚══════════════════════════════════════════════════════════╝
"""


def run_interactive(assistant: TradingAssistant, default_image: str | None = None, auto_screen: bool = False) -> None:
    print(WELCOME)

    while True:
        try:
            user_input = input("Ты: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nВыход.")
            break

        if not user_input:
            continue

        # --- Commands ---
        if user_input.lower() in ("/exit", "/quit"):
            print("Выход.")
            break

        if user_input.lower() == "/help":
            print(HELP_TEXT)
            continue

        if user_input.lower() == "/reset":
            assistant.reset_conversation()
            continue

        if user_input.lower().startswith("/context "):
            ctx = user_input[9:].strip()
            assistant.set_context(ctx)
            print(f"Контекст установлен: {ctx}")
            continue

        if user_input.lower() == "/screen":
            try:
                from bot.ai_agent.screen_capture import capture_screen
                print("Делаю скриншот...")
                path = capture_screen()
                print(f"Скриншот сохранён: {path}")
                user_input = "Проанализируй этот график. Определи структуру рынка, найди OB, FVG, уровни ликвидности. Есть ли торговый сетап?"
                _send_and_print(assistant, user_input, path)
            except Exception as e:
                print(f"Ошибка скриншота: {e}")
            continue

        if user_input.lower().startswith("/image "):
            image_path = user_input[7:].strip().strip('"').strip("'")
            message = "Проанализируй этот график. Определи структуру рынка, найди OB, FVG, уровни ликвидности. Есть ли торговый сетап?"
            _send_and_print(assistant, message, image_path)
            continue

        # --- Regular message ---
        image_path = None
        if auto_screen:
            try:
                from bot.ai_agent.screen_capture import capture_screen
                image_path = capture_screen()
            except Exception:
                pass
        elif default_image:
            image_path = default_image

        _send_and_print(assistant, user_input, image_path)


def _send_and_print(assistant: TradingAssistant, message: str, image_path: str | None) -> None:
    try:
        print("\nАнализирую...\n")
        reply = assistant.analyze(message, image_path)
        print(f"ИИ: {reply}\n")
        print("-" * 60)
    except Exception as e:
        print(f"Ошибка: {e}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Trading Assistant")
    parser.add_argument("--screen", action="store_true", help="Автоматически делать скриншот при каждом запросе")
    parser.add_argument("--image", type=str, default=None, help="Путь к изображению графика")
    parser.add_argument("--api-key", type=str, default=None, help="Anthropic API key")
    args = parser.parse_args()

    try:
        assistant = TradingAssistant(api_key=args.api_key)
    except ValueError as e:
        print(f"Ошибка: {e}")
        sys.exit(1)

    run_interactive(assistant, default_image=args.image, auto_screen=args.screen)


if __name__ == "__main__":
    main()
