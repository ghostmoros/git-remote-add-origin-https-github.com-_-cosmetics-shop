"""Источник свечей: синтетика для симуляции + опциональная загрузка с Binance."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass


@dataclass
class Candle:
    ts: int          # индекс/время
    open: float
    high: float
    low: float
    close: float
    volume: float


def synthetic_candles(n: int, start: float, seed: int = 7,
                      drift: float = 0.0003, vol: float = 0.015) -> list[Candle]:
    """Генерирует n свечей геометрическим броуновским движением с лёгким трендом.

    Детерминировано при фиксированном seed — симуляция полностью воспроизводима.
    """
    rng = random.Random(seed)
    candles: list[Candle] = []
    price = start
    for i in range(n):
        ret = drift + vol * rng.gauss(0, 1)
        new_price = max(0.01, price * math.exp(ret))
        o, c = price, new_price
        hi = max(o, c) * (1 + abs(rng.gauss(0, vol / 2)))
        lo = min(o, c) * (1 - abs(rng.gauss(0, vol / 2)))
        v = abs(rng.gauss(1000, 300))
        candles.append(Candle(i, o, hi, lo, c, v))
        price = new_price
    return candles


def binance_klines(symbol: str, interval: str = "1h", limit: int = 500,
                   timeout: float = 8.0) -> list[Candle]:
    """Загружает реальные свечи с публичного API Binance (без ключей).

    Может быть заблокировано сетевой политикой окружения (403/таймаут) — тогда
    вызывающий код должен откатиться на synthetic_candles().
    """
    import json
    import urllib.parse
    import urllib.request

    base = "https://api.binance.com/api/v3/klines"
    q = urllib.parse.urlencode({"symbol": symbol, "interval": interval, "limit": limit})
    req = urllib.request.Request(f"{base}?{q}", headers={"User-Agent": "professor-bot/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = json.loads(resp.read().decode())
    out: list[Candle] = []
    for i, k in enumerate(raw):
        # k = [openTime, open, high, low, close, volume, ...]
        out.append(Candle(i, float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])))
    return out
