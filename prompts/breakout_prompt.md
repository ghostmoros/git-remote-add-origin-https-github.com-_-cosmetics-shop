# Breakout Strategies — Prompt Collection

Covers: **Donchian Channel Breakout**, **London Session Breakout**

**Strategy style:** Breakout | **Best regime:** High-volatility breakout moments

---

## 1. Donchian Channel Breakout (Turtle style)

```
Analyze for a Donchian channel breakout signal.

Symbol: {symbol} | Timeframe: {timeframe}

Indicators (last closed bar):
- Donchian High ({period} bars): {don_high:.5f}   — prior {period}-bar highest high
- Donchian Low  ({period} bars): {don_low:.5f}    — prior {period}-bar lowest low
- Close (current bar):           {close:.5f}
- ATR (14):                      {atr:.5f}

Entry rule:
- LONG  when close > Donchian High  (breakout above the channel)
- SHORT when close < Donchian Low   (breakout below the channel)
- FLAT  when price is inside the channel

Note: signal is from bar i's close, acted on bar i+1's OPEN (no look-ahead).

sl_atr: {sl_atr} | tp_atr: {tp_atr} | risk_pct: {risk_pct}

Output a JSON signal.
```

---

## 2. London Session Breakout (FX-specific)

```
Analyze for a London session breakout signal.

Symbol: {symbol} | Timeframe: {timeframe}
This strategy requires intraday data with timestamps (M15 or H1 recommended).

Session range (Asian session, pre-London):
- Asian session high: {asian_high:.5f}
- Asian session low:  {asian_low:.5f}
- Range size:         {range_size:.5f}  ({range_pips:.1f} pips)

Current bar:
- Time (UTC): {bar_time}
- Open:  {open_:.5f}
- Close: {close:.5f}
- ATR (14): {atr:.5f}

Entry rule (London open window only — typically 07:00–10:00 UTC):
- LONG  when close > Asian session high  (London breaks above Asia range)
- SHORT when close < Asian session low   (London breaks below Asia range)
- FLAT  if bar is outside the London open window OR price is inside the range

sl_atr: {sl_atr} | tp_atr: {tp_atr} | risk_pct: {risk_pct}

Important: this strategy is only active during the London open window.
Output FLAT for all bars outside that window regardless of price.

Output a JSON signal.
```

---

## Notes on breakout strategies

- Breakouts generate fewer signals than reversion strategies but can catch large moves.
- **False breakouts** (price breaks and immediately reverses) are common — this is why ATR-based stops are critical.
- Donchian works on any liquid instrument. London Breakout is FX-specific (exploits the volatility spike when London opens).
- Win rates are typically lower (40–55%) but with a favourable R:R if tuned correctly.
