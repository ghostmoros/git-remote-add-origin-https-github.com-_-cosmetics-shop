# Forex Trading Bot

Automated forex trading bot — currently focused on **strategy logic + backtesting**.
Broker execution (OANDA / MetaTrader 5) plugs in later behind a clean interface,
so the same strategy code runs in backtest → paper → live without changes.

> ⚠️ **Not financial advice.** Trading forex is risky. Everything here runs on
> synthetic data by default. Validate on real historical data and a **demo
> account** before risking a cent.

## The one thing to remember about "win rate"

A high win rate does **not** mean profit. What decides profitability is
**expectancy**:

```
expectancy = win_rate × avg_win − loss_rate × avg_loss
```

You can win 90% of trades and still lose money (tiny wins, rare huge losses).
The backtest report always prints **win rate, profit factor and expectancy
together** so you optimise the right thing. Example sweep on the built-in data:

| Stop / Target | Win rate | Expectancy | Return | Max DD |
|---------------|---------:|-----------:|-------:|-------:|
| sl=3.0, tp=0.5 | **88.8 %** | +0.020 R | +10 %  | −6.0 % |
| sl=2.5, tp=1.0 | 80.2 %     | +0.103 R | +60 %  | −4.3 % |
| sl=1.5, tp=2.0 | 54.8 %     | **+0.244 R** | **+222 %** | −9.7 % |

The **highest win rate makes the least money.** Pick an operating point by
expectancy, then choose a win rate you can psychologically stick with.

## Quick start

```bash
pip install -r requirements.txt

python3 main.py        # run a backtest with config/config.yaml
python3 optimize.py    # grid-search stop-loss / take-profit multiples
python3 compare.py     # backtest ALL strategies, ranked in one table
python3 analyze_otc.py --selftest   # test if a synthetic/OTC feed is predictable
```

## Project layout

```
forex-bot/
├── bot/
│   ├── core/
│   │   └── strategy.py        # base Strategy interface (signals only)
│   ├── data/
│   │   ├── feed.py            # load CSV or generate synthetic candles
│   │   └── indicators.py      # SMA, EMA, RSI, ATR, Bollinger Bands
│   ├── strategies/            # each = one class emitting +1 / -1 / 0 signals
│   │   ├── mean_reversion.py  # Bollinger fade        (reversion)
│   │   ├── rsi.py             # RSI overbought/sold   (reversion)
│   │   ├── stochastic.py      # Stochastic oscillator (reversion)
│   │   ├── ma_crossover.py    # EMA crossover         (trend)
│   │   ├── macd.py            # MACD crossover        (trend)
│   │   ├── supertrend.py      # SuperTrend            (trend)
│   │   ├── ichimoku.py        # Ichimoku cloud        (trend)
│   │   ├── donchian.py        # Donchian breakout     (breakout)
│   │   └── london_breakout.py # session breakout      (breakout, FX-specific)
│   ├── brokers/
│   │   ├── base.py            # Broker interface (the venue seam)
│   │   └── mt5.py             # MetaTrader 5 adapter (RoboForex etc.)
│   ├── risk/
│   │   └── sizing.py          # lot sizing from risk % + stop distance
│   ├── analysis/
│   │   ├── otc.py             # is a synthetic/OTC feed predictable? (out-of-sample test)
│   │   └── edge.py            # two-feed lag-arbitrage test (fast feed vs broker feed)
│   └── backtest/
│       ├── engine.py          # risk-based sizing, ATR SL/TP, no look-ahead
│       └── metrics.py         # win rate, profit factor, expectancy, drawdown…
├── config/config.yaml         # all tunables in one place
├── main.py                    # run one backtest + report
├── optimize.py                # sweep risk params, rank by expectancy & win rate
├── compare.py                 # backtest every strategy, ranked in one table
├── analyze_otc.py             # test a synthetic/OTC feed for an out-of-sample edge
├── run_live.py                # live/dry-run trading via MT5 (run on YOUR PC)
├── fetch_history.py           # dump real candles from MT5 to data/*.csv
├── requirements.txt
└── requirements-live.txt      # MetaTrader5 (Windows-only)
```

**Design principle:** a *strategy* only emits signals (+1 long, −1 short, 0
flat). It knows nothing about position size, stops, or brokers. The *engine*
owns risk and execution. That separation is what lets us drop in an OANDA/MT5
adapter later without touching strategy logic.

## Strategies

Studied from popular open-source bots ([je-suis-tm/quant-trading](https://github.com/je-suis-tm/quant-trading),
[freqtrade](https://github.com/freqtrade/freqtrade-strategies), FXBot, MT5 bots)
and re-implemented behind our common signal interface.

**Mean reversion** (high win rate, small targets):
- **mean_reversion** — fades 2σ Bollinger-band stretches. Optional
  `require_rsi` / `use_trend_filter` tighten entries.
- **rsi** — long when RSI < oversold, short when RSI > overbought.
- **stochastic** — same idea using the stochastic oscillator.

**Trend following** (lower win rate, bigger winners):
- **ma_crossover** — fast/slow EMA crossover.
- **macd** — MACD line vs signal line.
- **supertrend** — ride the ATR-based SuperTrend line (popular in FX/MT5).
- **ichimoku** — long above the cloud + Tenkan > Kijun (and mirror for shorts).
- **trend_pullback** — EMA trend + ADX strength filter, enter on a pullback
  that reclaims the fast EMA. **Tuned for gold (XAUUSD)** — see below.

**Breakout**:
- **donchian** — Turtle-style break of the prior N-bar high/low.
- **london_breakout** — *forex-specific*: trade the break of the pre-London
  (Asian) range when London opens. Needs intraday data with timestamps.

`compare.py` backtests them all with a stop/target profile that's fair for each
style (trend lets winners run, reversion takes small profits) and ranks by
expectancy. On the built-in mean-reverting synthetic data the reversion
strategies win and the trend/breakout ones lose — exactly as theory predicts.
**Which family wins is entirely regime-dependent**, so always re-run on the real
market and timeframe you intend to trade.

## How signals are executed (no look-ahead bias)

A signal computed from bar *i*'s close is acted on at bar *i+1*'s **open**.
Stops/targets are sized from the ATR of the last closed bar. Position size is
set so a full stop-loss loses exactly `risk_pct` of equity (default 1 %), which
makes every result comparable in **R multiples**.

## Live trading via MetaTrader 5 (RoboForex)

> ⚠️ **Runs on YOUR machine, not in the cloud.** The `MetaTrader5` package is
> Windows-only and talks to a locally installed, running MT5 terminal. Start on
> a **DEMO** account. Never put your password in the repo or paste it anywhere.

1. Install the MT5 terminal from RoboForex and log into your **demo** account.
2. On that machine:
   ```bash
   pip install -r requirements.txt -r requirements-live.txt
   ```
3. Provide credentials via environment variables (PowerShell example):
   ```powershell
   $env:MT5_LOGIN="12345678"
   $env:MT5_PASSWORD="your-demo-password"
   $env:MT5_SERVER="RoboForex-Demo"   # or RoboForex-Pro / RoboForex-ECN
   ```
4. Pick the symbol/timeframe/strategy in `config/config.yaml` (`broker:` and
   `strategy:` sections), then run:
   ```bash
   python run_live.py          # one decision cycle, DRY-RUN (prints, no orders)
   python run_live.py --loop   # keep running every live.poll_seconds
   ```

**Safety gates** (in `config.yaml` → `live:`):
- `dry_run: true` (default) — decide and print only, place **no** orders.
- `allow_real: false` (default) — even with `dry_run: false`, a **real** account
  is refused unless you flip this to `true`.

Prove the strategy on demo for a meaningful period before even thinking about
real money.

## Trading gold (XAUUSD)

Gold is not a forex pair: it **trends hard** and is volatile, so mean-reversion
strategies get run over by it. Use the **trend** approach instead — there's a
ready profile in `config/config_gold.yaml` (strategy `trend_pullback`, wide
take-profit to let trends run, smaller `risk_pct`, gold spread). The ATR-based
stop and risk sizing auto-adapt to gold's larger volatility.

```bash
python fetch_history.py XAUUSD H1 5000     # real gold data (on your MT5 machine)
python main.py config/config_gold.yaml     # backtest the gold profile
python compare.py config/config_gold.yaml  # see which strategy fits gold
```

On synthetic *trending* data `trend_pullback` is strongly profitable while
mean-reversion loses badly — and vice-versa on ranging data. The lesson:
**match the strategy to the market regime, and confirm on real XAUUSD history.**

## Position sizing

Live orders are sized so a stop-loss hit loses exactly `backtest.risk_pct` of
account equity — the same risk model as the backtest. `bot/risk/sizing.py`
converts (risk amount, stop distance, contract tick value/size) into a lot size,
snapped to the broker's volume step. Set `live.sizing: risk` (default) to use
it, or `live.sizing: fixed` to fall back to a constant `live.lots`.

## Using real data

**Easiest — pull it straight from MT5** (on the machine with the terminal):

```bash
python fetch_history.py EURUSD H1 5000   # -> data/EURUSD_H1.csv
```

Or drop any CSV with `time, open, high, low, close` columns into `data/`. Then
point the config at it and backtest/compare on the real market:

```yaml
data:
  source: csv
  csv_path: data/EURUSD_H1.csv
```

```bash
python compare.py    # which strategy actually holds an edge on real EUR/USD?
```

## Testing a binary-options feed (`analyze_otc.py`)

Binary-options brokers either price weekend / **OTC** assets with an internal
generator, or (in market hours) quote a real pair that *lags* a faster feed. The
only rational reason to record their ticks is to ask, honestly, whether there's a
footprint you can predict — and whether that edge **survives on data you didn't
look at while searching**. `analyze_otc.py` does that, auto-detecting two layouts:

**1. Two-feed lag-arbitrage log** — `fast_ts,broker_ts,symbol,fast_price,broker_price`
(header optional). This is the actual "MT5 vs broker" strategy: it measures the
real feed **lag**, then bets the broker price catches up to the fast feed and
checks whether that beats the payout **out-of-sample**, with **non-overlapping**
trades (no inflated sample).

```bash
python3 analyze_otc.py arbitrage/data/edge_ticks_20260612_212522.csv --payout 0.82
```

**2. Single price / OTC stream** — any of `price`/`close`/`last`/`mid`/`bid`+`ask`
(a `time`/`date`/`datetime`/`timestamp` column is used if present, else row order).
Runs randomness tests (Wald–Wolfowitz runs test, autocorrelation, Markov
conditionals) + an out-of-sample short-memory model.

```bash
python3 analyze_otc.py --selftest                        # prove the tool works (no data needed)
python3 analyze_otc.py data/btc_otc.csv --payout 0.90    # crypto OTC pays ~90%
python3 analyze_otc.py data/eurusd_otc.csv --payout 0.85 # forex OTC pays ~85%
python3 analyze_otc.py edge_ticks_xxx.csv --otc          # force OTC test on a two-feed log's broker column
```

Both end in the **payout gate**: at an 82 % payout you must be right **> 54.95 %**
just to break even, so any "significant" pattern that doesn't clear that line is
worthless. The **in-sample vs out-of-sample gap is the overfitting**.

> A clean random / lock-step feed correctly comes back as **"no edge"** — that's
> the tool working, not failing. And even a real edge can be neutralised: live
> latency eats the lead, and the broker can re-quote at expiry, void "suspicious"
> trades, or refuse withdrawals. Test on a **demo** account, never risk money you
> can't lose.

## Roadmap

- [x] Indicators, strategies, backtest engine, metrics, optimizer
- [x] Broker adapter interface (`bot/brokers/base.py`)
- [x] MetaTrader 5 adapter + dry-run live runner (demo-first, real-account gated)
- [x] Risk-based lot sizing for live orders (% of equity per trade)
- [x] Pull real history from MT5 to CSV (`fetch_history.py`)
- [x] OTC/synthetic-feed predictability test, out-of-sample (`analyze_otc.py`)
- [ ] OANDA adapter (REST + streaming, practice account first)
- [ ] Telegram alerts / status reporting
- [ ] Walk-forward validation to avoid overfitting

## Configuration reference

See `config/config.yaml` — data source, strategy + params, and backtest risk
settings (`risk_pct`, `atr_period`, `sl_atr`, `tp_atr`, `spread`).
