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

CAPITAL__API_KEY=your-capital-api-key
CAPITAL__IDENTIFIER=your-capital-email
CAPITAL__PASSWORD=your-capital-password
CAPITAL__DEMO=true
```

Binance testnet keys: [testnet.binance.vision](https://testnet.binance.vision/). Capital.com demo account: [capital.com](https://capital.com/).

### 2. Backend

```bash
cd backend
pip install -r requirements.txt
python main.py
```

Server runs at http://localhost:8000.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at http://localhost:3000.

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
│   ├── main.py            # FastAPI server
│   ├── config.py          # Configuration
│   ├── connectors/        # Broker connections
│   ├── backtester/        # Backtesting engine
│   ├── trading/           # Order execution and bots
│   ├── strategies/        # Trading strategies
│   ├── data/historical/   # Historical CSV data
│   ├── results/           # Backtest result JSONs
│   └── .env               # Credentials, from .env.example (do NOT commit)
└── frontend/
    └── src/
        ├── app/           # Next.js pages
        ├── components/    # React components
        └── lib/           # API client
```
