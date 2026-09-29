import asyncio
import time
import requests
import pandas as pd
from typing import Optional
from .base import BaseConnector
from .resilience import with_retry

_TRANSIENT = (requests.exceptions.ConnectionError, requests.exceptions.Timeout)
_retry = with_retry(_TRANSIENT)


class CapitalConnector(BaseConnector):
    """Connector for Capital.com API (NASDAQ and Gold CFD trading).

    `requests` is synchronous, so every call is offloaded to a thread via
    asyncio.to_thread — otherwise a slow Capital.com response would block
    the whole FastAPI event loop, including unrelated Binance/websocket
    traffic being served at the same time.
    """

    DEMO_URL = "https://demo-api-capital.backend-capital.com"
    LIVE_URL = "https://api-capital.backend-capital.com"

    def __init__(self, api_key: str, identifier: str, password: str, demo: bool = True):
        self.api_key = api_key
        self.identifier = identifier
        self.password = password
        self.base_url = self.DEMO_URL if demo else self.LIVE_URL
        self.cst: Optional[str] = None
        self.security_token: Optional[str] = None
        self.session_time: float = 0

    def _ensure_session(self):
        """Create or refresh session if expired (10 min timeout)."""
        if self.cst and (time.time() - self.session_time) < 540:
            return
        self._create_session()

    def _create_session(self):
        url = f"{self.base_url}/api/v1/session"
        headers = {"X-CAP-API-KEY": self.api_key, "Content-Type": "application/json"}
        payload = {
            "identifier": self.identifier,
            "password": self.password,
            "encryptedPassword": False,
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        self.cst = resp.headers.get("CST")
        self.security_token = resp.headers.get("X-SECURITY-TOKEN")
        self.session_time = time.time()

    def _headers(self) -> dict:
        self._ensure_session()
        return {
            "X-CAP-API-KEY": self.api_key,
            "CST": self.cst,
            "X-SECURITY-TOKEN": self.security_token,
            "Content-Type": "application/json",
        }

    @_retry
    async def get_historical_data(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 500,
        since: Optional[int] = None,
    ) -> pd.DataFrame:
        resolution_map = {
            "1m": "MINUTE",
            "5m": "MINUTE_5",
            "15m": "MINUTE_15",
            "30m": "MINUTE_30",
            "1h": "HOUR",
            "4h": "HOUR_4",
            "1d": "DAY",
            "1w": "WEEK",
        }
        resolution = resolution_map.get(timeframe, "HOUR")

        url = f"{self.base_url}/api/v1/prices/{symbol}"
        params = {"resolution": resolution, "max": min(limit, 1000)}
        if since:
            from datetime import datetime, timezone
            params["from"] = datetime.fromtimestamp(since / 1000, tz=timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%S"
            )

        data = await asyncio.to_thread(self._get_json, url, params)

        prices = data.get("prices", [])
        if not prices:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

        rows = []
        for p in prices:
            rows.append({
                "timestamp": pd.to_datetime(p["snapshotTime"]),
                "open": (p["openPrice"]["bid"] + p["openPrice"]["ask"]) / 2,
                "high": (p["highPrice"]["bid"] + p["highPrice"]["ask"]) / 2,
                "low": (p["lowPrice"]["bid"] + p["lowPrice"]["ask"]) / 2,
                "close": (p["closePrice"]["bid"] + p["closePrice"]["ask"]) / 2,
                "volume": p.get("lastTradedVolume", 0),
            })

        df = pd.DataFrame(rows)
        df.set_index("timestamp", inplace=True)
        return df

    @_retry
    async def get_current_price(self, symbol: str) -> dict:
        url = f"{self.base_url}/api/v1/markets/{symbol}"
        data = await asyncio.to_thread(self._get_json, url)
        snapshot = data.get("snapshot", {})
        return {
            "symbol": symbol,
            "bid": snapshot.get("bid"),
            "ask": snapshot.get("offer"),
            "last": (snapshot.get("bid", 0) + snapshot.get("offer", 0)) / 2,
            "timestamp": int(time.time() * 1000),
        }

    async def place_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "market",
        price: Optional[float] = None,
    ) -> dict:
        direction = "BUY" if side.lower() == "buy" else "SELL"
        payload = {
            "epic": symbol,
            "direction": direction,
            "size": quantity,
        }
        if order_type == "limit" and price:
            payload["level"] = price
            payload["type"] = "LIMIT"

        data = await asyncio.to_thread(self._post_json, f"{self.base_url}/api/v1/positions", payload)
        return {
            "id": data.get("dealReference"),
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity,
            "price": price,
            "status": data.get("dealStatus", "ACCEPTED"),
            "timestamp": int(time.time() * 1000),
        }

    async def close_position(self, symbol: str, position_id: Optional[str] = None) -> dict:
        if not position_id:
            positions = await self.get_open_positions()
            for p in positions:
                if p["symbol"] == symbol:
                    position_id = p["id"]
                    break
            if not position_id:
                return {"status": "no_position"}

        url = f"{self.base_url}/api/v1/positions/{position_id}"
        await asyncio.to_thread(self._delete, url)
        return {"status": "closed", "id": position_id}

    @_retry
    async def get_open_positions(self) -> list[dict]:
        data = await asyncio.to_thread(self._get_json, f"{self.base_url}/api/v1/positions")
        positions = data.get("positions", [])
        return [
            {
                "id": p["position"]["dealId"],
                "symbol": p["market"]["epic"],
                "side": p["position"]["direction"].lower(),
                "size": p["position"]["size"],
                "entry_price": p["position"]["level"],
                "unrealized_pnl": p["position"].get("upl", 0),
            }
            for p in positions
        ]

    @_retry
    async def get_balance(self) -> dict:
        data = await asyncio.to_thread(self._get_json, f"{self.base_url}/api/v1/accounts")
        accounts = data.get("accounts", [])
        if accounts:
            acc = accounts[0]
            return {
                "total": acc.get("balance", 0),
                "free": acc.get("available", 0),
                "used": acc.get("balance", 0) - acc.get("available", 0),
                "currency": acc.get("currency", "USD"),
            }
        return {"total": 0, "free": 0, "used": 0, "currency": "USD"}

    # --- blocking helpers, always called through asyncio.to_thread above ---

    def _get_json(self, url: str, params: Optional[dict] = None) -> dict:
        resp = requests.get(url, headers=self._headers(), params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def _post_json(self, url: str, payload: dict) -> dict:
        resp = requests.post(url, json=payload, headers=self._headers(), timeout=10)
        resp.raise_for_status()
        return resp.json()

    def _delete(self, url: str) -> None:
        resp = requests.delete(url, headers=self._headers(), timeout=10)
        resp.raise_for_status()
