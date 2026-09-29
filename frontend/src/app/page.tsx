"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import Chart from "@/components/Chart";
import TradePanel from "@/components/TradePanel";
import { fetchHistory, fetchSymbols, subscribePrices, CandleData, Symbol } from "@/lib/api";

const TIMEFRAMES = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"];

export default function Home() {
  const [symbols, setSymbols] = useState<Symbol[]>([]);
  const [selectedSymbol, setSelectedSymbol] = useState("BTC/USDT");
  const [timeframe, setTimeframe] = useState("1h");
  const [chartData, setChartData] = useState<CandleData[]>([]);
  const [prices, setPrices] = useState<Record<string, { last: number; bid: number; ask: number; change_pct?: number; stale?: boolean }>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    // The backend, not this component, decides which symbols exist and
    // whether each broker is actually configured — hardcoding the same
    // list here is what let NASDAQ/Gold sit in the UI permanently 502ing.
    fetchSymbols().then(setSymbols).catch(() => {});
  }, []);

  useEffect(() => {
    const unsubscribe = subscribePrices((updated) => {
      setPrices((prev) => ({ ...prev, ...updated }));
    });
    return unsubscribe;
  }, []);

  useEffect(() => {
    loadChart();
  }, [selectedSymbol, timeframe]);

  const loadChart = async () => {
    setLoading(true);
    setError("");
    try {
      const history = await fetchHistory(selectedSymbol, timeframe, 500);
      setChartData(history);
    } catch (err: any) {
      setError(err.message || "Failed to load data");
    }
    setLoading(false);
  };

  const currentPrice = prices[selectedSymbol]?.last;
  const changePct = prices[selectedSymbol]?.change_pct;

  return (
    <div>
      <nav className="nav">
        <span className="nav-logo">Trading Platform</span>
        <Link href="/" className="active">Dashboard</Link>
        <Link href="/backtest">Backtest</Link>
        <Link href="/trade">Trade</Link>
      </nav>

      <div className="container">
        <div style={{ display: "flex", gap: 12, marginBottom: 16, alignItems: "center" }}>
          <div className="tab-bar">
            {symbols.map((s) => (
              <button
                key={s.id}
                className={`tab ${selectedSymbol === s.id ? "active" : ""}`}
                onClick={() => s.available && setSelectedSymbol(s.id)}
                disabled={!s.available}
                title={s.available ? undefined : `${s.broker} not configured on this server`}
              >
                {s.name}
                {prices[s.id] && (
                  <span style={{ marginLeft: 6, fontSize: 11, color: "var(--text-secondary)" }}>
                    ${prices[s.id].last.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                    {prices[s.id].stale ? " (stale)" : ""}
                  </span>
                )}
              </button>
            ))}
          </div>

          <div className="tab-bar" style={{ marginLeft: "auto" }}>
            {TIMEFRAMES.map((tf) => (
              <button
                key={tf}
                className={`tab ${timeframe === tf ? "active" : ""}`}
                onClick={() => setTimeframe(tf)}
              >
                {tf}
              </button>
            ))}
          </div>
        </div>

        {currentPrice && (
          <div style={{ marginBottom: 12, display: "flex", alignItems: "baseline", gap: 12 }}>
            <span style={{ fontSize: 28, fontWeight: 700, color: "var(--text-primary)" }}>
              ${currentPrice.toLocaleString(undefined, { maximumFractionDigits: 2 })}
            </span>
            {changePct !== undefined && (
              <span style={{ fontSize: 14, color: changePct >= 0 ? "var(--green)" : "var(--red)" }}>
                {changePct >= 0 ? "+" : ""}{changePct.toFixed(2)}%
              </span>
            )}
            <span style={{ fontSize: 11, color: "var(--text-secondary)", marginLeft: 4 }}>● LIVE</span>
          </div>
        )}

        {error && (
          <div className="card" style={{ marginBottom: 16, borderColor: "var(--red)" }}>
            <p style={{ color: "var(--red)" }}>{error}</p>
          </div>
        )}

        <div className="card">
          {loading ? (
            <div style={{ height: 450, display: "flex", alignItems: "center", justifyContent: "center" }}>
              <p style={{ color: "var(--text-secondary)" }}>Loading chart data...</p>
            </div>
          ) : chartData.length > 0 ? (
            <Chart data={chartData} />
          ) : (
            <div style={{ height: 450, display: "flex", alignItems: "center", justifyContent: "center" }}>
              <p style={{ color: "var(--text-secondary)" }}>No data available. Make sure the backend is running.</p>
            </div>
          )}
        </div>

        <TradePanel symbol={selectedSymbol} currentPrice={currentPrice} />
      </div>
    </div>
  );
}