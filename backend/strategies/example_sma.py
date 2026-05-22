import pandas as pd
from .base import BaseStrategy, Signal


class SMAcrossoverStrategy(BaseStrategy):
    """
    Simple Moving Average Crossover Strategy.
    Buy when fast SMA crosses above slow SMA, sell when it crosses below.
    """

    def __init__(self, fast_period: int = 10, slow_period: int = 30):
        super().__init__(
            name="SMA Crossover",
            params={"fast_period": fast_period, "slow_period": slow_period},
        )
        self.fast_period = fast_period
        self.slow_period = slow_period

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        if not self.validate_data(df):
            raise ValueError("DataFrame must have OHLC columns")

        df = df.copy()
        df["sma_fast"] = df["close"].rolling(window=self.fast_period).mean()
        df["sma_slow"] = df["close"].rolling(window=self.slow_period).mean()

        df["signal"] = Signal.HOLD

        # Crossover detection
        fast_above = df["sma_fast"] > df["sma_slow"]
        fast_above_prev = fast_above.shift(1)

        # Buy: fast crosses above slow
        df.loc[fast_above & ~fast_above_prev, "signal"] = Signal.BUY
        # Sell: fast crosses below slow
        df.loc[~fast_above & fast_above_prev, "signal"] = Signal.SELL

        return df


class RSIStrategy(BaseStrategy):
    """
    RSI Overbought/Oversold Strategy.
    Buy when RSI goes below oversold level, sell when above overbought.
    """

    def __init__(self, period: int = 14, oversold: float = 30, overbought: float = 70):
        super().__init__(
            name="RSI Strategy",
            params={"period": period, "oversold": oversold, "overbought": overbought},
        )
        self.period = period
        self.oversold = oversold
        self.overbought = overbought

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        if not self.validate_data(df):
            raise ValueError("DataFrame must have OHLC columns")

        df = df.copy()

        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0).rolling(window=self.period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.period).mean()
        rs = gain / loss
        df["rsi"] = 100 - (100 / (1 + rs))

        df["signal"] = Signal.HOLD

        rsi_prev = df["rsi"].shift(1)

        # Buy when RSI crosses below oversold
        df.loc[(df["rsi"] <= self.oversold) & (rsi_prev > self.oversold), "signal"] = Signal.BUY
        # Sell when RSI crosses above overbought
        df.loc[(df["rsi"] >= self.overbought) & (rsi_prev < self.overbought), "signal"] = Signal.SELL

        return df
