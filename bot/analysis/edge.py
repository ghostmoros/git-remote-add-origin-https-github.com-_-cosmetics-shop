"""Does a fast feed actually predict a laggy broker feed? (lag-arbitrage test)

This handles the two-feed tick logs a lag-arbitrage bot records:

    fast_ts, broker_ts, symbol, fast_price, broker_price

`fast_price` is the quick/reference feed (e.g. MT5), `broker_price` is the venue
you actually bet on (e.g. Olymp). The premise of the whole strategy is that the
broker price *lags* the fast price, so when they diverge the broker should soon
catch up — letting you bet the direction in advance.

This module tests that premise honestly:

1. **Lag** — how stale is the broker feed (`fast_ts - broker_ts`)? No lag => no edge.
2. **The trade** — when the fast price leads the broker by more than a threshold,
   open a fixed-expiry bet that the broker moves to catch up. Trades are taken
   **non-overlapping** (you can't hold the next one until this one expires), so the
   sample is realistic, not inflated by overlapping windows.
3. **Out-of-sample** — the threshold and the best expiry horizon are picked on the
   first part of the history; the win rate is then measured on a held-out tail.
4. **Payout gate** — win pays `payout`, loss costs the stake, an unchanged broker
   price at expiry is treated generously as a refund (and we also report the
   harsher "tie = loss" number). Break-even is `1 / (1 + payout)`.

Pure numpy/pandas. A genuinely laggy, catch-up feed will show an edge here; a feed
that already moves in lock-step with the fast one will not.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

_REQUIRED = ("fast_ts", "broker_ts", "fast_price", "broker_price")
_HORIZONS = (1.0, 2.0, 3.0, 5.0)  # expiry seconds tried; best (in-sample) is kept


def load_edge_ticks(path: str) -> pd.DataFrame | None:
    """Load a two-feed tick log, or return None if it isn't one.

    Tolerant of a missing header: the known `edge_ticks` layout is
    fast_ts,broker_ts,symbol,fast_price,broker_price with no header row.
    """
    df = pd.read_csv(path)
    df.columns = [str(c).strip().lower() for c in df.columns]

    if not set(_REQUIRED).issubset(df.columns):
        # Maybe the header row is missing and pandas ate the first data row as names.
        looks_headerless = any(_is_floatish(c) for c in df.columns)
        if df.shape[1] == 5 and looks_headerless:
            df = pd.read_csv(path, header=None,
                             names=["fast_ts", "broker_ts", "symbol", "fast_price", "broker_price"])
        else:
            return None

    for c in ("fast_ts", "broker_ts", "fast_price", "broker_price"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=list(_REQUIRED)).reset_index(drop=True)
    df = df[df["fast_ts"].diff().fillna(1) >= 0]  # keep monotonic time
    return df.reset_index(drop=True) if len(df) else None


def _is_floatish(s: str) -> bool:
    try:
        float(s)
        return True
    except (TypeError, ValueError):
        return False


def _lag_stats(fast_ts: np.ndarray, broker_ts: np.ndarray) -> dict:
    lag = fast_ts - broker_ts
    lag = lag[np.isfinite(lag)]
    if not len(lag):
        return {"median": 0.0, "p90": 0.0, "max": 0.0, "share_pos": 0.0}
    return {
        "median": float(np.median(lag)),
        "p90": float(np.quantile(lag, 0.90)),
        "max": float(lag.max()),
        "share_pos": float(np.mean(lag > 0)),
    }


def _simulate(fast_ts, broker_price, d, threshold, expiry_idx, lo, hi):
    """Non-overlapping trades for entries in rows [lo, hi).

    When |fast-broker| >= threshold, bet the broker moves toward the fast price;
    settle at the precomputed expiry row, then jump past it (no overlap).
    Returns list of (entry_row, signed_move) where signed_move > 0 == correct.
    """
    trades = []
    i = lo
    while i < hi:
        j = expiry_idx[i]
        if j >= len(broker_price):
            break
        if d[i] != 0 and abs(d[i]) >= threshold:
            direction = 1.0 if d[i] > 0 else -1.0
            signed_move = (broker_price[j] - broker_price[i]) * direction
            trades.append((i, signed_move))
            i = max(j, i + 1)  # non-overlapping
        else:
            i += 1
    return trades


def _score(trades, payout: float) -> dict:
    n = len(trades)
    if not n:
        return {"n": 0, "wins": 0, "losses": 0, "ties": 0, "hit_rate": 0.0,
                "exp_refund": 0.0, "exp_tieloss": 0.0}
    moves = np.array([m for _, m in trades], dtype=float)
    wins = int(np.sum(moves > 0))
    losses = int(np.sum(moves < 0))
    ties = int(np.sum(moves == 0))
    decided = wins + losses
    return {
        "n": n,
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "hit_rate": (wins / decided) if decided else 0.0,         # excludes ties
        "exp_refund": (wins * payout - losses) / n,               # tie = money back
        "exp_tieloss": (wins * payout - (losses + ties)) / n,     # tie = lose stake
    }


def analyze_edge(df: pd.DataFrame, payout: float = 0.82, train_frac: float = 0.65,
                 threshold: float | None = None) -> dict:
    fast_ts = df["fast_ts"].to_numpy(float)
    broker_price = df["broker_price"].to_numpy(float)
    d = df["fast_price"].to_numpy(float) - broker_price
    n = len(df)
    split = int(n * train_frac)
    breakeven = 1.0 / (1.0 + payout)
    symbol = str(df["symbol"].iloc[0]) if "symbol" in df.columns and len(df) else "?"

    # Threshold from TRAIN divergences only (no peeking at the holdout).
    if threshold is None:
        nz = np.abs(d[:split])
        nz = nz[nz > 0]
        threshold = float(np.quantile(nz, 0.70)) if len(nz) else 0.0

    # Pick the expiry horizon that pays best IN-SAMPLE, judge it OUT-OF-SAMPLE.
    best = None
    for h in _HORIZONS:
        expiry_idx = np.searchsorted(fast_ts, fast_ts + h, side="left")
        trades = _simulate(fast_ts, broker_price, d, threshold, expiry_idx, 0, n)
        train = [t for t in trades if t[0] < split]
        score_tr = _score(train, payout)
        if best is None or score_tr["exp_refund"] > best["train"]["exp_refund"]:
            best = {"horizon": h, "trades": trades, "train": score_tr}

    test = [t for t in best["trades"] if t[0] >= split]
    return {
        "symbol": symbol,
        "n_rows": n,
        "span_s": float(fast_ts[-1] - fast_ts[0]) if n > 1 else 0.0,
        "lag": _lag_stats(fast_ts, df["broker_ts"].to_numpy(float)),
        "threshold": threshold,
        "payout": payout,
        "breakeven": breakeven,
        "horizon": best["horizon"],
        "train": best["train"],
        "test": _score(test, payout),
    }


def _verdict(res: dict) -> tuple[str, list[str]]:
    test, train = res["test"], res["train"]
    notes: list[str] = []

    if res["lag"]["median"] <= 0:
        notes.append("Broker feed is NOT lagging (median lag <= 0) — the whole premise is absent here.")
    if test["n"] < 100:
        notes.append(f"Only {test['n']} out-of-sample trades — too few to trust; record much more.")
    if train["hit_rate"] - test["hit_rate"] > 0.05:
        notes.append(
            f"In-sample {train['hit_rate']*100:.1f}% hit rate falls to {test['hit_rate']*100:.1f}% "
            "out-of-sample — overfitting; the lead didn't generalise."
        )

    edge = (
        test["n"] >= 100
        and res["lag"]["median"] > 0
        and test["hit_rate"] > res["breakeven"]
        and test["exp_refund"] > 0
    )
    if edge:
        verdict = "POSSIBLE EDGE — broker catches up enough to beat the payout (confirm on fresh data)"
        notes.append("Necessary, not sufficient: re-record a separate batch and re-run before risking money.")
    else:
        verdict = "NO tradeable edge — the lead does not beat the payout out-of-sample"
        if test["hit_rate"] > res["breakeven"] and res["lag"]["median"] <= 0:
            notes.append("The >break-even hit rate without any feed lag is bid/ask bounce / mean "
                         "reversion — a binary option can't capture it. Not a real edge.")

    notes.append(
        "Live, it's worse than this backtest: your click/API latency eats into the lead, the broker "
        "can widen spread, void 'suspicious' trades, re-quote at expiry, or refuse withdrawals."
    )
    return verdict, notes


def format_edge_report(label: str, res: dict) -> str:
    bar = "=" * 64
    lag, test, train = res["lag"], res["test"], res["train"]
    verdict, notes = _verdict(res)
    lines = [
        bar,
        f"  LAG-ARBITRAGE ANALYSIS — {label}",
        f"  symbol={res['symbol']}  rows={res['n_rows']}  span={res['span_s']/60:.1f} min",
        bar,
        "  FEED LAG (broker behind fast, seconds)",
        f"    median {lag['median']:.3f} | p90 {lag['p90']:.3f} | max {lag['max']:.3f} | "
        f"broker-behind {lag['share_pos']*100:.0f}% of ticks",
        "-" * 64,
        "  STRATEGY (bet broker catches up to the fast feed)",
        f"    Divergence threshold : {res['threshold']:.6f}  (price units)",
        f"    Expiry horizon       : {res['horizon']:.0f} s   (best in-sample)",
        f"    Trades train/holdout : {train['n']} / {test['n']}  (non-overlapping)",
        f"    Hit rate in-sample   : {train['hit_rate']*100:.2f} %",
        f"    Hit rate OUT-OF-SAMP : {test['hit_rate']*100:.2f} %   "
        f"(W/L/tie {test['wins']}/{test['losses']}/{test['ties']})",
        f"    Break-even @ {res['payout']*100:.0f}% payout: {res['breakeven']*100:.2f} %",
        f"    Expectancy / trade   : {test['exp_refund']:+.4f} R (tie=refund) | "
        f"{test['exp_tieloss']:+.4f} R (tie=loss)",
        "-" * 64,
        f"  VERDICT: {verdict}",
        bar,
    ]
    for note in notes:
        lines.append(f"  ! {note}")
    lines.append(bar)
    return "\n".join(lines)
