"""Test whether a broker's synthetic ("OTC") feed is predictable — honestly.

Record OTC ticks from your bot to a CSV (any of these columns work as the price:
price / close / last / mid / bid+ask; a time/date/datetime/timestamp column is
used if present, otherwise row order). Then:

    python3 analyze_otc.py data/gbpusd_otc_ticks.csv             # default 82% payout
    python3 analyze_otc.py data/pepe_otc.csv --payout 0.95       # set your payout
    python3 analyze_otc.py --selftest                            # no data needed

What it does (see bot/analysis/otc.py for the details):
  * runs test + autocorrelation + Markov conditionals — is it a coin?
  * learns the best short-memory rule on the FIRST 65% of the history and scores
    it on the held-out tail — the in-sample vs out-of-sample gap is the overfit.
  * a payout gate: at 82% payout you must be right > 54.95% just to break even.

A clean random generator will (correctly) come back as "no exploitable edge".
This tells you whether the past held a repeatable footprint — it does not predict
the future, and a broker can change the generator or refuse withdrawals anytime.
"""
from __future__ import annotations

import argparse
import sys

from bot.analysis.otc import analyze, format_report, load_ticks, selftest


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Test a synthetic/OTC price feed for a tradeable, out-of-sample edge.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("csv", nargs="?", help="path to the OTC tick/price CSV")
    p.add_argument("--payout", type=float, default=0.82,
                   help="win payout as a fraction, e.g. 0.82 for 82%% (default: 0.82)")
    p.add_argument("--max-k", type=int, default=3, help="max memory length to try (default: 3)")
    p.add_argument("--max-lag", type=int, default=10, help="max autocorrelation lag (default: 10)")
    p.add_argument("--selftest", action="store_true",
                   help="run the built-in random vs rigged-momentum check and exit")
    args = p.parse_args(argv)

    if args.selftest:
        ok = selftest(payout=args.payout)
        return 0 if ok else 1

    if not args.csv:
        p.error("provide a CSV path, or use --selftest")

    if not 0.0 < args.payout < 5.0:
        p.error("--payout should be a fraction like 0.82 (82%), not a percentage")

    price = load_ticks(args.csv)
    res = analyze(price, payout=args.payout, max_lag=args.max_lag, max_k=args.max_k)
    print(format_report(args.csv, res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
