"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import TradePanel from "@/components/TradePanel";
import { fetchPositions, fetchBalance, fetchPrice, fetchSymbols, Symbol } from "@/lib/api";

export default function TradePage() {
  const [symbols, setSymbols] = useState<Symbol[]>([]);
  const [positions, setPositions] = useState<any[]>([]);
  const [balances, setBalances] = useState<any>({});
  const [prices, setPrices] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchSymbols().then(setSymbols).catch(() => {});
  }, []);

  useEffect(() => {
    if (symbols.length === 0) return;
    loadData();
    const interval = setInterval(loadData, 10000);
    return () => clearInterval(interval);
  }, [symbols]);

  const loadData = async () => {
    try {
      const [posData, balData] = await Promise.all([
        fetchPositions(),
        fetchBalance(),
      ]);
      setPositions(posData.positions || []);
      setBalances(balData);

      const pricePromises = symbols.filter((s) => s.available).map(async (s) => {
        try {
          const p = await fetchPrice(s.id);
          return { id: s.id, price: p.last };
        } catch {
          return { id: s.id, price: null };
        }
      });
      const priceResults = await Promise.all(pricePromises);
      const priceMap: Record<string, number> = {};
      priceResults.forEach((p) => {
        if (p.price) priceMap[p.id] = p.price;
      });
      setPrices(priceMap);
    } catch {
      // Backend might not be running
    }
  };

  return (
    <div>
      <nav className="nav">
        <span className="nav-logo">Trading Platform</span>
        <Link href="/">Dashboard</Link>
        <Link href="/backtest">Backtest</Link>
        <Link href="/trade" className="active">Trade</Link>
      </nav>

      <div className="container">
        <div className="grid-2" style={{ marginBottom: 16 }}>
          <div className="card">
            <h3 style={{ marginBottom: 12, fontSize: 14 }}>Binance Balance</h3>
            {balances.binance?.error ? (
              <p style={{ color: "var(--text-secondary)", fontSize: 13 }}>Not connected</p>
            ) : (
              <div>
                <p style={{ fontSize: 20, fontWeight: 700 }}>
                  ${(balances.binance?.total || 0).toLocaleString()} USDT
                </p>
                <p style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                  Available: ${(balances.binance?.free || 0).toLocaleString()}
                </p>
              </div>
            )}
          </div>
          <div className="card">
            <h3 style={{ marginBottom: 12, fontSize: 14 }}>Capital.com Balance</h3>
            {balances.capital?.error ? (
              <p style={{ color: "var(--text-secondary)", fontSize: 13 }}>Not connected</p>
            ) : (
              <div>
                <p style={{ fontSize: 20, fontWeight: 700 }}>
                  ${(balances.capital?.total || 0).toLocaleString()} {balances.capital?.currency}
                </p>
                <p style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                  Available: ${(balances.capital?.free || 0).toLocaleString()}
                </p>
              </div>
            )}
          </div>
        </div>

        <div className="card" style={{ marginBottom: 16 }}>
          <h3 style={{ marginBottom: 12, fontSize: 14 }}>Live Prices</h3>
          <div className="grid-3">
            {symbols.map((s) => (
              <div key={s.id} style={{ textAlign: "center", padding: 12, opacity: s.available ? 1 : 0.5 }}>
                <p style={{ fontSize: 12, color: "var(--text-secondary)" }}>{s.name}</p>
                <p style={{ fontSize: 20, fontWeight: 700 }}>
                  {!s.available ? "N/A" : prices[s.id] ? `$${prices[s.id].toLocaleString()}` : "---"}
                </p>
              </div>
            ))}
          </div>
        </div>

        <div className="card" style={{ marginBottom: 16 }}>
          <h3 style={{ marginBottom: 12, fontSize: 14 }}>Open Positions</h3>
          {positions.length === 0 ? (
            <p style={{ color: "var(--text-secondary)", fontSize: 13 }}>No open positions</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Side</th>
                  <th>Size</th>
                  <th>Entry Price</th>
                  <th>Unrealized P&L</th>
                </tr>
              </thead>
              <tbody>
                {positions.map((p, i) => (
                  <tr key={i}>
                    <td>{p.symbol}</td>
                    <td style={{ color: p.side === "long" || p.side === "buy" ? "var(--green)" : "var(--red)" }}>
                      {(p.side || "").toUpperCase()}
                    </td>
                    <td>{p.size}</td>
                    <td>${p.entry_price?.toLocaleString()}</td>
                    <td className={p.unrealized_pnl >= 0 ? "positive" : "negative"}>
                      ${p.unrealized_pnl?.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <h3 style={{ marginBottom: 12, fontSize: 16 }}>Place Orders</h3>
        <div className="grid-3">
          {symbols.filter((s) => s.available).map((s) => (
            <TradePanel key={s.id} symbol={s.id} currentPrice={prices[s.id]} />
          ))}
        </div>
      </div>
    </div>
  );
}
