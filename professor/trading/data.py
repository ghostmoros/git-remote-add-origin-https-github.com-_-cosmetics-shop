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


def load_csv(path: str) -> list[Candle]:
    """Загружает реальные свечи из CSV-файла (OHLCV).

    Понимает два частых формата:
      • с заголовком: колонки open/high/low/close [+ volume] [+ time/date/unix];
      • без заголовка, в стиле дампов Binance: time,open,high,low,close,volume,...

    Если есть числовая колонка времени — строки сортируются по возрастанию
    (некоторые источники отдают данные «новые сверху»).
    """
    import csv as _csv

    def num(x):
        try:
            return float(x)
        except (TypeError, ValueError):
            return None

    with open(path, newline="") as f:
        rows = [r for r in _csv.reader(f) if r]
    if not rows:
        return []

    has_header = any(num(x) is None for x in rows[0])
    if has_header:
        head = [h.strip().lower() for h in rows[0]]

        def col(*names):
            for nm in names:
                if nm in head:
                    return head.index(nm)
            return None

        oi, hi, li, ci = col("open"), col("high"), col("low"), col("close")
        vi = col("volume", "vol", "volume btc", "volume usdt", "basevolume")
        ti = col("unix", "timestamp", "time", "open_time", "date")
        data = rows[1:]
    else:
        ti, oi, hi, li, ci, vi = 0, 1, 2, 3, 4, 5      # Binance-style без заголовка
        data = rows

    if None in (oi, hi, li, ci):
        raise ValueError("CSV: не найдены колонки open/high/low/close")

    if ti is not None and data and all(
        ti < len(r) and num(r[ti]) is not None for r in data[:5]
    ):
        data = sorted(data, key=lambda r: num(r[ti]) if ti < len(r) else 0.0)

    candles: list[Candle] = []
    for i, r in enumerate(data):
        if max(oi, hi, li, ci) >= len(r):
            continue
        o, h, l, c = num(r[oi]), num(r[hi]), num(r[li]), num(r[ci])
        if None in (o, h, l, c):
            continue
        v = num(r[vi]) if (vi is not None and vi < len(r)) else None
        candles.append(Candle(i, o, h, l, c, v if v is not None else 0.0))
    return candles
