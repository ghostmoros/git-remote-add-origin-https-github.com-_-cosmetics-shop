"""Continuous market monitor — watches the screen and alerts on trading setups.

Loop:
  1. Capture screen every `interval` seconds.
  2. Quick scan: ask Claude if anything notable changed.
  3. If yes → full SMC analysis and alert.
  4. Repeat until Ctrl+C.
"""
from __future__ import annotations

import os
import time
from datetime import datetime
from typing import Callable

import anthropic

from bot.ai_agent.knowledge_loader import build_system_prompt
from bot.ai_agent.computer_use import take_screenshot, get_screen_size


QUICK_SCAN_PROMPT = """Look at this trading chart screenshot.

Answer ONLY in this exact format (nothing else):
SETUP: YES or NO
DIRECTION: BUY or SELL or NONE
INSTRUMENT: symbol or UNKNOWN
CONFLUENCES: number (0-10)
SUMMARY: one short sentence

A setup is valid only if there are 3+ confluences (OB + FVG + Liquidity + Kill Zone etc.)."""

FULL_ANALYSIS_PROMPT = """You are an expert SMC/ICT trading analyst. Analyze this chart in full detail.

Provide:
1. **Instrument & Timeframe**: what you see
2. **Market Structure**: trend, last BOS/CHoCH
3. **Key Zones**: Order Blocks, FVGs, Liquidity levels with approximate prices
4. **THE SETUP**: Entry price, Stop Loss, Take Profit, Risk:Reward
5. **Confluences** (list each one)
6. **Probability**: High / Medium / Low — and why
7. **What NOT to do**: key risks

Be specific with price levels. If no setup exists, say so clearly."""


class SetupAlert:
    def __init__(self, direction: str, instrument: str, confluences: int, summary: str, analysis: str, timestamp: str):
        self.direction = direction
        self.instrument = instrument
        self.confluences = confluences
        self.summary = summary
        self.analysis = analysis
        self.timestamp = timestamp


class MarketMonitor:
    """Continuously watches the screen and alerts when a trading setup appears."""

    QUICK_MODEL = "claude-opus-4-8"
    ANALYSIS_MODEL = "claude-opus-4-8"
    MAX_TOKENS_QUICK = 200
    MAX_TOKENS_ANALYSIS = 2048

    def __init__(
        self,
        interval: int = 60,
        min_confluences: int = 3,
        api_key: str | None = None,
        on_alert: Callable[[SetupAlert], None] | None = None,
        region: dict | None = None,
    ):
        """
        Args:
            interval: seconds between each screen check
            min_confluences: minimum confluences to trigger alert
            api_key: Anthropic API key
            on_alert: callback called with SetupAlert when setup found
            region: optional screen region dict {left, top, width, height}
        """
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise ValueError("ANTHROPIC_API_KEY не найден.")
        self.client = anthropic.Anthropic(api_key=key)
        self.system_prompt = build_system_prompt()
        self.interval = interval
        self.min_confluences = min_confluences
        self.on_alert = on_alert or self._default_alert
        self.region = region
        self._last_alert_summary: str = ""
        self._scan_count = 0
        self._alert_count = 0

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Start the monitoring loop. Blocks until KeyboardInterrupt."""
        w, h = get_screen_size()
        print(f"\n Мониторинг запущен. Экран: {w}×{h}")
        print(f" Интервал: каждые {self.interval} сек | Мин. confluences: {self.min_confluences}")
        print(" Для остановки нажми Ctrl+C\n")
        print("─" * 60)

        while True:
            try:
                self._tick()
                time.sleep(self.interval)
            except KeyboardInterrupt:
                print(f"\n Мониторинг остановлен. Сканов: {self._scan_count} | Алертов: {self._alert_count}")
                break
            except Exception as e:
                print(f"[{self._now()}] Ошибка скана: {e}")
                time.sleep(self.interval)

    def set_context(self, extra: str) -> None:
        self.system_prompt = build_system_prompt(extra_context=extra)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _tick(self) -> None:
        self._scan_count += 1
        ts = self._now()
        print(f"[{ts}] Скан #{self._scan_count}...", end=" ", flush=True)

        b64 = self._capture()
        result = self._quick_scan(b64)

        if result is None:
            print("ошибка парсинга ответа")
            return

        has_setup, direction, instrument, confluences, summary = result

        if not has_setup or confluences < self.min_confluences:
            print(f"нет сетапа ({confluences} confluences)")
            return

        # Avoid re-alerting the same setup
        if summary == self._last_alert_summary:
            print(f"сетап уже отправлен ({confluences}cf)")
            return

        print(f"СЕТАП! {direction} {instrument} [{confluences} confluences]")
        print(f"[{ts}] Запускаю полный анализ...")

        analysis = self._full_analysis(b64)
        self._last_alert_summary = summary
        self._alert_count += 1

        alert = SetupAlert(
            direction=direction,
            instrument=instrument,
            confluences=confluences,
            summary=summary,
            analysis=analysis,
            timestamp=ts,
        )
        self.on_alert(alert)

    def _capture(self) -> str:
        """Capture screen or region, return base64 PNG."""
        if self.region:
            from bot.ai_agent.computer_use import take_screenshot as ts_full
            import mss
            import mss.tools
            import base64
            from pathlib import Path
            import time as t

            out = Path("data/screenshots") / f"mon_{int(t.time())}.png"
            out.parent.mkdir(parents=True, exist_ok=True)
            with mss.mss() as sct:
                shot = sct.grab(self.region)
                mss.tools.to_png(shot.rgb, shot.size, output=str(out))
            with open(out, "rb") as f:
                import base64 as b64m
                return b64m.standard_b64encode(f.read()).decode()
        return take_screenshot()

    def _quick_scan(self, b64: str) -> tuple[bool, str, str, int, str] | None:
        """Fast check: is there a setup? Returns (has_setup, direction, instrument, confluences, summary)."""
        try:
            response = self.client.messages.create(
                model=self.QUICK_MODEL,
                max_tokens=self.MAX_TOKENS_QUICK,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}},
                        {"type": "text", "text": QUICK_SCAN_PROMPT},
                    ],
                }],
            )
            text = response.content[0].text.strip()
            return self._parse_quick(text)
        except Exception as e:
            print(f"quick_scan error: {e}")
            return None

    def _parse_quick(self, text: str) -> tuple[bool, str, str, int, str] | None:
        lines = {
            k.strip(): v.strip()
            for line in text.splitlines()
            if ":" in line
            for k, v in [line.split(":", 1)]
        }
        try:
            has_setup = lines.get("SETUP", "NO").upper() == "YES"
            direction = lines.get("DIRECTION", "NONE").upper()
            instrument = lines.get("INSTRUMENT", "UNKNOWN")
            confluences = int(lines.get("CONFLUENCES", "0"))
            summary = lines.get("SUMMARY", "")
            return has_setup, direction, instrument, confluences, summary
        except Exception:
            return None

    def _full_analysis(self, b64: str) -> str:
        """Deep SMC analysis of the chart."""
        try:
            response = self.client.messages.create(
                model=self.ANALYSIS_MODEL,
                max_tokens=self.MAX_TOKENS_ANALYSIS,
                system=self.system_prompt,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}},
                        {"type": "text", "text": FULL_ANALYSIS_PROMPT},
                    ],
                }],
            )
            return response.content[0].text.strip()
        except Exception as e:
            return f"Ошибка анализа: {e}"

    @staticmethod
    def _default_alert(alert: SetupAlert) -> None:
        border = "═" * 60
        print(f"\n\n{'🚨' * 5}  СЕТАП НАЙДЕН  {'🚨' * 5}")
        print(border)
        print(f" Время:       {alert.timestamp}")
        print(f" Инструмент:  {alert.instrument}")
        print(f" Направление: {alert.direction}")
        print(f" Confluences: {alert.confluences}")
        print(f" Кратко:      {alert.summary}")
        print(border)
        print(alert.analysis)
        print(border)
        print()
        # Terminal bell
        print("\a", end="", flush=True)

    @staticmethod
    def _now() -> str:
        return datetime.now().strftime("%H:%M:%S")
