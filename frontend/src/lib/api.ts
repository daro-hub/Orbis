const API_BASE = "/api";

export interface CandleData {
  time: number;
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface Symbol {
  id: string;
  name: string;
  broker: string;
  available: boolean;
}

export interface BacktestResult {
  status: string;
  metrics: Record<string, number>;
  trades: Array<{
    side: string;
    entry_price: number;
    exit_price: number;
    entry_time: string;
    exit_time: string;
    pnl: number;
    pnl_pct: number;
  }>;
  equity_curve: number[];
  signals: Array<{
    timestamp: string;
    signal: string;
    price: number;
    index: number;
  }>;
}

export interface Strategy {
  id: string;
  name: string;
  params: Record<string, number>;
}

export async function fetchSymbols(): Promise<Symbol[]> {
  const res = await fetch(`${API_BASE}/symbols`);
  const data = await res.json();
  return data.symbols;
}

export async function fetchHistory(
  symbol: string,
  timeframe: string = "1h",
  limit: number = 500
): Promise<CandleData[]> {
  const res = await fetch(
    `${API_BASE}/history/${encodeURIComponent(symbol)}?timeframe=${timeframe}&limit=${limit}`
  );
  const data = await res.json();
  return data.data;
}

export async function fetchPrice(symbol: string) {
  const res = await fetch(`${API_BASE}/prices/${encodeURIComponent(symbol)}`);
  return res.json();
}

export function subscribePrices(
  onUpdate: (prices: Record<string, { last: number; bid: number; ask: number; change_pct?: number }>) => void
): () => void {
  const es = new EventSource(`${API_BASE}/stream/prices`);
  es.onmessage = (e) => {
    try {
      onUpdate(JSON.parse(e.data));
    } catch {}
  };
  return () => es.close();
}

export async function fetchStrategies(): Promise<Strategy[]> {
  const res = await fetch(`${API_BASE}/backtest/strategies`);
  const data = await res.json();
  return data.strategies;
}

export async function runBacktest(params: {
  symbol: string;
  timeframe: string;
  limit: number;
  strategy: string;
  params: Record<string, number>;
  initial_capital: number;
}): Promise<BacktestResult> {
  const res = await fetch(`${API_BASE}/backtest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Backtest failed");
  }
  return res.json();
}

export async function placeOrder(params: {
  symbol: string;
  side: string;
  quantity: number;
  order_type?: string;
  price?: number;
}) {
  const res = await fetch(`${API_BASE}/orders`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Order failed");
  }
  return res.json();
}

export async function fetchPositions() {
  const res = await fetch(`${API_BASE}/positions`);
  return res.json();
}

export async function closePosition(symbol: string) {
  const res = await fetch(`${API_BASE}/positions/${encodeURIComponent(symbol)}`, { method: "DELETE" });
  return res.json();
}

export async function fetchBalance() {
  const res = await fetch(`${API_BASE}/balance`);
  return res.json();
}

export interface Bot {
  id: string;
  symbol: string;
  strategy: string;
  params: Record<string, number>;
  running: boolean;
  trades: number;
}

export async function fetchBots(): Promise<Bot[]> {
  const res = await fetch(`${API_BASE}/bot/list`);
  const data = await res.json();
  return data.bots;
}

export async function startBot(params: {
  symbol: string;
  strategy: string;
  params: Record<string, number>;
  timeframe: string;
  check_interval: number;
}) {
  const res = await fetch(`${API_BASE}/bot/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to start bot");
  }
  return res.json();
}

export async function stopBot(botId: string) {
  const res = await fetch(`${API_BASE}/bot/stop/${encodeURIComponent(botId)}`, { method: "POST" });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to stop bot");
  }
  return res.json();
}