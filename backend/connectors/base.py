from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd


class BaseConnector(ABC):
    """Abstract base class for exchange/broker connectors."""

    @abstractmethod
    async def get_historical_data(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 500,
        since: Optional[int] = None,
    ) -> pd.DataFrame:
        """Fetch historical OHLCV data and return as DataFrame."""
        pass

    @abstractmethod
    async def get_current_price(self, symbol: str) -> dict:
        """Get current price for a symbol."""
        pass

    @abstractmethod
    async def place_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "market",
        price: Optional[float] = None,
    ) -> dict:
        """Place an order. Returns order info dict."""
        pass

    @abstractmethod
    async def close_position(self, symbol: str, position_id: Optional[str] = None) -> dict:
        """Close an open position."""
        pass

    @abstractmethod
    async def get_open_positions(self) -> list[dict]:
        """Get all open positions."""
        pass

    @abstractmethod
    async def get_balance(self) -> dict:
        """Get account balance."""
        pass
