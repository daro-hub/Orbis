import json
import os
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd

from strategies.base import BaseStrategy, Signal
from .metrics import calculate_metrics

SECONDS_PER_YEAR = 365 * 24 * 3600


class BacktestEngine:
    """
    Event-driven backtesting engine.
    Iterates over historical candles and simulates trade execution.

    A signal computed from bar i's close is only known once bar i has fully
    formed, so it is executed at bar i+1's open — never at bar i's own close.
    Executing on the same bar that produced the signal is look-ahead bias:
    it assumes you could trade at a price before it's possible to know the
    signal that price would produce.
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
        n = len(df_with_signals)
        timestamps = df_with_signals.index
        opens = df_with_signals["open"].to_numpy()
        closes = df_with_signals["close"].to_numpy()
        signals = df_with_signals["signal"].to_numpy()

        pending_signal = None

        for i in range(n):
            if pending_signal is not None:
                self._execute_signal(pending_signal, opens[i], timestamps[i])
                pending_signal = None

            self.equity_curve.append(self._calculate_equity(closes[i]))

            if signals[i] != Signal.HOLD:
                self.signals_log.append({
                    "timestamp": str(timestamps[i]),
                    "signal": signals[i],
                    "price": float(closes[i]),
                    "index": i,
                })
                # Queued for execution at the *next* bar's open, not this
                # bar's close — see class docstring.
                pending_signal = signals[i]

        # Close any remaining position at the last available price — there
        # is no further bar to execute a fresh signal on.
        if self.position is not None and n > 0:
            self._close_position(float(closes[-1]), timestamps[-1])
            self.equity_curve[-1] = self._calculate_equity(float(closes[-1]))

        periods_per_year = self._periods_per_year(timestamps)
        metrics = calculate_metrics(self.trades, self.equity_curve, self.initial_capital, periods_per_year)

        return {
            "strategy": self.strategy.name,
            "params": self.strategy.params,
            "metrics": metrics,
            "trades": self.trades,
            "equity_curve": self.equity_curve,
            "signals": self.signals_log,
        }

    @staticmethod
    def _periods_per_year(timestamps: pd.Index) -> float:
        """Infer the Sharpe annualization factor from the actual bar spacing
        instead of assuming daily bars (a fixed sqrt(252) overstates Sharpe
        by ~5-6x on hourly data)."""
        if len(timestamps) < 2:
            return 252.0
        deltas = np.diff(timestamps.values).astype("timedelta64[s]").astype(float)
        median_seconds = float(np.median(deltas))
        if median_seconds <= 0:
            return 252.0
        return SECONDS_PER_YEAR / median_seconds

    def _execute_signal(self, signal: str, price: float, timestamp):
        if signal == Signal.BUY and self.position is None:
            self._open_position("buy", price, timestamp)
        elif signal == Signal.SELL and self.position is not None:
            self._close_position(price, timestamp)
        elif signal == Signal.SELL and self.position is None:
            self._open_position("sell", price, timestamp)
        elif signal == Signal.BUY and self.position is not None and self.position["side"] == "sell":
            self._close_position(price, timestamp)

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

        # Commission on the actual notional leaving the position, not on
        # `pnl + self.capital` (a leftover-cash figure that has nothing to
        # do with the position's exit value and, combined with overwriting
        # self.capital below, silently discarded the entry commission).
        exit_notional = self.position["quantity"] * exit_price
        commission_exit = exit_notional * self.commission_pct
        pnl -= commission_exit

        # self.capital already reflects capital-after-entry-commission and
        # sits untouched while the position is open (see _calculate_equity);
        # closing just realizes the net pnl into it.
        self.capital += pnl

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
