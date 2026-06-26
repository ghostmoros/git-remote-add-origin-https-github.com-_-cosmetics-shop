"""Computer-use action executor for the AI trading agent.

Translates Claude's computer_use tool action blocks into real OS-level
mouse/keyboard events via pyautogui.

Requires: pip install pyautogui pillow mss
"""
from __future__ import annotations

import base64
import time
from pathlib import Path
from typing import Any

SCREENSHOT_DIR = Path("data/screenshots")


def _ensure_dir() -> None:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Screenshot helpers
# ---------------------------------------------------------------------------

def take_screenshot() -> str:
    """Capture the full screen and return base64-encoded PNG string."""
    try:
        import mss
        import mss.tools
    except ImportError:
        raise ImportError("Установи: pip install mss")

    _ensure_dir()
    filename = SCREENSHOT_DIR / f"cu_{int(time.time())}.png"

    with mss.mss() as sct:
        monitor = sct.monitors[1]
        shot = sct.grab(monitor)
        mss.tools.to_png(shot.rgb, shot.size, output=str(filename))

    with open(filename, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def get_screen_size() -> tuple[int, int]:
    """Return (width, height) of the primary monitor."""
    try:
        import mss
        with mss.mss() as sct:
            m = sct.monitors[1]
            return m["width"], m["height"]
    except ImportError:
        return 1920, 1080


# ---------------------------------------------------------------------------
# Action executor
# ---------------------------------------------------------------------------

def execute_action(action: dict[str, Any]) -> str | None:
    """Execute a single computer_use action block from Claude.

    Returns base64 PNG for 'screenshot', None for everything else.
    Raises on unknown action types.
    """
    try:
        import pyautogui
    except ImportError:
        raise ImportError("Установи: pip install pyautogui")

    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.05

    action_type: str = action.get("action", "")
    coord: list[int] | None = action.get("coordinate")
    text: str | None = action.get("text")

    if action_type == "screenshot":
        return take_screenshot()

    if action_type == "mouse_move":
        if coord:
            pyautogui.moveTo(coord[0], coord[1], duration=0.2)

    elif action_type == "left_click":
        if coord:
            pyautogui.click(coord[0], coord[1])

    elif action_type == "right_click":
        if coord:
            pyautogui.rightClick(coord[0], coord[1])

    elif action_type == "double_click":
        if coord:
            pyautogui.doubleClick(coord[0], coord[1])

    elif action_type == "left_click_drag":
        start = action.get("start_coordinate", coord)
        end = coord
        if start and end:
            pyautogui.moveTo(start[0], start[1], duration=0.2)
            pyautogui.dragTo(end[0], end[1], duration=0.3, button="left")

    elif action_type == "type":
        if text:
            pyautogui.typewrite(text, interval=0.03)

    elif action_type == "key":
        if text:
            # Claude sends keys like "ctrl+z", "Return", "super+d"
            key = text.lower().replace("return", "enter").replace("super", "win")
            pyautogui.hotkey(*key.split("+")) if "+" in key else pyautogui.press(key)

    elif action_type == "scroll":
        clicks = action.get("scroll_direction", "down")
        amount = action.get("scroll_distance", 3)
        if coord:
            pyautogui.moveTo(coord[0], coord[1])
        direction = 1 if clicks == "up" else -1
        pyautogui.scroll(direction * amount)

    else:
        raise ValueError(f"Неизвестное действие: {action_type}")

    return None
