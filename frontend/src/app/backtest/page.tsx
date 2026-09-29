"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import Chart from "@/components/Chart";
import BacktestResults from "@/components/BacktestResults";
import { fetchHistory, fetchStrategies, fetchSymbols, runBacktest, CandleData, Strategy, BacktestResult, Symbol } from "@/lib/api";

const TIMEFRAMES = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"];

export default function BacktestPage() {
  const [symbols, setSymbols] = useState<Symbol[]>([]);
  const [symbol, setSymbol] = useState("BTC/USDT");
  const [timeframe, setTimeframe] = useState("1h");
  const [limit, setLimit] = useState(500);
  const [strategyId, setStrategyId] = useState("sma_crossover");
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [strategyParams, setStrategyParams] = useState<Record<string, number>>({});
  const [capital, setCapital] = useState(10000);
  const [results, setResults] = useState<BacktestResult | null>(null);
  const [chartData, setChartData] = useState<CandleData[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    loadStrategies();
    fetchSymbols().then(setSymbols).catch(() => {});
  }, []);

  useEffect(() => {
    const strat = strategies.find((s) => s.id === strategyId);
    if (strat) {
      setStrategyParams({ ...strat.params });
    }
  }, [strategyId, strategies]);

  const loadStrategies = async () => {
    try {
      const strats = await fetchStrategies();
      setStrategies(strats);
    } catch {
      // Backend might not be running
    }
  };

  const handleRunBacktest = async () => {
    setLoading(true);
    setError("");
    setResults(null);
    try {
      const [history, btResult] = await Promise.all([
        fetchHistory(symbol, timeframe, limit),
        runBacktest({
          symbol,
          timeframe,
          limit,
          strategy: strategyId,
          params: strategyParams,
          initial_capital: capital,
        }),
      ]);
      setChartData(history);
      setResults(btResult);
    } catch (err: any) {
      setError(err.message || "Backtest failed");
    }
    setLoading(false);
  };

  const signalMarkers = results?.signals.map((s) => {
    const candle = chartData.find((c) => c.time === Math.floor(new Date(s.timestamp).getTime() / 1000));
    return {
      time: candle?.time || Math.floor(new Date(s.timestamp).getTime() / 1000),
      position: s.signal === "buy" ? ("belowBar" as const) : ("aboveBar" as const),
      color: s.signal === "buy" ? "#22c55e" : "#ef4444",
      shape: s.signal === "buy" ? ("arrowUp" as const) : ("arrowDown" as const),
      text: s.signal.toUpperCase(),
    };
  });

  return (
    <div>
      <nav className="nav">
        <span className="nav-logo">Trading Platform</span>
        <Link href="/">Dashboard</Link>
        <Link href="/backtest" className="active">Backtest</Link>
        <Link href="/trade">Trade</Link>
      </nav>

      <div className="container">
        <div className="card" style={{ marginBottom: 16 }}>
          <h3 style={{ marginBottom: 16, fontSize: 16 }}>Backtest Configuration</h3>
          <div style={{ display: "flex", gap: 16, flexWrap: "wrap", alignItems: "flex-end" }}>
            <div>
              <label>Symbol</label>
              <select value={symbol} onChange={(e) => setSymbol(e.target.value)}>
                {symbols.map((s) => (
                  <option key={s.id} value={s.id} disabled={!s.available}>
                    {s.name}{!s.available ? " (not configured)" : ""}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label>Timeframe</label>
              <select value={timeframe} onChange={(e) => setTimeframe(e.target.value)}>
                {TIMEFRAMES.map((tf) => (
                  <option key={tf} value={tf}>{tf}</option>
                ))}
              </select>
            </div>
            <div>
              <label>Candles</label>
              <input
                type="number"
                value={limit}
                onChange={(e) => setLimit(parseInt(e.target.value))}
                min={100}
                max={5000}
                style={{ width: 80 }}
              />
            </div>
            <div>
              <label>Strategy</label>
              <select value={strategyId} onChange={(e) => setStrategyId(e.target.value)}>
                {strategies.map((s) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
                {strategies.length === 0 && (
                  <>
                    <option value="sma_crossover">SMA Crossover</option>
                    <option value="rsi">RSI Strategy</option>
                  </>
                )}
              </select>
            </div>
            <div>
              <label>Capital ($)</label>
              <input
                type="number"
                value={capital}
                onChange={(e) => setCapital(parseInt(e.target.value))}
                min={100}
                style={{ width: 100 }}
              />
            </div>

            {Object.entries(strategyParams).map(([key, val]) => (
              <div key={key}>
                <label>{key}</label>
                <input
                  type="number"
                  value={val}
                  onChange={(e) =>
                    setStrategyParams((prev) => ({ ...prev, [key]: parseFloat(e.target.value) }))
                  }
                  style={{ width: 70 }}
                />
              </div>
            ))}

            <button className="btn btn-primary" onClick={handleRunBacktest} disabled={loading}>
              {loading ? "Running..." : "Run Backtest"}
            </button>
          </div>
        </div>

        {error && (
          <div className="card" style={{ marginBottom: 16, borderColor: "var(--red)" }}>
            <p style={{ color: "var(--red)" }}>{error}</p>
          </div>
        )}

        {chartData.length > 0 && (
          <div className="card" style={{ marginBottom: 16 }}>
            <Chart data={chartData} markers={signalMarkers} />
          </div>
        )}

        {results && (
          <BacktestResults
            metrics={results.metrics}
            trades={results.trades}
            equityCurve={results.equity_curve}
          />
        )}
      </div>
    </div>
  );
}
