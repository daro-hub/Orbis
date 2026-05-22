"use client";

interface BacktestResultsProps {
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
  equityCurve: number[];
}

export default function BacktestResults({ metrics, trades, equityCurve }: BacktestResultsProps) {
  return (
    <div>
      <div className="grid-3" style={{ marginBottom: 20 }}>
        <div className="card metric">
          <div className={`metric-value ${metrics.total_pnl >= 0 ? "positive" : "negative"}`}>
            ${metrics.total_pnl}
          </div>
          <div className="metric-label">Total P&L</div>
        </div>
        <div className="card metric">
          <div className="metric-value">{metrics.win_rate}%</div>
          <div className="metric-label">Win Rate</div>
        </div>
        <div className="card metric">
          <div className="metric-value">{metrics.total_trades}</div>
          <div className="metric-label">Total Trades</div>
        </div>
        <div className="card metric">
          <div className="metric-value">{metrics.sharpe_ratio}</div>
          <div className="metric-label">Sharpe Ratio</div>
        </div>
        <div className="card metric">
          <div className={`metric-value negative`}>-{metrics.max_drawdown_pct}%</div>
          <div className="metric-label">Max Drawdown</div>
        </div>
        <div className="card metric">
          <div className="metric-value">{metrics.profit_factor}</div>
          <div className="metric-label">Profit Factor</div>
        </div>
      </div>

      <div className="card">
        <h3 style={{ marginBottom: 12, fontSize: 14 }}>Trade History</h3>
        <div style={{ overflowX: "auto" }}>
          <table>
            <thead>
              <tr>
                <th>Side</th>
                <th>Entry Price</th>
                <th>Exit Price</th>
                <th>Entry Time</th>
                <th>P&L</th>
                <th>P&L %</th>
              </tr>
            </thead>
            <tbody>
              {trades.map((trade, i) => (
                <tr key={i}>
                  <td>
                    <span style={{ color: trade.side === "buy" ? "var(--green)" : "var(--red)" }}>
                      {trade.side.toUpperCase()}
                    </span>
                  </td>
                  <td>${trade.entry_price.toLocaleString()}</td>
                  <td>${trade.exit_price.toLocaleString()}</td>
                  <td style={{ fontSize: 11 }}>{trade.entry_time}</td>
                  <td className={trade.pnl >= 0 ? "positive" : "negative"}>
                    ${trade.pnl}
                  </td>
                  <td className={trade.pnl_pct >= 0 ? "positive" : "negative"}>
                    {trade.pnl_pct}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
