import ccxt.async_support as ccxt
import pandas as pd
from typing import Optional
from .base import BaseConnector


class BybitConnector(BaseConnector):
    """Connector for Bybit exchange via ccxt (Bitcoin trading)."""

    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        self.exchange = ccxt.bybit({
            "apiKey": api_key,
            "secret": api_secret,
            "options": {"defaultType": "linear"},
        })
        if testnet:
            self.exchange.set_sandbox_mode(True)

    async def close(self):
        await self.exchange.close()

    async def get_historical_data(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 500,
        since: Optional[int] = None,
    ) -> pd.DataFrame:
        ohlcv = await self.exchange.fetch_ohlcv(
            symbol, timeframe=timeframe, limit=limit, since=since
        )
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        return df

    async def get_current_price(self, symbol: str) -> dict:
        ticker = await self.exchange.fetch_ticker(symbol)
        return {
            "symbol": symbol,
            "bid": ticker["bid"],
            "ask": ticker["ask"],
            "last": ticker["last"],
            "timestamp": ticker["timestamp"],
        }

    async def place_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "market",
        price: Optional[float] = None,
    ) -> dict:
        params = {}
        order = await self.exchange.create_order(
            symbol=symbol,
            type=order_type,
            side=side,
            amount=quantity,
            price=price,
            params=params,
        )
        return {
            "id": order["id"],
            "symbol": order["symbol"],
            "side": order["side"],
            "type": order["type"],
            "quantity": order["amount"],
            "price": order.get("average") or order.get("price"),
            "status": order["status"],
            "timestamp": order["timestamp"],
        }

    async def close_position(self, symbol: str, position_id: Optional[str] = None) -> dict:
        positions = await self.exchange.fetch_positions([symbol])
        for pos in positions:
            if float(pos["contracts"]) > 0:
                side = "sell" if pos["side"] == "long" else "buy"
                return await self.place_order(symbol, side, float(pos["contracts"]))
        return {"status": "no_position"}

    async def get_open_positions(self) -> list[dict]:
        positions = await self.exchange.fetch_positions()
        return [
            {
                "symbol": p["symbol"],
                "side": p["side"],
                "size": float(p["contracts"]),
                "entry_price": float(p["entryPrice"]) if p["entryPrice"] else 0,
                "unrealized_pnl": float(p["unrealizedPnl"]) if p["unrealizedPnl"] else 0,
                "leverage": p["leverage"],
            }
            for p in positions
            if float(p["contracts"]) > 0
        ]

    async def get_balance(self) -> dict:
        balance = await self.exchange.fetch_balance()
        return {
            "total": balance.get("total", {}).get("USDT", 0),
            "free": balance.get("free", {}).get("USDT", 0),
            "used": balance.get("used", {}).get("USDT", 0),
            "currency": "USDT",
        }
