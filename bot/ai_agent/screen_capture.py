"""Screen capture utility — grabs the trading chart from the screen.

Requires: pip install mss pillow
"""
from __future__ import annotations

import time
from pathlib import Path


SCREENSHOT_DIR = Path("data/screenshots")


def _ensure_dir() -> None:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


def capture_screen(monitor_index: int = 1, filename: str | None = None) -> str:
    """Capture the full screen and save as PNG. Returns the saved file path."""
    try:
        import mss
        import mss.tools
    except ImportError:
        raise ImportError("Установи: pip install mss")

    _ensure_dir()
    filename = filename or f"chart_{int(time.time())}.png"
    output_path = SCREENSHOT_DIR / filename

    with mss.mss() as sct:
        monitor = sct.monitors[monitor_index]
        shot = sct.grab(monitor)
        mss.tools.to_png(shot.rgb, shot.size, output=str(output_path))

    return str(output_path)


def capture_region(left: int, top: int, width: int, height: int, filename: str | None = None) -> str:
    """Capture a specific region of the screen. Returns the saved file path."""
    try:
        import mss
        import mss.tools
    except ImportError:
        raise ImportError("Установи: pip install mss")

    _ensure_dir()
    filename = filename or f"chart_region_{int(time.time())}.png"
    output_path = SCREENSHOT_DIR / filename

    region = {"left": left, "top": top, "width": width, "height": height}
    with mss.mss() as sct:
        shot = sct.grab(region)
        mss.tools.to_png(shot.rgb, shot.size, output=str(output_path))

    return str(output_path)


def latest_screenshot() -> str | None:
    """Return path to the most recent screenshot, or None if there are none."""
    _ensure_dir()
    shots = sorted(SCREENSHOT_DIR.glob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True)
    return str(shots[0]) if shots else None
