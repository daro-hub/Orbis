import ccxt.async_support as ccxt
import pandas as pd
from typing import Optional
from .base import BaseConnector
from .resilience import with_retry

# Transient failures worth a retry: connectivity blips, rate limiting,
# exchange briefly unavailable. Anything else (bad symbol, insufficient
# funds, auth) is a real error and should surface immediately.
_TRANSIENT = (ccxt.NetworkError, ccxt.ExchangeNotAvailable, ccxt.RequestTimeout, ccxt.DDoSProtection)
_retry = with_retry(_TRANSIENT)


class BinanceConnector(BaseConnector):
    """Connector for Binance exchange via ccxt (Bitcoin spot trading)."""

    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        self.exchange = ccxt.binance({
            "apiKey": api_key,
            "secret": api_secret,
            "options": {"defaultType": "spot"},
        })
        if testnet:
            self.exchange.set_sandbox_mode(True)

    async def close(self):
        await self.exchange.close()

    @_retry
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

    @_retry
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
        order = await self.exchange.create_order(
            symbol=symbol,
            type=order_type,
            side=side,
            amount=quantity,
            price=price,
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
        # For spot trading, "closing" means selling all holdings of the base asset
        balance = await self.exchange.fetch_balance()
        base_currency = symbol.split("/")[0]  # e.g. "BTC" from "BTC/USDT"
        available = float(balance.get("free", {}).get(base_currency, 0))
        if available > 0:
            return await self.place_order(symbol, "sell", available)
        return {"status": "no_position"}

    @_retry
    async def get_open_positions(self) -> list[dict]:
        balance = await self.exchange.fetch_balance()
        positions = []
        for currency, amount in balance.get("total", {}).items():
            if currency in ("USDT", "USD", "EUR") or float(amount) == 0:
                continue
            if float(amount) > 0:
                symbol = f"{currency}/USDT"
                try:
                    ticker = await self.exchange.fetch_ticker(symbol)
                    value = float(amount) * ticker["last"]
                    if value > 1:  # Only show positions worth > $1
                        positions.append({
                            "symbol": symbol,
                            "side": "long",
                            "size": float(amount),
                            "entry_price": 0,  # Spot doesn't track entry price
                            "unrealized_pnl": 0,
                            "current_value": value,
                        })
                except Exception:
                    continue
        return positions

    @_retry
    async def get_balance(self) -> dict:
        balance = await self.exchange.fetch_balance()
        return {
            "total": balance.get("total", {}).get("USDT", 0),
            "free": balance.get("free", {}).get("USDT", 0),
            "used": balance.get("used", {}).get("USDT", 0),
            "currency": "USDT",
        }
