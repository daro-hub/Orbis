# Orbis — Algorithmic Trading Platform

Full-stack trading platform with backtesting for Bitcoin, NASDAQ 100, and Gold (XAU/USD).

## The idea

A trading idea almost never works on the first try. It has to be backtested to find where it fails, corrected, and tested again — repeatedly, until it becomes consistently profitable. Orbis is built toward eventually automating that whole loop with AI agents that write a strategy, backtest it, read the results, and revise it on their own, then keep monitoring and adjusting it over time as conditions change.

Today the strategies and their tuning are still done by hand — the self-correcting agent loop is the direction the project is being built toward.

A further idea for later: AI models answer based on probability learned from past examples, and the same structure could apply to price data — training a model on an asset's historical movements to estimate the probability that a pattern repeats, and trading on that probabilistic prediction.

## What it does

- **Dashboard** — real-time candlestick charts for BTC, NASDAQ, Gold
- **Backtest** — test a strategy against historical data with full performance metrics before risking anything
- **Trade** — open/close positions manually on all three assets
- **Bot** — start automated bots that run a strategy in real time

## Strategies included

1. **SMA Crossover** — moving average crossover (parameters: `fast_period`, `slow_period`)
2. **RSI Strategy** — overbought/oversold (parameters: `period`, `oversold`, `overbought`)

Strategies are plugged in via a small registry (`strategies/registry.py`) instead of an `if/elif` over hardcoded classes: a new strategy just implements `BaseStrategy.generate_signals` and adds one `@register_strategy("id")` decorator, and it's immediately available to the backtester, the live bot, and the `/api/backtest/strategies` listing — no other file needs to change. This is also the extension point the self-correcting agent loop (see "The idea" above) would write into.

## Stack

- **Backend:** FastAPI (Python) — broker connectors, backtesting engine, strategy execution
- **Frontend:** Next.js — dashboard, backtest UI, manual trading

## Requirements

- Python >= 3.10
- Node.js >= 18

## Local setup

### 1. API keys

Copy `backend/.env.example` to `backend/.env` and fill in your credentials (never committed):

```bash
cp backend/.env.example backend/.env
```

```env
BINANCE__API_KEY=your-binance-testnet-api-key
BINANCE__API_SECRET=your-binance-testnet-api-secret
BINANCE__TESTNET=true
```

Binance testnet keys: [testnet.binance.vision](https://testnet.binance.vision/). This alone is enough to run everything BTC-related (dashboard, backtest, live prices).

Capital.com (NASDAQ/Gold) is optional — the backend boots fine without it and `/api/symbols` reports those two as `available: false` instead of the app crashing on missing config. To enable them, get a [Capital.com](https://capital.com/) demo account and add:

```env
CAPITAL__API_KEY=your-capital-api-key
CAPITAL__IDENTIFIER=your-capital-email
CAPITAL__PASSWORD=your-capital-password
CAPITAL__DEMO=true
```

### 2. Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Server runs at http://localhost:8000. Interactive docs at `/docs`.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at http://localhost:3000.

## Tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

Covers the backtesting engine and metrics: correct PnL/commission accounting, no look-ahead bias (a signal read from bar *i* only fills at bar *i+1*'s open, never at bar *i*'s own close), Sharpe annualized for the actual bar spacing instead of a hardcoded trading-day count, and the strategy registry.

## Reliability

- Read-only broker calls (price, history, balance, positions) retry with exponential backoff on transient network errors; order placement never auto-retries, since retrying a write that may have already gone through risks a duplicate order.
- The live Binance price WebSocket reconnects with backoff on any drop instead of dying silently; cached prices older than 30s are flagged `stale` so the UI can show that instead of a frozen "● LIVE".
- `CapitalConnector` offloads its (synchronous) HTTP calls to a thread so a slow Capital.com response can't block the whole event loop, including unrelated Binance/websocket traffic.

## Auth & CORS

Order placement and bot start/stop are open by default for local dev. Set `API_KEY` in `.env` to require an `X-API-Key` header on those endpoints, and `ALLOWED_ORIGINS` (comma-separated) to restrict which frontend origins the API accepts requests from — see `backend/.env.example`.

## API endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/symbols` | List available symbols |
| GET | `/api/prices/{symbol}` | Current price |
| GET | `/api/history/{symbol}` | Historical candle data |
| POST | `/api/orders` | Place an order |
| GET | `/api/positions` | Open positions |
| DELETE | `/api/positions/{symbol}` | Close a position |
| GET | `/api/balance` | Account balance |
| POST | `/api/backtest` | Run a backtest |
| GET | `/api/backtest/strategies` | Available strategies |
| POST | `/api/bot/start` | Start an automated bot |
| POST | `/api/bot/stop/{id}` | Stop a bot |
| GET | `/api/bot/list` | List active bots |

## Project structure

```
orbis/
├── backend/
│   ├── main.py                    # FastAPI server, symbol -> broker dispatch
│   ├── config.py                  # Env-based settings (pydantic-settings)
│   ├── connectors/
│   │   ├── base.py                # BaseConnector interface all brokers implement
│   │   ├── binance_connector.py   # BTC/USDT via ccxt
│   │   ├── capital_connector.py   # NASDAQ/Gold via Capital.com (optional)
│   │   ├── resilience.py          # Retry-with-backoff decorator for read calls
│   │   └── websocket_stream.py    # Live price stream with auto-reconnect
│   ├── backtester/
│   │   ├── engine.py              # Event-driven backtest, no look-ahead
│   │   └── metrics.py             # Sharpe/drawdown/profit factor
│   ├── trading/
│   │   ├── bot.py                 # Live strategy execution loop
│   │   ├── executor.py            # Order validation/logging
│   │   └── risk.py                # Position sizing, exposure limits
│   ├── strategies/
│   │   ├── base.py                # BaseStrategy interface
│   │   ├── registry.py            # @register_strategy — pluggable, no if/elif
│   │   └── example_sma.py         # SMA Crossover + RSI
│   ├── tests/                     # pytest: engine, metrics, registry
│   ├── data/historical/           # Historical CSV data (gitignored)
│   ├── results/                   # Backtest result JSONs (gitignored)
│   └── .env                       # Credentials, from .env.example (do NOT commit)
└── frontend/
    └── src/
        ├── app/           # Next.js pages
        ├── components/    # React components
        └── lib/           # API client
```
