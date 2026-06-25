"""Test whether you can actually beat a broker's feed — honestly.

Two modes, auto-detected from the CSV columns:

* **Two-feed lag-arbitrage log** (`fast_ts,broker_ts,symbol,fast_price,broker_price`,
  header optional) -> measures the real feed lag and whether the broker price
  catches up to the fast feed enough to beat the payout, out-of-sample. Also runs
  the randomness tests on the broker feed itself.
* **Single price / OTC stream** (any of `price/close/last/mid/bid+ask`; a
  `time/date/datetime/timestamp` column is used if present, else row order) ->
  randomness tests + an out-of-sample short-memory model.

Examples:

    python3 analyze_otc.py arbitrage/data/edge_ticks_20260612_212522.csv
    python3 analyze_otc.py data/gbpusd_otc.csv --payout 0.82
    python3 analyze_otc.py data/pepe_otc.csv  --payout 0.95
    python3 analyze_otc.py --selftest                 # no data needed

Both modes end in a payout gate: at an 82% payout you must be right > 54.95% just
to break even. A clean random / lock-step feed will (correctly) come back as
"no edge". This tells you whether the past held a repeatable footprint — it does
not predict the future, and a broker can change the feed or refuse withdrawals.
"""
from __future__ import annotations

import argparse
import sys

from bot.analysis import edge as edge_mod
from bot.analysis.otc import analyze, format_report, load_ticks, selftest


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Test an OTC / lag-arbitrage feed for a tradeable, out-of-sample edge.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("csv", nargs="?", help="path to the tick CSV (single-feed or two-feed)")
    p.add_argument("--payout", type=float, default=0.82,
                   help="win payout as a fraction, e.g. 0.82 for 82%% (default: 0.82)")
    p.add_argument("--max-k", type=int, default=3, help="max memory length to try, OTC mode (default: 3)")
    p.add_argument("--max-lag", type=int, default=10, help="max autocorrelation lag, OTC mode (default: 10)")
    p.add_argument("--selftest", action="store_true",
                   help="run the built-in random vs rigged-momentum check and exit")
    args = p.parse_args(argv)

    if args.selftest:
        return 0 if selftest(payout=args.payout) else 1

    if not args.csv:
        p.error("provide a CSV path, or use --selftest")
    if not 0.0 < args.payout < 5.0:
        p.error("--payout should be a fraction like 0.82 (82%), not a percentage")

    # Two-feed lag-arbitrage log? That's the bot's actual strategy — test it directly.
    edge_df = edge_mod.load_edge_ticks(args.csv)
    if edge_df is not None:
        print(edge_mod.format_edge_report(args.csv, edge_mod.analyze_edge(edge_df, payout=args.payout)))
        return 0

    # Otherwise treat it as a single price / OTC stream.
    price = load_ticks(args.csv)
    print(format_report(args.csv, analyze(price, payout=args.payout, max_lag=args.max_lag, max_k=args.max_k)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
