"""Web dashboard entry point.

Использование:
    python run_web.py             # localhost:8000
    python run_web.py --port 8080
    python run_web.py --host 0.0.0.0 --port 8000  # доступен в локальной сети
"""
from __future__ import annotations

import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Trading Web Dashboard")
    parser.add_argument("--host", default="127.0.0.1", help="Хост (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Порт (default: 8000)")
    args = parser.parse_args()

    try:
        import uvicorn
    except ImportError:
        print("Установи: pip install uvicorn")
        sys.exit(1)

    print(f"\n Открой в браузере: http://{args.host}:{args.port}\n")
    uvicorn.run(
        "bot.web.app:app",
        host=args.host,
        port=args.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
