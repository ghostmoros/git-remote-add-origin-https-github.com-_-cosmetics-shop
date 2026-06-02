"""Performance metrics + a human-readable report.

The headline number people chase is win_rate, but the ones that actually decide
whether a strategy makes money are profit_factor and expectancy. The report
prints all of them together on purpose.
"""
from __future__ import annotations

import math
from collections import Counter

import numpy as np

from bot.backtest.engine import BacktestResult


def compute(result: BacktestResult, bars_per_year: int = 252 * 24) -> dict:
    trades = result.trades
    eq = result.equity_curve.to_numpy(float)

    metrics: dict = {
        "trades": len(trades),
        "win_rate": 0.0,
        "profit_factor": 0.0,
        "expectancy_r": 0.0,
        "expectancy_cur": 0.0,
        "avg_win": 0.0,
        "avg_loss": 0.0,
        "avg_r": 0.0,
        "total_return": (result.final_balance - result.initial_balance) / result.initial_balance,
        "max_drawdown": 0.0,
        "sharpe": 0.0,
        "final_balance": result.final_balance,
        "exit_reasons": {},
    }

    if not trades:
        return metrics

    pnls = np.array([t.pnl for t in trades], dtype=float)
    r_multiples = np.array([t.r_multiple for t in trades], dtype=float)
    wins = pnls[pnls > 0]
    losses = pnls[pnls < 0]

    gross_profit = float(wins.sum())
    gross_loss = float(-losses.sum())

    metrics["win_rate"] = len(wins) / len(trades)
    metrics["profit_factor"] = (gross_profit / gross_loss) if gross_loss > 0 else math.inf
    metrics["expectancy_r"] = float(r_multiples.mean())
    metrics["expectancy_cur"] = float(pnls.mean())
    metrics["avg_win"] = float(wins.mean()) if len(wins) else 0.0
    metrics["avg_loss"] = float(losses.mean()) if len(losses) else 0.0
    metrics["avg_r"] = float(r_multiples.mean())
    metrics["exit_reasons"] = dict(Counter(t.exit_reason for t in trades))

    # Max drawdown off the equity curve.
    peak = np.maximum.accumulate(eq)
    drawdown = (eq - peak) / peak
    metrics["max_drawdown"] = float(drawdown.min())

    # Rough annualised Sharpe from per-bar equity returns.
    returns = np.diff(eq) / eq[:-1]
    if returns.std() > 0:
        metrics["sharpe"] = float(returns.mean() / returns.std() * math.sqrt(bars_per_year))

    return metrics


def format_report(strategy_name: str, metrics: dict) -> str:
    pf = metrics["profit_factor"]
    pf_str = "inf" if math.isinf(pf) else f"{pf:.2f}"
    lines = [
        "=" * 52,
        f"  BACKTEST REPORT — strategy: {strategy_name}",
        "=" * 52,
        f"  Trades            : {metrics['trades']}",
        f"  Win rate          : {metrics['win_rate'] * 100:6.2f} %",
        f"  Profit factor     : {pf_str}",
        f"  Expectancy / trade: {metrics['expectancy_r']:+.3f} R  ({metrics['expectancy_cur']:+.2f} $)",
        f"  Avg win / loss    : {metrics['avg_win']:+.2f} $ / {metrics['avg_loss']:+.2f} $",
        "-" * 52,
        f"  Total return      : {metrics['total_return'] * 100:+.2f} %",
        f"  Final balance     : {metrics['final_balance']:.2f} $",
        f"  Max drawdown      : {metrics['max_drawdown'] * 100:.2f} %",
        f"  Sharpe (annual)   : {metrics['sharpe']:.2f}",
        f"  Exits             : {metrics['exit_reasons']}",
        "=" * 52,
    ]
    if metrics["trades"]:
        if metrics["expectancy_r"] > 0:
            lines.append("  Edge looks POSITIVE — expectancy > 0. Validate on real data next.")
        else:
            lines.append("  WARNING: expectancy <= 0. High win rate but NOT profitable. Tune R:R.")
        lines.append("=" * 52)
    return "\n".join(lines)
