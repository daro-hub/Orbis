"""
WebSocket price streaming for real-time data updates.
Connects to Binance WebSocket for BTC prices.
"""

import asyncio
import json
import logging
import time
from typing import Optional

import websockets

logger = logging.getLogger(__name__)

# Above this age, a cached price is shown as stale rather than "live" — see
# PriceCache.get_all(). Set comfortably above the reconnect backoff cap.
STALE_AFTER_SECONDS = 30.0


class BinanceWebSocket:
    """Real-time price stream from Binance WebSocket, with auto-reconnect.

    A dropped connection used to end `listen()` silently, leaving the UI
    showing a frozen "● LIVE" price forever. `run()` instead keeps
    reconnecting with backoff until `stop()` is called, and the cache marks
    prices stale once they haven't updated recently.
    """

    MAINNET_URL = "wss://stream.binance.com:9443/ws"
    TESTNET_URL = "wss://testnet.binance.vision/ws"

    def __init__(self, testnet: bool = True):
        self.base_url = self.TESTNET_URL if testnet else self.MAINNET_URL
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self._running = False

    async def run(self, symbols: list[str], max_backoff: float = 30.0):
        """Connect and listen forever, reconnecting with exponential
        backoff on any drop, until `stop()` is called."""
        self._running = True
        backoff = 1.0
        while self._running:
            try:
                await self._connect(symbols)
                backoff = 1.0  # reset once a connection succeeds
                await self._listen()
            except Exception as e:
                logger.warning("Binance WebSocket connection lost: %s", e)
            if not self._running:
                break
            logger.info("Reconnecting to Binance WebSocket in %.1fs", backoff)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, max_backoff)

    async def _connect(self, symbols: list[str]):
        streams = "/".join(f"{s.lower().replace('/', '')}@ticker" for s in symbols)
        url = f"{self.base_url}/{streams}"
        self.ws = await websockets.connect(url, ping_interval=20)
        logger.info("Binance WebSocket connected: %s", url)

    async def _listen(self):
        """Listen for incoming ticker messages and update price_cache."""
        if not self.ws:
            return
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
    """In-memory cache for latest prices, tagged with staleness so a stuck
    reconnect shows as "stale" instead of a frozen "● LIVE" price."""

    def __init__(self):
        self._prices: dict[str, dict] = {}
        self._updated_at: dict[str, float] = {}

    def update(self, symbol: str, price_data: dict):
        self._prices[symbol] = price_data
        self._updated_at[symbol] = time.time()

    def _with_staleness(self, symbol: str, price_data: dict) -> dict:
        age = time.time() - self._updated_at.get(symbol, 0)
        return {**price_data, "stale": age > STALE_AFTER_SECONDS}

    def get(self, symbol: str) -> Optional[dict]:
        if symbol not in self._prices:
            return None
        return self._with_staleness(symbol, self._prices[symbol])

    def get_all(self) -> dict:
        return {s: self._with_staleness(s, data) for s, data in self._prices.items()}


price_cache = PriceCache()
