"""Position sizing — turn a risk budget into a broker lot size.

Pure function (no broker imports) so it's testable anywhere. The idea matches
the backtest engine: size the trade so that hitting the stop-loss loses exactly
`risk_amount` of account currency.

    loss_per_lot = (stop_distance / tick_size) * tick_value     # per 1.0 lot
    lots         = risk_amount / loss_per_lot                   # then snap to step

`tick_value` and `tick_size` come from the broker's symbol info (for MT5:
trade_tick_value / trade_tick_size, both in account currency / price terms).
"""
from __future__ import annotations

import math


def position_size(
    risk_amount: float,
    stop_distance: float,
    tick_value: float,
    tick_size: float,
    volume_min: float,
    volume_max: float,
    volume_step: float,
) -> float:
    """Lots to trade for `risk_amount` lost at a `stop_distance` price move.

    Snaps DOWN to the broker's volume step and clamps to [min, max]. Falls back
    to the minimum lot if inputs are degenerate (so we never return 0/NaN).
    """
    if stop_distance <= 0 or tick_value <= 0 or tick_size <= 0 or risk_amount <= 0:
        return volume_min

    loss_per_lot = (stop_distance / tick_size) * tick_value
    if loss_per_lot <= 0:
        return volume_min

    raw_lots = risk_amount / loss_per_lot

    if volume_step > 0:
        steps = math.floor(raw_lots / volume_step + 1e-9)  # epsilon for float noise
        lots = steps * volume_step
    else:
        lots = raw_lots

    lots = max(volume_min, min(volume_max, lots))
    return round(lots, 8)
