import pandas as pd

from strategies.example_sma import SMAcrossoverStrategy


def test_sma_crossover_does_not_crash_during_rolling_warmup():
    """Regression: shift(1) on the boolean crossover series left NaN on
    the first row, upcasting it to object/float — `~fast_above_prev` then
    raised TypeError on any real dataset (anything longer than the rolling
    window), since this path was never exercised by a real backtest run."""
    n = 50
    index = pd.date_range("2024-01-01", periods=n, freq="h")
    prices = [100.0 + i * 0.5 for i in range(n)]
    df = pd.DataFrame(
        {"open": prices, "high": prices, "low": prices, "close": prices, "volume": [1.0] * n},
        index=index,
    )

    strategy = SMAcrossoverStrategy(fast_period=5, slow_period=10)
    result = strategy.generate_signals(df)  # must not raise

    assert "signal" in result.columns
    assert len(result) == n
