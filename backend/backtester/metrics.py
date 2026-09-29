import numpy as np


def calculate_metrics(
    trades: list[dict],
    equity_curve: list[float],
    initial_capital: float,
    periods_per_year: float = 252.0,
) -> dict:
    """Calculate performance metrics from trade history and equity curve.

    periods_per_year annualizes the Sharpe ratio for the bar spacing actually
    used (e.g. ~8760 for 1h candles, ~365 for 1d) — a fixed 252 (trading days)
    silently overstates Sharpe on any intraday timeframe.
    """
    if not trades:
        return {
            "total_trades": 0,
            "win_rate": 0,
            "total_pnl": 0,
            "total_pnl_pct": 0,
            "max_drawdown": 0,
            "max_drawdown_pct": 0,
            "sharpe_ratio": 0,
            "profit_factor": 0,
            "avg_trade_pnl": 0,
            "best_trade": 0,
            "worst_trade": 0,
        }

    pnls = [t["pnl"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]

    total_pnl = sum(pnls)
    win_rate = len(wins) / len(trades) * 100 if trades else 0

    gross_profit = sum(wins) if wins else 0.0
    gross_loss = abs(sum(losses)) if losses else 0.0
    if gross_loss == 0:
        # No losing trades: a true ratio would be infinite, which isn't
        # valid JSON. Cap it instead of silently returning a dollar amount
        # (the previous bug) or `inf` (which breaks res.json() client-side).
        profit_factor = 9999.0 if gross_profit > 0 else 0.0
    else:
        profit_factor = gross_profit / gross_loss

    equity = np.array(equity_curve)
    peak = np.maximum.accumulate(equity)
    drawdown = peak - equity
    max_drawdown = float(np.max(drawdown)) if len(drawdown) > 0 else 0.0

    # % drawdown against the running peak at each point, not the single
    # global peak — otherwise a big drop after an early, smaller peak gets
    # diluted by a later, unrelated all-time high.
    safe_peak = np.where(peak > 0, peak, 1)
    drawdown_pct_series = drawdown / safe_peak
    max_drawdown_pct = float(np.max(drawdown_pct_series) * 100) if len(drawdown_pct_series) > 0 else 0.0

    returns = np.diff(equity) / equity[:-1] if len(equity) > 1 else np.array([0])
    sharpe_ratio = 0
    if len(returns) > 1 and np.std(returns) > 0:
        sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(periods_per_year)

    return {
        "total_trades": len(trades),
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "win_rate": round(win_rate, 2),
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": round(total_pnl / initial_capital * 100, 2),
        "max_drawdown": round(max_drawdown, 2),
        "max_drawdown_pct": round(max_drawdown_pct, 2),
        "sharpe_ratio": round(sharpe_ratio, 2),
        "profit_factor": round(profit_factor, 2),
        "avg_trade_pnl": round(np.mean(pnls), 2),
        "best_trade": round(max(pnls), 2),
        "worst_trade": round(min(pnls), 2),
        "initial_capital": initial_capital,
        "final_capital": round(equity[-1], 2) if len(equity) > 0 else initial_capital,
    }
