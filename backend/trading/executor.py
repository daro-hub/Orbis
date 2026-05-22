from typing import Optional
from connectors.base import BaseConnector


class TradeExecutor:
    """Handles trade execution with validation and logging."""

    def __init__(self, connector: BaseConnector):
        self.connector = connector
        self.trade_log: list[dict] = []

    async def execute_market_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> dict:
        if side not in ("buy", "sell"):
            return {"error": "Side must be 'buy' or 'sell'"}
        if quantity <= 0:
            return {"error": "Quantity must be positive"}

        result = await self.connector.place_order(
            symbol=symbol, side=side, quantity=quantity, order_type="market"
        )

        trade_record = {**result, "stop_loss": stop_loss, "take_profit": take_profit}
        self.trade_log.append(trade_record)
        return result

    async def execute_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
    ) -> dict:
        if side not in ("buy", "sell"):
            return {"error": "Side must be 'buy' or 'sell'"}
        if quantity <= 0 or price <= 0:
            return {"error": "Quantity and price must be positive"}

        result = await self.connector.place_order(
            symbol=symbol, side=side, quantity=quantity, order_type="limit", price=price
        )
        self.trade_log.append(result)
        return result

    async def close_all_positions(self, symbols: list[str]) -> list[dict]:
        results = []
        for symbol in symbols:
            result = await self.connector.close_position(symbol)
            results.append(result)
        return results
