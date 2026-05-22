import json
import os
from datetime import datetime
from typing import Optional

import pandas as pd

from strategies.base import BaseStrategy, Signal
from .metrics import calculate_metrics


class BacktestEngine:
    """
    Event-driven backtesting engine.
    Iterates over historical candles and simulates trade execution.
    """

    def __init__(
        self,
        strategy: BaseStrategy,
        initial_capital: float = 10000.0,
        commission_pct: float = 0.1,
        slippage_pct: float = 0.01,
    ):
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.commission_pct = commission_pct / 100
        self.slippage_pct = slippage_pct / 100
        self.reset()

    def reset(self):
        self.capital = self.initial_capital
        self.position: Optional[dict] = None
        self.trades: list[dict] = []
        self.equity_curve: list[float] = []
        self.signals_log: list[dict] = []

    def run(self, df: pd.DataFrame) -> dict:
        """Run backtest on historical data."""
        self.reset()

        df_with_signals = self.strategy.generate_signals(df)

        for i, (timestamp, row) in enumerate(df_with_signals.iterrows()):
            signal = row.get("signal", Signal.HOLD)
            price = row["close"]

            if signal == Signal.BUY and self.position is None:
                self._open_position("buy", price, timestamp)
            elif signal == Signal.SELL and self.position is not None:
                self._close_position(price, timestamp)
            elif signal == Signal.SELL and self.position is None:
                self._open_position("sell", price, timestamp)
            elif signal == Signal.BUY and self.position is not None and self.position["side"] == "sell":
                self._close_position(price, timestamp)

            current_equity = self._calculate_equity(price)
            self.equity_curve.append(current_equity)

            if signal != Signal.HOLD:
                self.signals_log.append({
                    "timestamp": str(timestamp),
                    "signal": signal,
                    "price": price,
                    "index": i,
                })

        # Close any remaining position at last price
        if self.position is not None:
            last_price = df_with_signals.iloc[-1]["close"]
            last_ts = df_with_signals.index[-1]
            self._close_position(last_price, last_ts)

        metrics = calculate_metrics(self.trades, self.equity_curve, self.initial_capital)

        return {
            "strategy": self.strategy.name,
            "params": self.strategy.params,
            "metrics": metrics,
            "trades": self.trades,
            "equity_curve": self.equity_curve,
            "signals": self.signals_log,
        }

    def _open_position(self, side: str, price: float, timestamp):
        slippage = price * self.slippage_pct
        entry_price = price + slippage if side == "buy" else price - slippage
        commission = self.capital * self.commission_pct

        position_size = self.capital - commission
        quantity = position_size / entry_price

        self.position = {
            "side": side,
            "entry_price": entry_price,
            "quantity": quantity,
            "entry_time": str(timestamp),
            "commission_entry": commission,
        }
        self.capital -= commission

    def _close_position(self, price: float, timestamp):
        if self.position is None:
            return

        slippage = price * self.slippage_pct
        exit_price = price - slippage if self.position["side"] == "buy" else price + slippage

        if self.position["side"] == "buy":
            pnl = (exit_price - self.position["entry_price"]) * self.position["quantity"]
        else:
            pnl = (self.position["entry_price"] - exit_price) * self.position["quantity"]

        commission = abs(pnl + self.capital) * self.commission_pct
        pnl -= commission

        self.capital = self.position["quantity"] * self.position["entry_price"] + pnl

        trade = {
            "side": self.position["side"],
            "entry_price": round(self.position["entry_price"], 4),
            "exit_price": round(exit_price, 4),
            "quantity": round(self.position["quantity"], 6),
            "entry_time": self.position["entry_time"],
            "exit_time": str(timestamp),
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl / self.initial_capital * 100, 2),
        }
        self.trades.append(trade)
        self.position = None

    def _calculate_equity(self, current_price: float) -> float:
        if self.position is None:
            return self.capital
        if self.position["side"] == "buy":
            unrealized = (current_price - self.position["entry_price"]) * self.position["quantity"]
        else:
            unrealized = (self.position["entry_price"] - current_price) * self.position["quantity"]
        return self.capital + unrealized

    def save_results(self, results: dict, filepath: Optional[str] = None) -> str:
        """Save backtest results to JSON file."""
        if filepath is None:
            results_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "results")
            os.makedirs(results_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"backtest_{self.strategy.name.replace(' ', '_')}_{timestamp}.json"
            filepath = os.path.join(results_dir, filename)

        serializable = {
            **results,
            "equity_curve": [round(e, 2) for e in results["equity_curve"]],
        }

        with open(filepath, "w") as f:
            json.dump(serializable, f, indent=2, default=str)

        return filepath
