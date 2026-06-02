"""Run a strategy against a live MetaTrader 5 terminal (e.g. RoboForex).

⚠️  RUNS ON YOUR MACHINE where MT5 is installed — never in the cloud.

Safety model (deliberately conservative):
  - live.dry_run = true  -> decide and PRINT only; place no orders (default).
  - live.dry_run = false -> may place orders, but a REAL (non-demo) account is
                            still refused unless live.allow_real = true.
  Start on a DEMO account. Set credentials via environment variables
  (MT5_LOGIN / MT5_PASSWORD / MT5_SERVER) — never in the repo.

Usage (on your PC):
    pip install -r requirements.txt -r requirements-live.txt
    set MT5_LOGIN=...    &  set MT5_PASSWORD=...  &  set MT5_SERVER=RoboForex-Demo
    python run_live.py            # one decision cycle (dry-run)
    python run_live.py --loop     # repeat every live.poll_seconds
"""
from __future__ import annotations

import sys
import time

import yaml

from bot.brokers.mt5 import MT5Broker
from bot.data.indicators import atr
from bot.risk.sizing import position_size
from bot.strategies import build_strategy


def decide_and_act(broker, strategy, df, symbol, live_cfg, risk_cfg) -> None:
    signals = strategy.generate_signals(df)
    # Use the last CLOSED bar (-2); the final row is the still-forming candle.
    desired = int(signals.iloc[-2])

    positions = broker.positions(symbol)
    current = 0
    if positions:
        current = 1 if positions[0]["type"] == 0 else -1  # 0 = buy, 1 = sell

    bar_time = df.index[-1]
    print(f"[{bar_time:%Y-%m-%d %H:%M}] {symbol}: signal={desired:+d} position={current:+d}")

    if desired == 0 or desired == current:
        print("  -> no change.")
        return

    side = "buy" if desired == 1 else "sell"
    price = float(df["close"].iloc[-1])
    a = float(atr(df["high"], df["low"], df["close"], risk_cfg["atr_period"]).iloc[-1])
    stop_distance = risk_cfg["sl_atr"] * a
    if desired == 1:
        sl, tp = price - stop_distance, price + risk_cfg["tp_atr"] * a
    else:
        sl, tp = price + stop_distance, price - risk_cfg["tp_atr"] * a

    if live_cfg.get("sizing", "fixed") == "risk":
        acc = broker.account_info()
        equity = float(acc.get("equity", acc.get("balance", 0.0)))
        info = broker.symbol_info(symbol)
        risk_amount = equity * risk_cfg["risk_pct"]
        volume = position_size(
            risk_amount, stop_distance,
            info["trade_tick_value"], info["trade_tick_size"],
            info["volume_min"], info["volume_max"], info["volume_step"],
        )
        print(f"  risk-sizing: equity={equity:.2f} risk={risk_amount:.2f} "
              f"({risk_cfg['risk_pct'] * 100:.1f}%) -> {volume} lots")
    else:
        volume = float(live_cfg.get("lots", 0.01))

    if live_cfg.get("dry_run", True):
        print(f"  DRY-RUN: would {side} {volume} {symbol} @~{price:.5f} "
              f"sl={sl:.5f} tp={tp:.5f} (no order placed)")
        return

    if not broker.is_demo() and not live_cfg.get("allow_real", False):
        print("  REFUSING to trade a REAL-money account. "
              "Set live.allow_real: true to override. Aborting cycle.")
        return

    for p in positions:  # close any opposite position before reversing
        result = broker.close_position(p["ticket"])
        print(f"  closed #{p['ticket']}: retcode={result.get('retcode')}")
    result = broker.market_order(symbol, side, volume, sl=sl, tp=tp)
    print(f"  ORDER SENT: {side} {volume} {symbol} -> retcode={result.get('retcode')} "
          f"{result.get('comment', '')}")


def main(config_path: str = "config/config.yaml", loop: bool = False) -> None:
    with open(config_path) as fh:
        cfg = yaml.safe_load(fh)

    broker_cfg = cfg.get("broker", {})
    live_cfg = cfg.get("live", {})
    risk_cfg = cfg["backtest"]
    symbol = broker_cfg.get("symbol", "EURUSD")
    timeframe = broker_cfg.get("timeframe", "H1")
    count = int(broker_cfg.get("candles", 500))

    broker = MT5Broker.from_env()
    broker.connect()
    acc = broker.account_info()
    mode = "DEMO" if acc.get("trade_mode") == 0 else "REAL"
    print(f"Connected: login={acc.get('login')} server={acc.get('server')} "
          f"balance={acc.get('balance')} {acc.get('currency')}  [{mode}]")
    if mode == "REAL" and not live_cfg.get("dry_run", True):
        print("⚠️  REAL-money account + live mode. Orders gated by live.allow_real.")

    strategy = build_strategy(cfg["strategy"]["name"], cfg["strategy"].get("params"))
    print(f"Strategy: {strategy.name} | {symbol} {timeframe} | "
          f"dry_run={live_cfg.get('dry_run', True)}\n")

    try:
        while True:
            df = broker.get_candles(symbol, timeframe, count)
            decide_and_act(broker, strategy, df, symbol, live_cfg, risk_cfg)
            if not loop:
                break
            time.sleep(int(live_cfg.get("poll_seconds", 60)))
    finally:
        broker.shutdown()


if __name__ == "__main__":
    args = sys.argv[1:]
    do_loop = "--loop" in args
    paths = [a for a in args if not a.startswith("--")]
    main(paths[0] if paths else "config/config.yaml", loop=do_loop)
