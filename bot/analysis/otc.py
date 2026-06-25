"""Is a synthetic ("OTC") price feed predictable, or just a random generator?

Binary-options brokers price their weekend / OTC assets with an *internal*
generator instead of a real market. The only rational reason to record OTC ticks
is to ask one question honestly:

    Does the generator leave a footprint we can exploit to predict the next move
    better than the payout break-even — and does that edge SURVIVE on data we did
    not look at while searching?

This module answers that with three things:

1. **Randomness tests** (runs test, autocorrelation, Markov conditionals,
   distribution shape) — is the up/down sequence distinguishable from a coin?
2. **An out-of-sample predictor** — learn the best short-memory rule on the FIRST
   part of the history, then measure its accuracy on a held-out tail it never
   saw. The gap between in-sample and out-of-sample accuracy *is* the overfitting.
3. **A payout gate** — a binary option only pays `payout` on a win and costs the
   whole stake on a loss, so you must be right more than `1 / (1 + payout)` of the
   time just to break even (payout 0.82 -> 54.95 %). Accuracy below that line is
   worthless no matter how "significant" a test looks.

Pure numpy/pandas — no scipy — so it runs anywhere the rest of the bot does.
Nothing here predicts the future; it only tells you whether the past contained a
repeatable, tradeable footprint. A clean random generator will (correctly) come
back as "no edge".
"""
from __future__ import annotations

import math
from collections import defaultdict
from statistics import NormalDist

import numpy as np
import pandas as pd

# Column names we'll accept for the timestamp and the price of a tick row.
_TIME_COLS = ("time", "date", "datetime", "timestamp")
_PRICE_COLS = ("price", "close", "last", "mid", "broker_price", "bid", "ask")


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #
def load_ticks(path: str) -> pd.Series:
    """Load a tick/price CSV into a price Series.

    Flexible on purpose — a bot's tick log rarely has tidy OHLC columns. We
    auto-detect the price column from `price/close/last/mid/bid/ask` (averaging
    bid+ask if both exist and there's no explicit mid/price) and a timestamp from
    `time/date/datetime/timestamp`. If there is no time column we fall back to
    row order, which is all the randomness tests actually need.
    """
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]

    price = _pick_price(df)

    time_col = next((c for c in _TIME_COLS if c in df.columns), None)
    if time_col is not None:
        idx = pd.to_datetime(df[time_col], errors="coerce")
        price = price[idx.notna()]
        price.index = idx[idx.notna()]
        price = price.sort_index()
    else:
        price.index = pd.RangeIndex(len(price))

    price = pd.to_numeric(price, errors="coerce").dropna()
    price.name = "price"
    return price


def _pick_price(df: pd.DataFrame) -> pd.Series:
    for col in _PRICE_COLS:
        if col in df.columns:
            return df[col].copy()
    if "bid" in df.columns and "ask" in df.columns:
        return (df["bid"] + df["ask"]) / 2.0
    raise ValueError(
        f"CSV must contain a price column (one of {list(_PRICE_COLS)}); got {list(df.columns)}"
    )


def to_directions(price: pd.Series) -> np.ndarray:
    """Price -> sequence of up(1)/down(0) moves, with flat ticks dropped.

    Flat ticks carry no directional information and would bias every test toward
    "structure", so we remove them rather than bucket them arbitrarily.
    """
    diff = np.diff(price.to_numpy(dtype=float))
    diff = diff[diff != 0.0]
    return (diff > 0).astype(int)


# --------------------------------------------------------------------------- #
# Small stats helpers (hand-rolled so we need no scipy)
# --------------------------------------------------------------------------- #
def _norm_sf(z: float) -> float:
    """One-sided survival function P(Z > z) for a standard normal."""
    return 0.5 * math.erfc(z / math.sqrt(2))


def _two_sided_p(z: float) -> float:
    return 2.0 * _norm_sf(abs(z))


def runs_test(directions: np.ndarray) -> dict:
    """Wald–Wolfowitz runs test: are up/down streaks consistent with a coin?

    Too few runs => trends/momentum; too many => mean reversion. Either is
    structure. p < 0.05 means the sequence is unlikely to be i.i.d. coin flips.
    """
    n = len(directions)
    n1 = int(directions.sum())          # ups
    n2 = n - n1                          # downs
    if n1 == 0 or n2 == 0 or n < 2:
        return {"runs": n, "expected": float(n), "z": 0.0, "p_value": 1.0, "n": n}

    runs = 1 + int(np.sum(directions[1:] != directions[:-1]))
    expected = 2.0 * n1 * n2 / n + 1.0
    var = (2.0 * n1 * n2 * (2.0 * n1 * n2 - n)) / (n * n * (n - 1.0))
    z = (runs - expected) / math.sqrt(var) if var > 0 else 0.0
    return {"runs": runs, "expected": expected, "z": z, "p_value": _two_sided_p(z), "n": n}


def autocorrelation(x: np.ndarray, max_lag: int = 10) -> list[dict]:
    """ACF of a series at lags 1..max_lag with a ±1.96/sqrt(n) significance band.

    Run it on the *returns* (do moves repeat in size?) and on the *signed
    directions* (do ups follow ups?). Significant lags = a memory you might trade.
    """
    x = np.asarray(x, dtype=float)
    n = len(x)
    x = x - x.mean()
    denom = float(np.sum(x * x))
    # Bonferroni-correct the 95% band for the number of lags we test, so a few
    # spurious hits don't get flagged just because we looked at many lags at once.
    alpha = 0.05 / max(1, max_lag)
    band = NormalDist().inv_cdf(1 - alpha / 2) / math.sqrt(n) if n > 0 else math.inf
    out = []
    for lag in range(1, min(max_lag, n - 1) + 1):
        acf = float(np.sum(x[lag:] * x[:-lag]) / denom) if denom > 0 else 0.0
        out.append({"lag": lag, "acf": acf, "significant": abs(acf) > band})
    return out


def markov_conditionals(directions: np.ndarray, k: int) -> list[dict]:
    """For every pattern of the last `k` moves, P(next = up) and its sample size.

    A fair generator pins every conditional near 0.5. A big, well-sampled
    deviation is the kind of thing a predictor could (in-sample) exploit.
    """
    counts: dict[tuple, list[int]] = defaultdict(lambda: [0, 0])  # [down, up]
    for t in range(k, len(directions)):
        pat = tuple(int(v) for v in directions[t - k:t])
        counts[pat][int(directions[t])] += 1
    rows = []
    for pat, (down, up) in sorted(counts.items()):
        total = down + up
        rows.append({"pattern": pat, "p_up": up / total, "count": total})
    return rows


def distribution_stats(price: pd.Series) -> dict:
    """Shape of the tick returns + a lag-1 mean-reversion proxy.

    `ar1` is the lag-1 autocorrelation of returns: < 0 hints mean reversion,
    > 0 hints momentum. It's a proxy, not a full ADF test — read it alongside the
    runs test, don't lean on it alone.
    """
    r = np.diff(price.to_numpy(dtype=float))
    r = r[np.isfinite(r)]
    if len(r) < 3:
        return {"n_returns": len(r), "mean": 0.0, "std": 0.0, "skew": 0.0, "kurtosis": 0.0, "ar1": 0.0}
    mean = float(r.mean())
    d = r - mean
    m2 = float(np.mean(d ** 2))
    std = math.sqrt(m2)
    skew = float(np.mean(d ** 3) / m2 ** 1.5) if m2 > 0 else 0.0
    kurt = float(np.mean(d ** 4) / m2 ** 2 - 3.0) if m2 > 0 else 0.0
    ar1 = float(np.corrcoef(r[:-1], r[1:])[0, 1]) if m2 > 0 else 0.0
    return {"n_returns": len(r), "mean": mean, "std": std, "skew": skew, "kurtosis": kurt, "ar1": ar1}


# --------------------------------------------------------------------------- #
# Out-of-sample predictor (the part that actually matters)
# --------------------------------------------------------------------------- #
def _learn_table(directions: np.ndarray, k: int) -> dict[tuple, tuple[float, int]]:
    """pattern(last k) -> (P(up), count) estimated from `directions`."""
    counts: dict[tuple, list[int]] = defaultdict(lambda: [0, 0])
    for t in range(k, len(directions)):
        pat = tuple(int(v) for v in directions[t - k:t])
        counts[pat][int(directions[t])] += 1
    return {pat: (up / (down + up), down + up) for pat, (down, up) in counts.items()}


def _apply_table(
    table: dict[tuple, tuple[float, int]],
    directions: np.ndarray,
    k: int,
    default: int,
    conf: float = 0.0,
    min_count: int = 1,
) -> tuple[float, int]:
    """Predict each move from the preceding `k`; return (accuracy, n_predicted).

    `conf`/`min_count` enable *selective* betting: only predict when the learned
    pattern leaned far enough from 50/50 (|p_up-0.5| >= conf) on enough samples.
    Unseen / low-confidence patterns are skipped (or use `default` when conf==0).
    """
    correct = total = 0
    for t in range(k, len(directions)):
        pat = tuple(int(v) for v in directions[t - k:t])
        if pat in table:
            p_up, cnt = table[pat]
            if cnt < min_count or abs(p_up - 0.5) < conf:
                continue
            pred = 1 if p_up >= 0.5 else 0
        elif conf > 0.0:
            continue
        else:
            pred = default
        correct += int(pred == directions[t])
        total += 1
    return (correct / total if total else 0.0, total)


def oos_predictor(
    directions: np.ndarray,
    payout: float = 0.82,
    max_k: int = 3,
    train_frac: float = 0.65,
    conf: float = 0.05,
    min_count: int = 20,
) -> dict:
    """Learn the best memory-`k` rule in-sample, judge it out-of-sample.

    Returns in-sample vs out-of-sample accuracy, a selective (high-confidence)
    variant with its coverage, the break-even line and the resulting per-trade
    expectancy in R (stake = 1: win -> +payout, loss -> -1).
    """
    n = len(directions)
    split = int(n * train_frac)
    train, hold = directions[:split], directions[split:]
    base_default = 1 if (len(train) and train.mean() >= 0.5) else 0
    breakeven = 1.0 / (1.0 + payout)

    best = None
    for k in range(1, max_k + 1):
        if len(train) <= k + 1 or len(hold) <= k + 1:
            continue
        table = _learn_table(train, k)
        in_acc, _ = _apply_table(table, train, k, base_default)
        if best is None or in_acc > best["in_sample_acc"]:
            best = {"k": k, "table": table, "in_sample_acc": in_acc}

    if best is None:
        return {"ok": False, "reason": "not enough data to split", "breakeven": breakeven}

    k, table = best["k"], best["table"]
    oos_acc, oos_n = _apply_table(table, hold, k, base_default)
    sel_acc, sel_n = _apply_table(table, hold, k, base_default, conf=conf, min_count=min_count)
    exp_all = oos_acc * payout - (1 - oos_acc)
    exp_sel = sel_acc * payout - (1 - sel_acc)
    return {
        "ok": True,
        "k": k,
        "payout": payout,
        "breakeven": breakeven,
        "in_sample_acc": best["in_sample_acc"],
        "oos_acc": oos_acc,
        "oos_n": oos_n,
        "selective_acc": sel_acc,
        "selective_n": sel_n,
        "selective_coverage": sel_n / max(1, len(hold) - k),
        "expectancy_all_r": exp_all,
        "expectancy_selective_r": exp_sel,
        "train_n": len(train),
        "hold_n": len(hold),
        "conf": conf,
        "min_count": min_count,
    }


# --------------------------------------------------------------------------- #
# Orchestration + report
# --------------------------------------------------------------------------- #
MIN_TICKS = 5000  # below this any verdict is statistically shaky


def analyze(price: pd.Series, payout: float = 0.82, max_lag: int = 10, max_k: int = 3) -> dict:
    directions = to_directions(price)
    return {
        "n_ticks": len(price),
        "n_moves": len(directions),
        "up_rate": float(directions.mean()) if len(directions) else 0.0,
        "runs": runs_test(directions),
        "acf_returns": autocorrelation(np.diff(price.to_numpy(float)), max_lag),
        "acf_direction": autocorrelation(directions * 2 - 1, max_lag),
        "markov_k1": markov_conditionals(directions, 1),
        "distribution": distribution_stats(price),
        "predictor": oos_predictor(directions, payout=payout, max_k=max_k),
    }


def _verdict(res: dict) -> tuple[str, list[str]]:
    """Turn the numbers into a plain-language call plus the reasons behind it."""
    notes: list[str] = []
    pred = res["predictor"]
    runs = res["runs"]
    # Only treat low-lag, clearly-above-band autocorrelation as real "structure"
    # (a single global test at p<0.01, or a short-memory ACF that's not marginal).
    strong_dir = [a for a in res["acf_direction"]
                  if a["significant"] and a["lag"] <= 3 and abs(a["acf"]) > 0.02]

    structured = runs.get("p_value", 1.0) < 0.01 or bool(strong_dir)
    edge = (
        pred.get("ok")
        and pred["selective_n"] > 0
        and pred["selective_coverage"] > 0.02
        and pred["selective_acc"] > pred["breakeven"]
        and pred["expectancy_selective_r"] > 0
    )

    if res["n_moves"] < MIN_TICKS:
        notes.append(
            f"Only {res['n_moves']} moves — below {MIN_TICKS}. Treat everything below as "
            "INCONCLUSIVE; collect more ticks before trusting any verdict."
        )

    if pred.get("ok") and pred["in_sample_acc"] - pred["oos_acc"] > 0.03:
        notes.append(
            f"In-sample {pred['in_sample_acc']*100:.1f}% collapses to {pred['oos_acc']*100:.1f}% "
            "out-of-sample — classic overfitting; the 'pattern' did not generalise."
        )

    if edge:
        verdict = "POSSIBLE EDGE — confirm on MORE out-of-sample data before risking money"
        notes.append(
            "A high-confidence subset beat break-even out-of-sample. This is necessary but NOT "
            "sufficient: re-run on a fresh, separately-collected batch. One holdout can get lucky."
        )
    elif structured:
        verdict = "STRUCTURE detected, but NO tradeable edge after the payout gate"
        notes.append(
            "The sequence isn't a perfect coin, but the deviation doesn't clear the payout "
            "break-even out-of-sample — not profitable."
        )
    else:
        verdict = "NO exploitable edge — indistinguishable from a random generator"

    notes.append(
        "Even a real edge can be neutralised: the broker can reseed/alter the generator, void "
        "'suspicious' trades, or refuse withdrawals. Demo-only until proven, and never bet money "
        "you can't lose."
    )
    return verdict, notes


def format_report(label: str, res: dict) -> str:
    bar = "=" * 64
    pred = res["predictor"]
    dist = res["distribution"]
    runs = res["runs"]
    verdict, notes = _verdict(res)

    sig_ret = [a["lag"] for a in res["acf_returns"] if a["significant"]]
    sig_dir = [a["lag"] for a in res["acf_direction"] if a["significant"]]

    lines = [
        bar,
        f"  OTC FEED ANALYSIS — {label}",
        bar,
        f"  Ticks / non-flat moves : {res['n_ticks']} / {res['n_moves']}",
        f"  Up-move rate           : {res['up_rate']*100:.2f} %   (coin = 50.00 %)",
        "-" * 64,
        "  RANDOMNESS",
        f"    Runs test            : runs={runs['runs']} exp={runs['expected']:.0f} "
        f"z={runs['z']:+.2f} p={runs['p_value']:.4f}"
        f"  {'<-- non-random' if runs['p_value'] < 0.05 else '(consistent with random)'}",
        f"    ACF returns  (sig)   : {sig_ret if sig_ret else 'none'}",
        f"    ACF direction(sig)   : {sig_dir if sig_dir else 'none'}",
        f"    Return skew/kurtosis : {dist['skew']:+.3f} / {dist['kurtosis']:+.3f}",
        f"    Mean-revert proxy ar1: {dist['ar1']:+.3f}  "
        f"({'mean-reverting' if dist['ar1'] < -0.02 else 'momentum' if dist['ar1'] > 0.02 else 'none'})",
        "-" * 64,
        "  PREDICTABILITY (out-of-sample is the one that counts)",
    ]
    if pred.get("ok"):
        lines += [
            f"    Memory k chosen      : {pred['k']}   (train {pred['train_n']} / holdout {pred['hold_n']} moves)",
            f"    Accuracy in-sample   : {pred['in_sample_acc']*100:.2f} %",
            f"    Accuracy OUT-OF-SAMP : {pred['oos_acc']*100:.2f} %   (all {pred['oos_n']} moves)",
            f"    Selective (hi-conf)  : {pred['selective_acc']*100:.2f} %  "
            f"on {pred['selective_n']} bets ({pred['selective_coverage']*100:.1f}% coverage)",
            f"    Break-even @ {pred['payout']*100:.0f}% payout: {pred['breakeven']*100:.2f} %",
            f"    Expectancy / trade   : all {pred['expectancy_all_r']:+.4f} R | "
            f"selective {pred['expectancy_selective_r']:+.4f} R",
        ]
    else:
        lines.append(f"    (skipped: {pred.get('reason', 'n/a')})")
    lines += ["-" * 64, f"  VERDICT: {verdict}", bar]
    for note in notes:
        lines.append(f"  ! {note}")
    lines.append(bar)
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Self-test — proves the instrument works before you trust it on real data
# --------------------------------------------------------------------------- #
def _series_from_directions(dirs: np.ndarray, start: float = 1.30) -> pd.Series:
    """Rebuild a price path from up/down moves so the full pipeline gets exercised."""
    steps = np.where(dirs > 0, 1.0, -1.0) * 1e-5
    return pd.Series(start + np.cumsum(np.concatenate([[0.0], steps])), name="price")


def selftest(n: int = 40000, seed: int = 7, payout: float = 0.82) -> bool:
    """Random feed must read 'no edge'; a rigged momentum feed must be caught."""
    rng = np.random.default_rng(seed)

    rand_dirs = (rng.random(n) > 0.5).astype(int)
    rand_res = analyze(_series_from_directions(rand_dirs), payout=payout)
    print(format_report("SELFTEST: pure random (expect NO edge)", rand_res))
    print()

    # Rigged: each move repeats the previous one 65% of the time (momentum).
    mom = np.empty(n, dtype=int)
    mom[0] = 1
    for i in range(1, n):
        mom[i] = mom[i - 1] if rng.random() < 0.65 else 1 - mom[i - 1]
    mom_res = analyze(_series_from_directions(mom), payout=payout)
    print(format_report("SELFTEST: rigged momentum (expect edge DETECTED)", mom_res))

    rand_ok = rand_res["predictor"]["oos_acc"] < 0.53 and rand_res["runs"]["p_value"] > 0.01
    mom_ok = (
        mom_res["runs"]["p_value"] < 0.01
        and mom_res["predictor"]["selective_acc"] > mom_res["predictor"]["breakeven"]
    )
    print()
    print(f"[selftest] random reads as no-edge : {'PASS' if rand_ok else 'FAIL'}")
    print(f"[selftest] momentum edge detected  : {'PASS' if mom_ok else 'FAIL'}")
    return bool(rand_ok and mom_ok)
