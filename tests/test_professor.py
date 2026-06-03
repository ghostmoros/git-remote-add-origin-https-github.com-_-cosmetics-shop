"""Юнит-тесты «Профессора» (стандартная библиотека, без зависимостей).

Запуск:  python3 -m unittest discover -s tests
"""
import unittest

from professor.polymarket.models import PMMarket
from professor.polymarket.scanner import scan
from professor.trading.backtest import run_backtest
from professor.trading.data import synthetic_candles
from professor.trading.indicators import rsi, sma
from professor.trading.strategy import SmaRsiStrategy


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


if __name__ == "__main__":
    unittest.main()
