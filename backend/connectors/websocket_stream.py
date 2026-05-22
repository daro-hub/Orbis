"""
WebSocket price streaming for real-time data updates.
Connects to Binance WebSocket for BTC prices.
"""

import json
import logging
from typing import Optional

import websockets

logger = logging.getLogger(__name__)


class BinanceWebSocket:
    """Real-time price stream from Binance WebSocket."""

    MAINNET_URL = "wss://stream.binance.com:9443/ws"
    TESTNET_URL = "wss://testnet.binance.vision/ws"

    def __init__(self, testnet: bool = True):
        self.base_url = self.TESTNET_URL if testnet else self.MAINNET_URL
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self._running = False

    async def connect(self, symbols: list[str]):
        """Connect to a combined stream for all given symbols (ticker)."""
        streams = "/".join(f"{s.lower().replace('/', '')}@ticker" for s in symbols)
        url = f"{self.base_url}/{streams}"
        self.ws = await websockets.connect(url, ping_interval=20)
        self._running = True
        logger.info("Binance WebSocket connected: %s", url)

    async def listen(self):
        """Listen for incoming ticker messages and update price_cache."""
        if not self.ws:
            return
        try:
            async for raw in self.ws:
                data = json.loads(raw)
                # Combined stream wraps messages in {"stream": ..., "data": {...}}
                payload = data.get("data", data)
                symbol_raw = payload.get("s", "")
                if symbol_raw:
                    symbol = _normalise_symbol(symbol_raw)
                    price_cache.update(symbol, {
                        "last": float(payload.get("c", 0)),
                        "bid": float(payload.get("b", 0)),
                        "ask": float(payload.get("a", 0)),
                        "change_pct": float(payload.get("P", 0)),
                    })
        except websockets.exceptions.ConnectionClosed:
            self._running = False
            logger.warning("Binance WebSocket connection closed")
        except Exception as e:
            self._running = False
            logger.error("Binance WebSocket error: %s", e)

    async def disconnect(self):
        self._running = False
        if self.ws:
            await self.ws.close()


def _normalise_symbol(raw: str) -> str:
    """Convert 'BTCUSDT' -> 'BTC/USDT'."""
    for quote in ("USDT", "BUSD", "BTC", "ETH", "BNB", "USD"):
        if raw.endswith(quote):
            base = raw[: -len(quote)]
            return f"{base}/{quote}"
    return raw


class PriceCache:
    """In-memory cache for latest prices."""

    def __init__(self):
        self._prices: dict[str, dict] = {}

    def update(self, symbol: str, price_data: dict):
        self._prices[symbol] = price_data

    def get(self, symbol: str) -> Optional[dict]:
        return self._prices.get(symbol)

    def get_all(self) -> dict:
        return self._prices.copy()


price_cache = PriceCache()
