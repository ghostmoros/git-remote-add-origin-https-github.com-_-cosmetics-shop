"""FastAPI web application — trading AI dashboard."""
from __future__ import annotations

import asyncio
import base64
import json
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from bot.ai_agent.market_monitor import MarketMonitor, SetupAlert
from bot.ai_agent.trading_assistant import TradingAssistant
from bot.ai_agent.computer_use import take_screenshot, get_screen_size

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="AI Trading Dashboard")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class AppState:
    def __init__(self):
        self.monitor: MonitorThread | None = None
        self.assistant: TradingAssistant | None = None
        self.alerts: list[dict] = []
        self.connections: list[WebSocket] = []
        self.monitor_running = False
        self.scan_count = 0
        self.last_scan: str = "—"
        self.last_screenshot_b64: str = ""

state = AppState()


# ---------------------------------------------------------------------------
# WebSocket broadcast
# ---------------------------------------------------------------------------

async def broadcast(msg: dict) -> None:
    dead = []
    for ws in state.connections:
        try:
            await ws.send_text(json.dumps(msg))
        except Exception:
            dead.append(ws)
    for ws in dead:
        state.connections.remove(ws)


def broadcast_sync(msg: dict) -> None:
    """Thread-safe broadcast from background threads."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(broadcast(msg), loop)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Monitor thread wrapper
# ---------------------------------------------------------------------------

class MonitorThread(threading.Thread):
    def __init__(self, interval: int, min_cf: int, context: str, api_key: str):
        super().__init__(daemon=True)
        self._stop_event = threading.Event()
        self.interval = interval
        self.min_cf = min_cf
        self.context = context
        self.api_key = api_key

    def run(self) -> None:
        monitor = MarketMonitor(
            interval=self.interval,
            min_confluences=self.min_cf,
            api_key=self.api_key,
            on_alert=self._on_alert,
        )
        if self.context:
            monitor.set_context(self.context)

        broadcast_sync({"type": "monitor_status", "running": True})

        while not self._stop_event.is_set():
            try:
                ts = datetime.now().strftime("%H:%M:%S")
                state.scan_count += 1
                state.last_scan = ts
                broadcast_sync({"type": "scan", "count": state.scan_count, "time": ts})

                b64 = monitor._capture()
                state.last_screenshot_b64 = b64
                broadcast_sync({"type": "screenshot", "data": b64})

                result = monitor._quick_scan(b64)
                if result:
                    has_setup, direction, instrument, confluences, summary = result
                    broadcast_sync({
                        "type": "quick_scan",
                        "has_setup": has_setup,
                        "direction": direction,
                        "instrument": instrument,
                        "confluences": confluences,
                        "summary": summary,
                    })
                    if has_setup and confluences >= self.min_cf:
                        if summary != monitor._last_alert_summary:
                            analysis = monitor._full_analysis(b64)
                            monitor._last_alert_summary = summary
                            alert = SetupAlert(direction, instrument, confluences, summary, analysis, ts)
                            monitor._alert_count += 1
                            self._on_alert(alert)
            except Exception as e:
                broadcast_sync({"type": "error", "message": str(e)})

            self._stop_event.wait(self.interval)

        broadcast_sync({"type": "monitor_status", "running": False})

    def stop(self) -> None:
        self._stop_event.set()

    @staticmethod
    def _on_alert(alert: SetupAlert) -> None:
        entry = {
            "timestamp": alert.timestamp,
            "direction": alert.direction,
            "instrument": alert.instrument,
            "confluences": alert.confluences,
            "summary": alert.summary,
            "analysis": alert.analysis,
        }
        state.alerts.insert(0, entry)
        if len(state.alerts) > 50:
            state.alerts.pop()
        broadcast_sync({"type": "alert", "alert": entry})


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    state.connections.append(ws)
    # Send current state to newly connected client
    await ws.send_text(json.dumps({
        "type": "init",
        "monitor_running": state.monitor_running,
        "scan_count": state.scan_count,
        "last_scan": state.last_scan,
        "alerts": state.alerts[:20],
        "screenshot": state.last_screenshot_b64,
    }))
    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            await handle_client_message(ws, msg)
    except WebSocketDisconnect:
        if ws in state.connections:
            state.connections.remove(ws)


async def handle_client_message(ws: WebSocket, msg: dict) -> None:
    action = msg.get("action")

    if action == "start_monitor":
        if state.monitor and state.monitor.is_alive():
            await ws.send_text(json.dumps({"type": "error", "message": "Мониторинг уже запущен"}))
            return
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        state.monitor = MonitorThread(
            interval=int(msg.get("interval", 60)),
            min_cf=int(msg.get("min_cf", 3)),
            context=msg.get("context", ""),
            api_key=api_key,
        )
        state.monitor.start()
        state.monitor_running = True
        state.scan_count = 0

    elif action == "stop_monitor":
        if state.monitor:
            state.monitor.stop()
            state.monitor = None
        state.monitor_running = False
        await broadcast({"type": "monitor_status", "running": False})

    elif action == "screenshot":
        try:
            b64 = take_screenshot()
            state.last_screenshot_b64 = b64
            await broadcast({"type": "screenshot", "data": b64})
        except Exception as e:
            await ws.send_text(json.dumps({"type": "error", "message": str(e)}))

    elif action == "chat":
        await handle_chat(ws, msg)

    elif action == "clear_alerts":
        state.alerts.clear()
        await broadcast({"type": "alerts_cleared"})


async def handle_chat(ws: WebSocket, msg: dict) -> None:
    text = msg.get("text", "").strip()
    if not text:
        return

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        await ws.send_text(json.dumps({"type": "error", "message": "ANTHROPIC_API_KEY не найден"}))
        return

    if state.assistant is None:
        try:
            state.assistant = TradingAssistant(api_key=api_key)
        except Exception as e:
            await ws.send_text(json.dumps({"type": "error", "message": str(e)}))
            return

    await ws.send_text(json.dumps({"type": "chat_thinking"}))

    use_screen = msg.get("use_screen", False)
    image_path: str | None = None

    if use_screen and state.last_screenshot_b64:
        # Save latest screenshot to temp file for assistant
        tmp = Path("data/screenshots/_chat_latest.png")
        tmp.parent.mkdir(parents=True, exist_ok=True)
        with open(tmp, "wb") as f:
            f.write(base64.b64decode(state.last_screenshot_b64))
        image_path = str(tmp)

    loop = asyncio.get_event_loop()
    try:
        reply = await loop.run_in_executor(
            None, state.assistant.analyze, text, image_path
        )
        await ws.send_text(json.dumps({"type": "chat_reply", "text": reply}))
    except Exception as e:
        await ws.send_text(json.dumps({"type": "error", "message": str(e)}))
