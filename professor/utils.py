"""Мелкие помощники форматирования."""
from __future__ import annotations


def fmt_money(x: float) -> str:
    return f"${x:,.2f}"


def fmt_pct(x: float, digits: int = 2) -> str:
    return f"{x * 100:.{digits}f}%"


def fmt_signed_pct(x: float, digits: int = 2) -> str:
    return f"{x * 100:+.{digits}f}%"


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))
