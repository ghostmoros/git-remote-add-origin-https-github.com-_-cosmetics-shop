"""Настройки «Профессора». Меняй значения здесь, чтобы управлять поведением бота."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TradingConfig:
    """Параметры крипто-трейдинга."""

    symbols: list[str] = field(default_factory=lambda: ["BTCUSDT", "ETHUSDT", "SOLUSDT"])
    candles: int = 500            # сколько свечей анализировать
    timeframe: str = "1h"
    start_price: dict = field(default_factory=lambda: {
        "BTCUSDT": 65000.0, "ETHUSDT": 3200.0, "SOLUSDT": 150.0,
    })
    fee_pct: float = 0.04         # комиссия за сделку, % (тейкер ~0.04%)
    # стратегия SMA-cross + RSI-фильтр
    fast_ma: int = 20
    slow_ma: int = 50
    rsi_period: int = 14
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0
    exposure: float = 0.95        # какая доля капитала идёт в позицию


@dataclass
class PolymarketConfig:
    """Параметры сканера возможностей Polymarket."""

    n_markets: int = 50           # сколько рынков просканировать
    min_volume: float = 5000.0    # фильтр ликвидности, $
    min_edge: float = 0.05        # минимальное преимущество (5 п.п.)
    kelly_fraction: float = 0.25  # доля Келли (1/4 Kelly — консервативно)
    max_results: int = 12


@dataclass
class WalkForwardConfig:
    """Параметры walk-forward анализа (Donchian breakout)."""

    candles: int = 1000           # длиннее основного прогона — нужно много окон
    in_sample: int = 300          # окно оптимизации (train)
    out_sample: int = 120         # окно проверки (test, out-of-sample)
    warmup: int = 60              # прогрев индикаторов перед каждым OOS-окном
    entry_grid: list = field(default_factory=lambda: [15, 20, 30, 40, 55])


@dataclass
class Config:
    """Корневая конфигурация."""

    mode: str = "sim"             # "sim" — симуляция; "live" — реальные публичные API
    csv_path: str | None = None   # путь к CSV с реальными свечами (--csv); важнее mode
    seed: int = 7                 # фиксируем для воспроизводимости симуляции
    capital: float = 1000.0       # стартовый капитал на символ, USDT
    trading: TradingConfig = field(default_factory=TradingConfig)
    polymarket: PolymarketConfig = field(default_factory=PolymarketConfig)
    walkforward: WalkForwardConfig = field(default_factory=WalkForwardConfig)
