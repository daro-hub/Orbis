import asyncio
import json
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from config import load_config
from connectors.base import BaseConnector
from connectors.binance_connector import BinanceConnector
from connectors.capital_connector import CapitalConnector
from connectors.websocket_stream import BinanceWebSocket, price_cache
from backtester.engine import BacktestEngine
import strategies  # noqa: F401 - side effect: registers built-in strategies
from strategies.registry import create_strategy, describe_strategies
import trading.bot as bot_module

# ---------------------------------------------------------------------------
# Config & connectors
# ---------------------------------------------------------------------------

cfg = load_config()

connectors: dict[str, BaseConnector] = {
    "binance": BinanceConnector(
        api_key=cfg.binance.api_key,
        api_secret=cfg.binance.api_secret,
        testnet=cfg.binance.testnet,
    ),
}
if cfg.capital is not None:
    connectors["capital"] = CapitalConnector(
        api_key=cfg.capital.api_key,
        identifier=cfg.capital.identifier,
        password=cfg.capital.password,
        demo=cfg.capital.demo,
    )

# Static symbol -> broker map. NASDAQ/Gold stay listed even when Capital.com
# isn't configured, but flagged unavailable, so the frontend can grey them
# out instead of discovering a 503 only after the user clicks them.
SYMBOLS = [
    {"id": cfg.symbols.bitcoin, "name": "Bitcoin", "broker": "binance"},
    {"id": cfg.symbols.nasdaq, "name": "NASDAQ 100", "broker": "capital"},
    {"id": cfg.symbols.gold, "name": "Gold (XAU/USD)", "broker": "capital"},
]
_SYMBOL_BROKER = {s["id"]: s["broker"] for s in SYMBOLS}


def get_connector(symbol: str) -> BaseConnector:
    broker = _SYMBOL_BROKER.get(symbol)
    if broker is None:
        raise HTTPException(status_code=404, detail=f"Unknown symbol: {symbol}")
    connector = connectors.get(broker)
    if connector is None:
        raise HTTPException(
            status_code=503,
            detail=f"{broker} is not configured on this server (missing credentials)",
        )
    return connector


def require_api_key(x_api_key: Optional[str] = Header(default=None)):
    """No-op when API_KEY isn't set (local dev); enforced once it is."""
    if cfg.api_key and x_api_key != cfg.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")


ws_stream: Optional[BinanceWebSocket] = None
ws_task: Optional[asyncio.Task] = None


# ---------------------------------------------------------------------------
# Startup / shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    global ws_stream, ws_task
    ws_stream = BinanceWebSocket(testnet=cfg.binance.testnet)
    ws_task = asyncio.create_task(ws_stream.run([cfg.symbols.bitcoin]))

    yield

    if ws_stream:
        await ws_stream.disconnect()
    if ws_task:
        ws_task.cancel()
    for connector in connectors.values():
        close = getattr(connector, "close", None)
        if close:
            await close()


app = FastAPI(title="Trading Platform API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cfg.allowed_origins_list,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "X-API-Key"],
)


# ---------------------------------------------------------------------------
# Symbols
# ---------------------------------------------------------------------------

@app.get("/api/symbols")
async def get_symbols():
    return {
        "symbols": [
            {**s, "available": s["broker"] in connectors} for s in SYMBOLS
        ]
    }


# ---------------------------------------------------------------------------
# Prices
# ---------------------------------------------------------------------------

@app.get("/api/prices/{symbol:path}")
async def get_price(symbol: str):
    cached = price_cache.get(symbol)
    if cached:
        return {"symbol": symbol, **cached}
    try:
        connector = get_connector(symbol)
        return await connector.get_current_price(symbol)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/api/stream/prices")
async def stream_prices():
    """SSE endpoint — pushes price updates every second."""
    async def event_generator():
        while True:
            all_prices = price_cache.get_all()
            if all_prices:
                payload = json.dumps(all_prices)
                yield f"data: {payload}\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# Historical data
# ---------------------------------------------------------------------------

@app.get("/api/history/{symbol:path}")
async def get_history(symbol: str, timeframe: str = "1h", limit: int = 500):
    connector = get_connector(symbol)
    try:
        df = await connector.get_historical_data(symbol, timeframe=timeframe, limit=limit)
        records = []
        for ts, row in df.iterrows():
            records.append({
                "time": int(ts.timestamp()),
                "timestamp": str(ts),
                "open": round(float(row["open"]), 4),
                "high": round(float(row["high"]), 4),
                "low": round(float(row["low"]), 4),
                "close": round(float(row["close"]), 4),
                "volume": round(float(row["volume"]), 4),
            })
        return {"symbol": symbol, "timeframe": timeframe, "data": records}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch data: {e}")


# ---------------------------------------------------------------------------
# Balance & positions
# ---------------------------------------------------------------------------

@app.get("/api/balance")
async def get_balance():
    """Per-broker balances, e.g. {"binance": {...}, "capital": {...}}.
    A broker that isn't configured, or that errors, reports {"error": ...}
    under its own key instead of failing the whole request."""
    result = {}
    for broker, connector in connectors.items():
        try:
            result[broker] = await connector.get_balance()
        except Exception as e:
            result[broker] = {"error": str(e)}
    for broker in ("binance", "capital"):
        result.setdefault(broker, {"error": "not configured"})
    return result


@app.get("/api/positions")
async def get_positions():
    positions = []
    for broker, connector in connectors.items():
        try:
            for p in await connector.get_open_positions():
                positions.append({**p, "broker": broker})
        except Exception:
            continue
    return {"positions": positions}


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------

class OrderRequest(BaseModel):
    symbol: str
    side: str
    quantity: float
    order_type: str = "market"
    price: Optional[float] = None


@app.post("/api/orders", dependencies=[Depends(require_api_key)])
async def place_order(req: OrderRequest):
    connector = get_connector(req.symbol)
    try:
        if req.order_type == "limit" and req.price:
            result = await connector.place_order(
                req.symbol, req.side, req.quantity, "limit", req.price
            )
        else:
            result = await connector.place_order(req.symbol, req.side, req.quantity)
        return result
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.delete("/api/positions/{symbol:path}", dependencies=[Depends(require_api_key)])
async def close_position(symbol: str):
    connector = get_connector(symbol)
    try:
        return await connector.close_position(symbol)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


# ---------------------------------------------------------------------------
# Backtest
# ---------------------------------------------------------------------------

@app.get("/api/backtest/strategies")
async def list_strategies():
    return {"strategies": describe_strategies()}


class BacktestRequest(BaseModel):
    symbol: str
    timeframe: str = "1h"
    limit: int = 500
    strategy: str = "sma_crossover"
    params: dict = {}
    initial_capital: float = 10000.0


@app.post("/api/backtest")
async def run_backtest(req: BacktestRequest):
    try:
        strategy = create_strategy(req.strategy, req.params)
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Unknown strategy: {req.strategy}")
    except TypeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid strategy params: {e}")

    connector = get_connector(req.symbol)
    try:
        df = await connector.get_historical_data(req.symbol, timeframe=req.timeframe, limit=req.limit)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch data: {e}")

    engine = BacktestEngine(strategy=strategy, initial_capital=req.initial_capital)
    results = engine.run(df)

    return {
        "status": "ok",
        "strategy": results["strategy"],
        "params": results["params"],
        "metrics": results["metrics"],
        "trades": results["trades"],
        "equity_curve": [round(e, 2) for e in results["equity_curve"]],
        "signals": results["signals"],
    }


# ---------------------------------------------------------------------------
# Bot
# ---------------------------------------------------------------------------

class BotStartRequest(BaseModel):
    symbol: str
    strategy: str = "sma_crossover"
    params: dict = {}
    timeframe: str = "1h"
    check_interval: int = 60


@app.post("/api/bot/start", dependencies=[Depends(require_api_key)])
async def bot_start(req: BotStartRequest):
    connector = get_connector(req.symbol)
    message = await bot_module.start_bot(
        symbol=req.symbol,
        strategy_id=req.strategy,
        strategy_params=req.params,
        connector=connector,
        timeframe=req.timeframe,
        check_interval=req.check_interval,
    )
    return {"message": message}


@app.post("/api/bot/stop/{bot_id}", dependencies=[Depends(require_api_key)])
async def bot_stop(bot_id: str):
    return {"message": bot_module.stop_bot(bot_id)}


@app.get("/api/bot/list")
async def bot_list():
    return {"bots": bot_module.list_bots()}


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health():
    return {"status": "ok", "brokers": list(connectors.keys())}
