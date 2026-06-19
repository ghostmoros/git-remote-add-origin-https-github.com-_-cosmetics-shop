# Trend Following — Prompt Collection

Covers: **EMA Crossover**, **MACD**, **SuperTrend**, **Ichimoku**, **Trend Pullback (Gold)**

**Strategy style:** Trend | **Best market regime:** Trending (ADX > 20)

---

## 1. EMA Crossover

```
Analyze the following data for an EMA crossover trend signal.

Symbol: {symbol} | Timeframe: {timeframe}

Indicator values (last closed bar):
- EMA Fast ({ema_fast}): {ema_fast_val:.5f}
- EMA Slow ({ema_slow}): {ema_slow_val:.5f}
- Close: {close:.5f}
- ATR (14): {atr:.5f}

Entry rule:
- LONG  when fast EMA crosses above slow EMA
- SHORT when fast EMA crosses below slow EMA
- FLAT  when no crossover on this bar

Signal acted on next bar's OPEN (no look-ahead).
sl_atr: {sl_atr} | tp_atr: {tp_atr} | risk_pct: {risk_pct}

Output a JSON signal.
```

---

## 2. MACD Crossover

```
Analyze for a MACD signal.

Symbol: {symbol} | Timeframe: {timeframe}

Indicators (last closed bar):
- MACD line:   {macd_line:.6f}
- Signal line: {macd_signal:.6f}
- Histogram:   {macd_hist:.6f}
- ATR (14):    {atr:.5f}
- Close:       {close:.5f}

Entry rule:
- LONG  when MACD line crosses above signal line
- SHORT when MACD line crosses below signal line
- FLAT  when no crossover

sl_atr: {sl_atr} | tp_atr: {tp_atr} | risk_pct: {risk_pct}

Output a JSON signal.
```

---

## 3. SuperTrend

```
Analyze for a SuperTrend signal.

Symbol: {symbol} | Timeframe: {timeframe}

Indicators (last closed bar):
- SuperTrend value: {supertrend:.5f}
- SuperTrend direction: {st_direction}   # "up" or "down"
- Close: {close:.5f}
- ATR (14): {atr:.5f}

Entry rule:
- LONG  when price is above SuperTrend (direction = "up")
- SHORT when price is below SuperTrend (direction = "down")
- FLAT  when undecided or on direction flip

sl_atr: {sl_atr} | tp_atr: {tp_atr} | risk_pct: {risk_pct}

Output a JSON signal.
```

---

## 4. Ichimoku Cloud

```
Analyze for an Ichimoku signal.

Symbol: {symbol} | Timeframe: {timeframe}

Indicators (last closed bar):
- Tenkan-sen (9):    {tenkan:.5f}
- Kijun-sen (26):    {kijun:.5f}
- Senkou Span A:     {span_a:.5f}
- Senkou Span B:     {span_b:.5f}
- Chikou Span:       {chikou:.5f}
- Close:             {close:.5f}
- ATR (14):          {atr:.5f}

Entry rule:
- LONG  when: close > max(span_a, span_b)  AND  tenkan > kijun  AND  close > kijun
- SHORT when: close < min(span_a, span_b)  AND  tenkan < kijun  AND  close < kijun
- FLAT  otherwise

sl_atr: {sl_atr} | tp_atr: {tp_atr} | risk_pct: {risk_pct}

Output a JSON signal.
```

---

## 5. Trend Pullback with ADX (Gold / XAUUSD)

```
Analyze for a trend-pullback entry on {symbol}. This strategy is tuned for gold.

Symbol: {symbol} | Timeframe: {timeframe}

Indicators (last two bars):
- EMA Fast (21) — current: {ema_fast_cur:.3f}  |  previous: {ema_fast_prev:.3f}
- EMA Slow (50) — current: {ema_slow_cur:.3f}
- ADX (14):        {adx:.1f}      (strong trend if > 20)
- Close — current: {close_cur:.3f} | previous: {close_prev:.3f}
- ATR (14):        {atr:.3f}

Entry rule:
- Uptrend condition:   fast > slow  AND  close > slow  AND  ADX > 20
- Downtrend condition: fast < slow  AND  close < slow  AND  ADX > 20
- Pullback LONG:  uptrend  AND  previous_close < previous_fast  AND  current_close > current_fast
- Pullback SHORT: downtrend AND previous_close > previous_fast  AND  current_close < current_fast

sl_atr: {sl_atr} | tp_atr: {tp_atr} | risk_pct: {risk_pct}

Gold note: mean-reversion strategies get run over by gold's strong trends.
Only trend/pullback approaches have positive expectancy on XAUUSD.

Output a JSON signal.
```

---

## Common trend-following reminder

Lower win rate (40–60%) is NORMAL for trend strategies. What matters is that winners are 2–3× larger than losers. Always evaluate by **expectancy** and **profit factor**, not win rate alone.
