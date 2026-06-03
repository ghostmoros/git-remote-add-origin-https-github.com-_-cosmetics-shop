"""Источник рынков Polymarket: синтетика для симуляции + опциональный Gamma API."""
from __future__ import annotations

import random

from .models import PMMarket

_CATEGORIES = ["Politics", "Crypto", "Sports", "Economy", "Tech", "Culture"]
_TEMPLATES = [
    "Will {x} happen before {y}?",
    "Will {x} exceed its target by {y}?",
    "{x} to win in {y}?",
    "Will {x} be announced in {y}?",
]
_SUBJECTS = ["BTC $100k", "ETH $5k", "Fed rate cut", "Team A", "Candidate X",
             "GPT-6", "SpaceX Starship", "US recession", "New iPhone", "Solana ETF"]
_WHENS = ["2026", "Q3", "July", "this year", "the finals", "next month"]


def sample_markets(n: int, seed: int = 7) -> list[PMMarket]:
    """Генерирует n правдоподобных рынков для симуляции.

    У части рынков «честная» вероятность (fair_yes) намеренно смещена
    относительно рыночной цены — это и есть искусственные «возможности»,
    которые сканер должен найти. Детерминировано при фиксированном seed.
    """
    rng = random.Random(seed * 31 + 1)
    markets: list[PMMarket] = []
    for i in range(n):
        cat = rng.choice(_CATEGORIES)
        q = rng.choice(_TEMPLATES).format(x=rng.choice(_SUBJECTS), y=rng.choice(_WHENS))
        yes = round(rng.uniform(0.05, 0.95), 3)
        spread = rng.uniform(0.0, 0.04)                       # рыночный спред
        no = round(min(0.99, max(0.01, 1 - yes + spread)), 3)
        # иногда no дешевле, чем 1-yes → возникает арбитраж
        if rng.random() < 0.12:
            no = round(max(0.01, 1 - yes - rng.uniform(0.02, 0.08)), 3)
        vol = round(rng.uniform(500, 200000), 2)
        liq = round(vol * rng.uniform(0.05, 0.5), 2)
        # честная оценка: обычно близко к рынку, но в ~30% случаев заметно смещена
        spread_fair = rng.uniform(-0.20, 0.20) if rng.random() < 0.30 else rng.uniform(-0.03, 0.03)
        fair = round(min(0.98, max(0.02, yes + spread_fair)), 3)
        markets.append(PMMarket(f"PM-{i:03d}", q, cat, yes, no, vol, liq, fair))
    return markets


def gamma_markets(limit: int = 50, timeout: float = 8.0) -> list[PMMarket]:
    """Загружает реальные активные рынки с публичного Gamma API Polymarket.

    Может быть заблокировано сетевой политикой (403/таймаут) — вызывающий код
    должен откатиться на sample_markets().
    """
    import json
    import urllib.parse
    import urllib.request

    base = "https://gamma-api.polymarket.com/markets"
    q = urllib.parse.urlencode({"limit": limit, "active": "true", "closed": "false",
                                "order": "volume", "ascending": "false"})
    req = urllib.request.Request(f"{base}?{q}", headers={"User-Agent": "professor-bot/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode())

    out: list[PMMarket] = []
    for m in data:
        try:
            prices = m.get("outcomePrices")
            if isinstance(prices, str):
                prices = json.loads(prices)          # приходит строкой JSON
            yes, no = float(prices[0]), float(prices[1])
            out.append(PMMarket(
                str(m.get("id")),
                m.get("question", "?"),
                m.get("category") or "?",
                yes, no,
                float(m.get("volumeNum") or m.get("volume") or 0.0),
                float(m.get("liquidityNum") or m.get("liquidity") or 0.0),
                None,
            ))
        except (KeyError, IndexError, ValueError, TypeError):
            continue
    return out
