# Oscillator Mean Reversion — Prompt Collection

Covers: **RSI**, **Stochastic**

**Strategy style:** Reversion | **Best market regime:** Ranging / sideways

---

## 1. RSI Strategy

```
Analyze the following data for an RSI mean-reversion signal.

Symbol: {symbol} | Timeframe: {timeframe}

Indicators (last closed bar):
- RSI ({rsi_period}): {rsi:.1f}
- Close:  {close:.5f}
- ATR (14): {atr:.5f}

Entry rule:
- LONG  when RSI < {rsi_oversold}   (oversold — expect bounce)
- SHORT when RSI > {rsi_overbought} (overbought — expect pullback)
- FLAT  otherwise

Default thresholds: oversold={rsi_oversold}, overbought={rsi_overbought}

sl_atr: {sl_atr} | tp_atr: {tp_atr} | risk_pct: {risk_pct}

Caution: in strong trends RSI can stay overbought/oversold for extended periods.
Consider adding an EMA-200 trend filter if results are poor on trending assets.

Output a JSON signal.
```

---

## 2. Stochastic Oscillator

```
Analyze for a Stochastic oscillator mean-reversion signal.

Symbol: {symbol} | Timeframe: {timeframe}

Indicators (last closed bar):
- %K ({k_period}): {stoch_k:.1f}
- %D ({d_period}): {stoch_d:.1f}
- Close:  {close:.5f}
- ATR (14): {atr:.5f}

Entry rule:
- LONG  when %K < {oversold}  AND  %K crosses above %D  (momentum turning up from oversold)
- SHORT when %K > {overbought} AND  %K crosses below %D (momentum turning down from overbought)
- FLAT  otherwise

Default thresholds: oversold={oversold}, overbought={overbought}

sl_atr: {sl_atr} | tp_atr: {tp_atr} | risk_pct: {risk_pct}

Output a JSON signal.
```

---

## Notes on oscillator strategies

- Both RSI and Stochastic work best in **ranging markets**. In a trending market they generate false signals (the indicator stays extreme).
- Pairing with a **Bollinger Band width filter** (only trade when bands are narrow = low volatility / range) can improve signal quality.
- Default setup uses wide SL / small TP for high win rate. Check expectancy before going live.
