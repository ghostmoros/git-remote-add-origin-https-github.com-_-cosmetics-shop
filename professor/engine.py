"""Движок: связывает данные, стратегию и сканер. Live-режим сам откатывается на sim."""
from __future__ import annotations

from .config import Config
from .polymarket.client import gamma_markets, sample_markets
from .polymarket.models import PMMarket
from .polymarket.scanner import Opportunity, scan
from .trading.backtest import BacktestResult, run_backtest
from .trading.data import Candle, binance_klines, synthetic_candles
from .trading.strategy import DonchianBreakoutStrategy, SmaRsiStrategy
from .trading.walkforward import WalkForwardResult, walk_forward


def _load_candles(cfg: Config, symbol: str, n: int | None = None) -> tuple[list[Candle], str]:
    count = n if n is not None else cfg.trading.candles
    if cfg.mode == "live":
        try:
            return binance_klines(symbol, cfg.trading.timeframe, count), "live"
        except Exception:
            pass  # сеть заблокирована/ошибка → тихий откат на симуляцию
    start = cfg.trading.start_price.get(symbol, 100.0)
    seed = cfg.seed + sum(ord(ch) for ch in symbol)   # свой ряд на каждый символ
    return synthetic_candles(count, start, seed), "sim"


def run_trading(cfg: Config) -> tuple[list[BacktestResult], str]:
    strat = SmaRsiStrategy(
        fast=cfg.trading.fast_ma, slow=cfg.trading.slow_ma,
        rsi_period=cfg.trading.rsi_period,
        rsi_ob=cfg.trading.rsi_overbought, rsi_os=cfg.trading.rsi_oversold,
    )
    results: list[BacktestResult] = []
    source = "sim"
    for sym in cfg.trading.symbols:
        candles, source = _load_candles(cfg, sym)
        results.append(run_backtest(sym, candles, strat, cfg.capital,
                                    cfg.trading.fee_pct, cfg.trading.exposure))
    return results, source


def run_polymarket(cfg: Config) -> tuple[list[Opportunity], str]:
    source = "sim"
    markets: list[PMMarket]
    if cfg.mode == "live":
        try:
            markets = gamma_markets(cfg.polymarket.n_markets)
            source = "live"
        except Exception:
            markets = sample_markets(cfg.polymarket.n_markets, cfg.seed)
    else:
        markets = sample_markets(cfg.polymarket.n_markets, cfg.seed)
    opps = scan(markets, cfg.polymarket.min_edge, cfg.polymarket.min_volume,
                cfg.polymarket.kelly_fraction)
    return opps, source


def run_walkforward(cfg: Config) -> tuple[list[WalkForwardResult], str]:
    """Walk-forward анализ Donchian breakout по каждому символу."""
    wf = cfg.walkforward
    grid = [{"entry": e, "exit": max(5, e // 2)} for e in wf.entry_grid]

    def factory(p: dict) -> DonchianBreakoutStrategy:
        return DonchianBreakoutStrategy(entry_period=p["entry"], exit_period=p["exit"],
                                        name=f"Donchian {p['entry']}/{p['exit']}")

    results: list[WalkForwardResult] = []
    source = "sim"
    for sym in cfg.trading.symbols:
        candles, source = _load_candles(cfg, sym, wf.candles)
        results.append(walk_forward(sym, candles, factory, grid, cfg.capital,
                                    cfg.trading.fee_pct, wf.in_sample, wf.out_sample,
                                    wf.warmup))
    return results, source
