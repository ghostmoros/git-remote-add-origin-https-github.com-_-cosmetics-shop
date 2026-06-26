"""Claude Computer Use agentic loop for the AI trading agent.

Claude sees the screen, controls the mouse/keyboard, and applies SMC/ICT
trading knowledge to interact with any trading platform or browser chart.

Loop:
  1. Send user message (+ current screenshot) to Claude.
  2. Claude replies with text and/or computer_use tool_use blocks.
  3. Execute each action via computer_use.execute_action().
  4. Send tool_result blocks back to Claude.
  5. Repeat until Claude emits stop_reason == "end_turn".
"""
from __future__ import annotations

import os
from typing import Any

import anthropic

from bot.ai_agent.knowledge_loader import build_system_prompt, get_knowledge_summary
from bot.ai_agent.computer_use import execute_action, get_screen_size, take_screenshot


COMPUTER_USE_BETA = "computer-use-2024-10-22"


class TradingAgentCU:
    """Computer-use powered trading agent that can see and control the screen."""

    MODEL = "claude-opus-4-8"
    MAX_TOKENS = 4096
    MAX_LOOP_STEPS = 30  # safety cap

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

        width, height = get_screen_size()
        self.computer_tool = {
            "type": "computer_20241022",
            "name": "computer",
            "display_width_px": width,
            "display_height_px": height,
            "display_number": 1,
        }

        print(get_knowledge_summary())
        print(f"\nComputer-Use агент готов. Модель: {self.MODEL}")
        print(f"Разрешение экрана: {width}×{height}\n")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, user_message: str, include_screenshot: bool = True) -> str:
        """Send a task to Claude and run the agentic loop until completion.

        Returns the final text reply from Claude.
        """
        content: list[dict] = []

        if include_screenshot:
            print("Делаю скриншот экрана...")
            b64 = take_screenshot()
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": "image/png", "data": b64},
            })

        content.append({"type": "text", "text": user_message})
        self.conversation_history.append({"role": "user", "content": content})

        return self._run_loop()

    def reset_conversation(self) -> None:
        self.conversation_history = []
        print("История диалога очищена.")

    def set_context(self, extra: str) -> None:
        self.system_prompt = build_system_prompt(extra_context=extra)

    # ------------------------------------------------------------------
    # Agentic loop
    # ------------------------------------------------------------------

    def _run_loop(self) -> str:
        """Drive the tool-use loop until end_turn or step cap."""
        final_text = ""

        for step in range(self.MAX_LOOP_STEPS):
            response = self.client.beta.messages.create(
                model=self.MODEL,
                max_tokens=self.MAX_TOKENS,
                system=self.system_prompt,
                tools=[self.computer_tool],
                messages=self.conversation_history,
                betas=[COMPUTER_USE_BETA],
            )

            # Collect assistant message
            assistant_blocks: list[dict] = []
            tool_uses: list[dict] = []

            for block in response.content:
                if block.type == "text":
                    final_text = block.text
                    assistant_blocks.append({"type": "text", "text": block.text})
                    if block.text:
                        print(f"\n[ИИ — шаг {step + 1}]: {block.text}\n")

                elif block.type == "tool_use":
                    tool_uses.append(block)
                    assistant_blocks.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })

            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_blocks,
            })

            if response.stop_reason == "end_turn" or not tool_uses:
                break

            # Execute tools and collect results
            tool_results = self._execute_tools(tool_uses)
            self.conversation_history.append({
                "role": "user",
                "content": tool_results,
            })

        return final_text

    def _execute_tools(self, tool_uses: list[Any]) -> list[dict]:
        results: list[dict] = []

        for tool in tool_uses:
            action = tool.input
            action_type = action.get("action", "?")
            print(f"  → Выполняю: {action_type} {action.get('coordinate', action.get('text', ''))}")

            try:
                screenshot_b64 = execute_action(action)

                if screenshot_b64:
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": tool.id,
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": screenshot_b64,
                                },
                            }
                        ],
                    })
                else:
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": tool.id,
                        "content": "OK",
                    })

            except Exception as exc:
                print(f"  ✗ Ошибка действия '{action_type}': {exc}")
                results.append({
                    "type": "tool_result",
                    "tool_use_id": tool.id,
                    "is_error": True,
                    "content": str(exc),
                })

        return results
