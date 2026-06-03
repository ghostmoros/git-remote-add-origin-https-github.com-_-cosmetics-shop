"""Текстовые отчёты для консоли."""
from __future__ import annotations

from .polymarket.scanner import Opportunity
from .trading.backtest import BacktestResult
from .utils import fmt_money, fmt_pct, fmt_signed_pct


def render_trading(results: list[BacktestResult], start_equity: float) -> str:
    lines = ["📈 КРИПТО-ТРЕЙДИНГ (симуляция, paper trading)", "─" * 66]
    lines.append(f"{'Символ':<10}{'Сделок':>8}{'Винрейт':>10}{'PF':>8}"
                 f"{'Доход':>11}{'Просадка':>11}")
    lines.append("─" * 66)
    total_final = 0.0
    for r in results:
        s = r.stats
        pf = "∞" if s.profit_factor == float("inf") else f"{s.profit_factor:.2f}"
        lines.append(f"{r.symbol:<10}{s.n_trades:>8}{fmt_pct(s.win_rate):>10}{pf:>8}"
                     f"{fmt_signed_pct(s.total_return):>11}{fmt_pct(s.max_drawdown):>11}")
        total_final += s.final_equity
    lines.append("─" * 66)
    invested = start_equity * len(results)
    if invested:
        pnl = total_final - invested
        lines.append(f"Итог: вложено {fmt_money(invested)} → стало "
                     f"{fmt_money(total_final)} ({fmt_signed_pct(pnl / invested)})")
    return "\n".join(lines)


def render_polymarket(opps: list[Opportunity], max_results: int = 12) -> str:
    lines = ["🎲 POLYMARKET — НАЙДЕННЫЕ ВОЗМОЖНОСТИ", "─" * 78]
    if not opps:
        lines.append("Возможностей по заданным фильтрам не найдено.")
        return "\n".join(lines)
    lines.append(f"{'Тип':<11}{'Сторона':>8}{'Цена':>7}{'Честн.':>8}"
                 f"{'Edge':>8}{'EV/$':>8}{'Kelly':>7}  Вопрос")
    lines.append("─" * 78)
    for o in opps[:max_results]:
        q = o.market.question
        q = (q[:38] + "…") if len(q) > 39 else q
        lines.append(f"{o.kind:<11}{o.side:>8}{o.price:>7.3f}{o.fair_prob:>8.3f}"
                     f"{fmt_pct(o.edge, 1):>8}{fmt_pct(o.ev_per_dollar, 1):>8}"
                     f"{fmt_pct(o.kelly, 1):>7}  {q}")
    lines.append("─" * 78)
    shown = min(max_results, len(opps))
    lines.append(f"Всего возможностей: {len(opps)} (показаны топ-{shown} по EV на $1)")
    return "\n".join(lines)
