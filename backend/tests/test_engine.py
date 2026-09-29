import pandas as pd
import pytest

from backtester.engine import BacktestEngine
from strategies.base import BaseStrategy, Signal


class ScriptedStrategy(BaseStrategy):
    """Test double: emits an exact, caller-specified signal per bar instead
    of computing one, so tests can assert on precisely which bar/price the
    engine executes against."""

    def __init__(self, signals: list[str]):
        super().__init__(name="Scripted", params={})
        self.signals = signals

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["signal"] = self.signals
        return df


def make_df(opens, closes):
    n = len(opens)
    index = pd.date_range("2024-01-01", periods=n, freq="h")
    return pd.DataFrame(
        {
            "open": opens,
            "high": [max(o, c) for o, c in zip(opens, closes)],
            "low": [min(o, c) for o, c in zip(opens, closes)],
            "close": closes,
            "volume": [1.0] * n,
        },
        index=index,
    )


@pytest.fixture
def scenario():
    # bar:      0      1      2      3      4
    opens =  [100.0, 110.0, 115.0, 118.0, 120.0]
    closes = [105.0, 108.0, 120.0, 122.0, 121.0]
    signals = [Signal.BUY, Signal.HOLD, Signal.SELL, Signal.HOLD, Signal.HOLD]
    return make_df(opens, closes), signals


def test_execution_happens_on_next_bar_open_not_signal_bar_close(scenario):
    """The core look-ahead-bias fix: a signal read from bar i must be filled
    at bar i+1's open, never at bar i's own close."""
    df, signals = scenario
    engine = BacktestEngine(ScriptedStrategy(signals), initial_capital=10000, commission_pct=0, slippage_pct=0)

    results = engine.run(df)

    assert len(results["trades"]) == 1
    trade = results["trades"][0]
    # BUY signal at bar 0 -> filled at bar 1's open (110), not bar 0's
    # close (105) and not bar 1's close (108).
    assert trade["entry_price"] == 110.0
    # SELL signal at bar 2 -> filled at bar 3's open (118), not bar 2's
    # close (120).
    assert trade["exit_price"] == 118.0


def test_pnl_and_capital_accounting_matches_hand_calculation(scenario):
    """Regression: the old _close_position derived commission from
    `pnl + self.capital` (meaningless) and overwrote self.capital with
    `quantity * entry_price + pnl`, discarding the entry commission
    already paid. With zero commission this particular bug doesn't show,
    so the commission case below is the real regression test — this one
    pins down the base PnL math."""
    df, signals = scenario
    engine = BacktestEngine(ScriptedStrategy(signals), initial_capital=10000, commission_pct=0, slippage_pct=0)

    results = engine.run(df)

    quantity = 10000.0 / 110.0
    expected_pnl = (118.0 - 110.0) * quantity
    trade = results["trades"][0]
    assert trade["pnl"] == round(expected_pnl, 2)
    assert results["metrics"]["final_capital"] == round(10000.0 + expected_pnl, 2)


def test_capital_accounting_with_commission_matches_hand_calculation(scenario):
    df, signals = scenario
    engine = BacktestEngine(ScriptedStrategy(signals), initial_capital=10000, commission_pct=1.0, slippage_pct=0)

    results = engine.run(df)

    entry_commission = 10000.0 * 0.01
    quantity = (10000.0 - entry_commission) / 110.0  # == 90.0 exactly
    gross_pnl = (118.0 - 110.0) * quantity
    exit_commission = (quantity * 118.0) * 0.01
    expected_final_capital = 10000.0 - entry_commission - exit_commission + gross_pnl

    assert results["metrics"]["final_capital"] == round(expected_final_capital, 2)


def test_equity_curve_has_one_point_per_bar(scenario):
    df, signals = scenario
    engine = BacktestEngine(ScriptedStrategy(signals), initial_capital=10000, commission_pct=0, slippage_pct=0)

    results = engine.run(df)

    assert len(results["equity_curve"]) == len(df)
    # Bar 0: no position has been opened yet (the BUY signal from bar 0
    # only executes at bar 1's open) — equity is just flat starting capital.
    assert results["equity_curve"][0] == 10000.0


def test_signal_on_last_bar_has_no_next_open_and_is_not_executed():
    """A signal generated on the final bar has no following bar to fill
    at — it must be dropped, not crash the engine."""
    opens = [100.0, 110.0, 115.0]
    closes = [105.0, 108.0, 120.0]
    signals = [Signal.HOLD, Signal.HOLD, Signal.BUY]
    df = make_df(opens, closes)

    engine = BacktestEngine(ScriptedStrategy(signals), initial_capital=10000, commission_pct=0, slippage_pct=0)
    results = engine.run(df)

    assert results["trades"] == []
    assert len(results["equity_curve"]) == 3
