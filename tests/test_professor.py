"""Юнит-тесты «Профессора» (стандартная библиотека, без зависимостей).

Запуск:  python3 -m unittest discover -s tests
"""
import unittest

from professor.polymarket.models import PMMarket
from professor.polymarket.scanner import scan
from professor.trading.backtest import run_backtest
from professor.trading.data import load_csv, synthetic_candles
from professor.trading.indicators import rsi, sma
from professor.trading.strategy import DonchianBreakoutStrategy, Signal, SmaRsiStrategy
from professor.trading.walkforward import buy_and_hold_return, walk_forward


class TestIndicators(unittest.TestCase):
    def test_sma_basic(self):
        out = sma([1, 2, 3, 4, 5], 3)
        self.assertIsNone(out[0])
        self.assertIsNone(out[1])
        self.assertAlmostEqual(out[2], 2.0)
        self.assertAlmostEqual(out[4], 4.0)

    def test_rsi_range_and_trend(self):
        out = rsi([float(i) for i in range(1, 60)], 14)
        last = [x for x in out if x is not None][-1]
        self.assertTrue(0.0 <= last <= 100.0)
        self.assertGreater(last, 90.0)  # монотонный рост → RSI высокий


class TestScanner(unittest.TestCase):
    def test_detects_arbitrage(self):
        m = PMMarket("a", "q?", "Crypto", yes_price=0.40, no_price=0.50, volume=10_000)
        kinds = {o.kind for o in scan([m], min_edge=0.05)}
        self.assertIn("arbitrage", kinds)

    def test_detects_value(self):
        m = PMMarket("b", "q?", "Crypto", yes_price=0.40, no_price=0.62,
                     volume=10_000, fair_yes=0.60)
        opps = scan([m], min_edge=0.05)
        self.assertTrue(any(o.kind == "value-yes" for o in opps))
        ve = next(o for o in opps if o.kind == "value-yes")
        self.assertAlmostEqual(ve.edge, 0.20, places=6)

    def test_volume_filter(self):
        m = PMMarket("c", "q?", "Crypto", yes_price=0.40, no_price=0.50, volume=100)
        self.assertEqual(scan([m], min_edge=0.05, min_volume=5_000), [])


class TestBacktest(unittest.TestCase):
    def test_runs_and_is_sane(self):
        candles = synthetic_candles(300, 100.0, seed=1)
        res = run_backtest("TEST", candles, SmaRsiStrategy(), 1000.0)
        self.assertEqual(res.symbol, "TEST")
        self.assertEqual(len(res.equity_curve), 300)
        self.assertGreaterEqual(res.stats.n_trades, 0)
        self.assertGreaterEqual(res.stats.final_equity, 0.0)  # long-only не уходит в минус

    def test_deterministic(self):
        a = synthetic_candles(200, 100.0, seed=42)
        b = synthetic_candles(200, 100.0, seed=42)
        self.assertEqual([c.close for c in a], [c.close for c in b])

    def test_warmup_skips_early_candles(self):
        candles = synthetic_candles(100, 100.0, seed=2)
        res = run_backtest("T", candles, SmaRsiStrategy(), 1000.0, warmup=30)
        self.assertEqual(len(res.equity_curve), 70)


class TestDonchian(unittest.TestCase):
    def test_breakout_generates_buy(self):
        # сильный аптренд с малым шумом → постоянные новые максимумы → пробои
        candles = synthetic_candles(200, 100.0, seed=1, drift=0.01, vol=0.005)
        signals = DonchianBreakoutStrategy(entry_period=20, exit_period=10).generate(candles)
        self.assertGreater(sum(s == Signal.BUY for s in signals), 0)

    def test_no_lookahead_first_candles_hold(self):
        candles = synthetic_candles(50, 100.0, seed=1)
        signals = DonchianBreakoutStrategy(entry_period=20, exit_period=10).generate(candles)
        # до набора истории канала сигналов быть не может
        self.assertTrue(all(s == Signal.HOLD for s in signals[:10]))


class TestWalkForward(unittest.TestCase):
    def _factory(self, p):
        return DonchianBreakoutStrategy(entry_period=p["entry"], exit_period=p["exit"])

    def test_walk_forward_runs(self):
        candles = synthetic_candles(700, 100.0, seed=3)
        grid = [{"entry": e, "exit": max(5, e // 2)} for e in (15, 20, 30)]
        res = walk_forward("T", candles, self._factory, grid, 1000.0, 0.04,
                           in_size=200, out_size=100, warmup=40)
        self.assertGreaterEqual(res.n_segments, 1)
        self.assertEqual(len(res.chosen_params), res.n_segments)
        self.assertGreaterEqual(res.oos_stats.final_equity, 0.0)  # long-only ≥ 0

    def test_buy_and_hold(self):
        candles = synthetic_candles(50, 100.0, seed=5)
        self.assertAlmostEqual(buy_and_hold_return(candles),
                               candles[-1].close / candles[0].close - 1)


class TestCSVLoader(unittest.TestCase):
    def _write(self, content: str) -> str:
        import os
        import tempfile
        fd, path = tempfile.mkstemp(suffix=".csv")
        with os.fdopen(fd, "w", newline="") as f:
            f.write(content)
        self.addCleanup(os.unlink, path)
        return path

    def test_headerless_binance_style(self):
        path = self._write("1000,10,12,9,11,100\n2000,11,13,10,12,120\n3000,12,14,11,13,130\n")
        candles = load_csv(path)
        self.assertEqual(len(candles), 3)
        self.assertEqual(candles[0].close, 11.0)
        self.assertEqual(candles[2].high, 14.0)

    def test_header_and_ascending_sort(self):
        # строки «новые сверху» → загрузчик сортирует по unix по возрастанию
        path = self._write("unix,open,high,low,close,volume\n"
                           "2000,11,13,10,12,5\n1000,10,12,9,11,4\n")
        candles = load_csv(path)
        self.assertEqual(len(candles), 2)
        self.assertEqual(candles[0].close, 11.0)   # самая ранняя (unix 1000) — первая
        self.assertEqual(candles[1].close, 12.0)


if __name__ == "__main__":
    unittest.main()
