"""Core AI trading assistant powered by Claude API.

Accepts text and/or a chart screenshot, returns structured SMC analysis.
"""
from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Optional

import anthropic

from bot.ai_agent.knowledge_loader import build_system_prompt, get_knowledge_summary


class TradingAssistant:
    """Claude-powered trading assistant with full SMC/ICT knowledge."""

    MODEL = "claude-opus-4-8"
    MAX_TOKENS = 4096

    def __init__(self, api_key: str | None = None):
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise ValueError(
                "ANTHROPIC_API_KEY не найден. "
                "Установи: export ANTHROPIC_API_KEY='your-key'"
            )
        self.client = anthropic.Anthropic(api_key=key)
        self.system_prompt = build_system_prompt()
        self.conversation_history: list[dict] = []
        print(get_knowledge_summary())
        print(f"\nИИ-ассистент готов. Модель: {self.MODEL}\n")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self, message: str, image_path: str | None = None) -> str:
        """Send a message (+ optional chart screenshot) and get AI response."""
        content = self._build_content(message, image_path)
        self.conversation_history.append({"role": "user", "content": content})

        response = self.client.messages.create(
            model=self.MODEL,
            max_tokens=self.MAX_TOKENS,
            system=self.system_prompt,
            messages=self.conversation_history,
        )

        reply = response.content[0].text
        self.conversation_history.append({"role": "assistant", "content": reply})
        return reply

    def reset_conversation(self) -> None:
        """Clear conversation history — start fresh."""
        self.conversation_history = []
        print("История диалога очищена.")

    def set_context(self, extra: str) -> None:
        """Rebuild system prompt with additional context (symbol, session, news)."""
        self.system_prompt = build_system_prompt(extra_context=extra)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_content(self, message: str, image_path: str | None) -> list | str:
        if not image_path:
            return message

        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Изображение не найдено: {image_path}")

        suffix = path.suffix.lower()
        media_type_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        media_type = media_type_map.get(suffix, "image/png")

        with open(path, "rb") as f:
            image_data = base64.standard_b64encode(f.read()).decode("utf-8")

        return [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": image_data,
                },
            },
            {"type": "text", "text": message},
        ]
