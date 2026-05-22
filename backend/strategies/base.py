from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd


class Signal:
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class BaseStrategy(ABC):
    """Abstract base class for trading strategies."""

    def __init__(self, name: str = "BaseStrategy", params: Optional[dict] = None):
        self.name = name
        self.params = params or {}

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Process historical data and generate signals.
        Must add a 'signal' column to the DataFrame with values: 'buy', 'sell', or 'hold'.
        """
        pass

    def validate_data(self, df: pd.DataFrame) -> bool:
        required = ["open", "high", "low", "close"]
        return all(col in df.columns for col in required)
