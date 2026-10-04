"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  fetchBots,
  fetchStrategies,
  fetchSymbols,
  startBot,
  stopBot,
  Bot,
  Strategy,
  Symbol,
} from "@/lib/api";

const TIMEFRAMES = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"];

export default function BotPage() {
  const [symbols, setSymbols] = useState<Symbol[]>([]);
  const [symbol, setSymbol] = useState("BTC/USDT");
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [strategyId, setStrategyId] = useState("sma_crossover");
  const [strategyParams, setStrategyParams] = useState<Record<string, number>>({});
  const [timeframe, setTimeframe] = useState("1h");
  const [checkInterval, setCheckInterval] = useState(60);
  const [bots, setBots] = useState<Bot[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    fetchSymbols().then(setSymbols).catch(() => {});
    fetchStrategies().then(setStrategies).catch(() => {});
    loadBots();
    const interval = setInterval(loadBots, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const strat = strategies.find((s) => s.id === strategyId);
    if (strat) {
      setStrategyParams({ ...strat.params });
    }
  }, [strategyId, strategies]);

  const loadBots = async () => {
    try {
      setBots(await fetchBots());
    } catch {
      // Backend might not be running
    }
  };

  const handleStart = async () => {
    setLoading(true);
    setError("");
    setMessage("");
    try {
      const result = await startBot({
        symbol,
        strategy: strategyId,
        params: strategyParams,
        timeframe,
        check_interval: checkInterval,
      });
      setMessage(result.message);
      await loadBots();
    } catch (err: any) {
      setError(err.message || "Failed to start bot");
    }
    setLoading(false);
  };

  const handleStop = async (botId: string) => {
    try {
      const result = await stopBot(botId);
      setMessage(result.message);
      await loadBots();
    } catch (err: any) {
      setError(err.message || "Failed to stop bot");
    }
  };

  return (
    <div>
      <nav className="nav">
        <span className="nav-logo">Orbis</span>
        <Link href="/">Dashboard</Link>
        <Link href="/backtest">Backtest</Link>
        <Link href="/trade">Trade</Link>
        <Link href="/bot" className="active">Bot</Link>
      </nav>

      <div className="container">
        <div className="card" style={{ marginBottom: 16 }}>
          <h3 style={{ marginBottom: 4, fontSize: 16 }}>Start an Automated Bot</h3>
          <p style={{ marginBottom: 16, fontSize: 13, color: "var(--text-secondary)" }}>
            Runs a strategy live: checks for a signal on an interval and executes trades through
            the same risk-managed order path as manual trading.
          </p>
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
              <label>Timeframe</label>
              <select value={timeframe} onChange={(e) => setTimeframe(e.target.value)}>
                {TIMEFRAMES.map((tf) => (
                  <option key={tf} value={tf}>{tf}</option>
                ))}
              </select>
            </div>
            <div>
              <label>Check Interval (s)</label>
              <input
                type="number"
                value={checkInterval}
                onChange={(e) => setCheckInterval(parseInt(e.target.value))}
                min={5}
                style={{ width: 90 }}
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

            <button className="btn btn-primary" onClick={handleStart} disabled={loading}>
              {loading ? "Starting..." : "Start Bot"}
            </button>
          </div>
        </div>

        {error && (
          <div className="card" style={{ marginBottom: 16, borderColor: "var(--red)" }}>
            <p style={{ color: "var(--red)" }}>{error}</p>
          </div>
        )}

        {message && !error && (
          <div className="card" style={{ marginBottom: 16 }}>
            <p style={{ color: "var(--text-secondary)", fontSize: 13 }}>{message}</p>
          </div>
        )}

        <div className="card">
          <h3 style={{ marginBottom: 12, fontSize: 14 }}>Active Bots</h3>
          {bots.length === 0 ? (
            <p style={{ color: "var(--text-secondary)", fontSize: 13 }}>No bots running.</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Strategy</th>
                  <th>Status</th>
                  <th>Trades</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {bots.map((b) => (
                  <tr key={b.id}>
                    <td>{b.symbol}</td>
                    <td>{b.strategy}</td>
                    <td className={b.running ? "positive" : "negative"}>
                      {b.running ? "● RUNNING" : "STOPPED"}
                    </td>
                    <td>{b.trades}</td>
                    <td>
                      <button
                        className="btn"
                        style={{ background: "var(--border)", color: "var(--text-primary)", padding: "6px 12px" }}
                        onClick={() => handleStop(b.id)}
                        disabled={!b.running}
                      >
                        Stop
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
