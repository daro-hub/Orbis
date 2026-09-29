import asyncio
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from config import load_config
from connectors.binance_connector import BinanceConnector
from connectors.websocket_stream import BinanceWebSocket, price_cache
from strategies.example_sma import SMAcrossoverStrategy, RSIStrategy
from backtester.engine import BacktestEngine


# ---------------------------------------------------------------------------
# Load config
# ---------------------------------------------------------------------------

cfg = load_config()

binance_cfg = cfg.binance
connector = BinanceConnector(
    api_key=binance_cfg.api_key,
    api_secret=binance_cfg.api_secret,
    testnet=binance_cfg.testnet,
)

ws_stream: Optional[BinanceWebSocket] = None


# ---------------------------------------------------------------------------
# Startup / shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    global ws_stream
    ws_stream = BinanceWebSocket(testnet=binance_cfg.testnet)
    try:
        await ws_stream.connect(["BTC/USDT"])
        asyncio.create_task(ws_stream.listen())
    except Exception:
        ws_stream = None

    yield

    if ws_stream:
        await ws_stream.disconnect()
    await connector.close()


app = FastAPI(title="Trading Platform API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Symbols
# ---------------------------------------------------------------------------

SYMBOLS = [
    {"id": "BTC/USDT", "name": "Bitcoin / USDT", "broker": "binance"},
]


@app.get("/api/symbols")
async def get_symbols():
    return {"symbols": SYMBOLS}


# ---------------------------------------------------------------------------
# Prices
# ---------------------------------------------------------------------------

@app.get("/api/prices/{symbol:path}")
async def get_price(symbol: str):
    cached = price_cache.get(symbol)
    if cached:
        return {"symbol": symbol, **cached}
    try:
        return await connector.get_current_price(symbol)
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
        raise HTTPException(status_code=502, detail=str(e))


# ---------------------------------------------------------------------------
# Balance & positions
# ---------------------------------------------------------------------------

@app.get("/api/balance")
async def get_balance():
    try:
        return await connector.get_balance()
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/api/positions")
async def get_positions():
    try:
        positions = await connector.get_open_positions()
        return {"positions": positions}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------

class OrderRequest(BaseModel):
    symbol: str
    side: str
    quantity: float
    order_type: str = "market"
    price: Optional[float] = None


@app.post("/api/orders")
async def place_order(req: OrderRequest):
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


@app.delete("/api/positions/{symbol:path}")
async def close_position(symbol: str):
    try:
        return await connector.close_position(symbol)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


# ---------------------------------------------------------------------------
# Backtest
# ---------------------------------------------------------------------------

STRATEGIES = {
    "sma_crossover": {
        "name": "SMA Crossover",
        "params": {"fast_period": 10, "slow_period": 30},
    },
    "rsi": {
        "name": "RSI Strategy",
        "params": {"period": 14, "oversold": 30, "overbought": 70},
    },
}


@app.get("/api/backtest/strategies")
async def list_strategies():
    return {
        "strategies": [
            {"id": k, "name": v["name"], "params": v["params"]}
            for k, v in STRATEGIES.items()
        ]
    }


class BacktestRequest(BaseModel):
    symbol: str
    timeframe: str = "1h"
    limit: int = 500
    strategy: str = "sma_crossover"
    params: dict = {}
    initial_capital: float = 10000.0


@app.post("/api/backtest")
async def run_backtest(req: BacktestRequest):
    if req.strategy not in STRATEGIES:
        raise HTTPException(status_code=400, detail=f"Unknown strategy: {req.strategy}")

    try:
        df = await connector.get_historical_data(req.symbol, timeframe=req.timeframe, limit=req.limit)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch data: {e}")

    merged_params = {**STRATEGIES[req.strategy]["params"], **req.params}

    if req.strategy == "sma_crossover":
        strategy = SMAcrossoverStrategy(
            fast_period=int(merged_params.get("fast_period", 10)),
            slow_period=int(merged_params.get("slow_period", 30)),
        )
    else:
        strategy = RSIStrategy(
            period=int(merged_params.get("period", 14)),
            oversold=float(merged_params.get("oversold", 30)),
            overbought=float(merged_params.get("overbought", 70)),
        )

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
# Health check
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health():
    return {"status": "ok"}
