"""
Automated Trading Bot - Runs strategies on live data.
Checks for signals at configurable intervals and executes trades.
"""

import asyncio
import json
import os
import time
from datetime import datetime
from typing import Optional

from connectors.base import BaseConnector
from strategies.base import BaseStrategy, Signal
from strategies.registry import create_strategy
from trading.risk import RiskManager, RiskConfig


class TradingBot:
    """
    Automated trading bot that runs a strategy on a schedule.
    Fetches latest data, generates signals, and executes trades with risk management.
    """

    def __init__(
        self,
        connector: BaseConnector,
        strategy: BaseStrategy,
        symbol: str,
        timeframe: str = "1h",
        lookback: int = 100,
        risk_config: Optional[RiskConfig] = None,
        check_interval_seconds: int = 60,
    ):
        self.connector = connector
        self.strategy = strategy
        self.symbol = symbol
        self.timeframe = timeframe
        self.lookback = lookback
        self.risk_manager = RiskManager(risk_config or RiskConfig())
        self.check_interval = check_interval_seconds

        self._running = False
        self._last_signal: Optional[str] = None
        self.trade_log: list[dict] = []
        # Symbols like "BTC/USDT" contain a "/" -- left unescaped, it was
        # read as a path separator, so the log silently landed at
        # results/bot_BTC/USDT_<strategy>.json (a stray "bot_BTC" directory)
        # instead of a single flat file.
        safe_symbol = symbol.replace("/", "-")
        self.log_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "results",
            f"bot_{safe_symbol}_{strategy.name.replace(' ', '_')}.json",
        )

    async def start(self):
        """Start the bot loop."""
        self._running = True
        self._log(f"Bot started: {self.strategy.name} on {self.symbol} ({self.timeframe})")

        while self._running:
            try:
                await self._check_signal()
            except Exception as e:
                self._log(f"Error during check: {e}")

            await asyncio.sleep(self.check_interval)

    def stop(self):
        """Stop the bot."""
        self._running = False
        self._log("Bot stopped")
        self._save_log()

    async def _check_signal(self):
        df = await self.connector.get_historical_data(
            self.symbol, timeframe=self.timeframe, limit=self.lookback
        )

        if df.empty:
            return

        df_signals = self.strategy.generate_signals(df)
        latest_signal = df_signals.iloc[-1].get("signal", Signal.HOLD)

        if latest_signal == self._last_signal:
            return

        self._last_signal = latest_signal
        current_price = df_signals.iloc[-1]["close"]

        if latest_signal == Signal.BUY:
            await self._handle_buy(current_price)
        elif latest_signal == Signal.SELL:
            await self._handle_sell(current_price)

    async def _handle_buy(self, price: float):
        balance = await self.connector.get_balance()
        capital = balance.get("free", 0)

        if capital <= 0:
            self._log("No available capital for buy")
            return

        quantity = self.risk_manager.calculate_position_size(capital, price)
        can_trade, reason = self.risk_manager.can_open_position(capital, quantity * price)

        if not can_trade:
            self._log(f"Risk check failed: {reason}")
            return

        try:
            result = await self.connector.place_order(
                symbol=self.symbol, side="buy", quantity=quantity, order_type="market"
            )
            self.risk_manager.open_positions_count += 1
            self._log(f"BUY executed: {quantity:.6f} @ ${price:.2f}", result)
            self.trade_log.append({
                "time": datetime.now().isoformat(),
                "action": "buy",
                "price": price,
                "quantity": quantity,
                "result": result,
            })
        except Exception as e:
            self._log(f"Buy order failed: {e}")

    async def _handle_sell(self, price: float):
        try:
            result = await self.connector.close_position(self.symbol)
            if result.get("status") != "no_position":
                self.risk_manager.open_positions_count -= 1
                self._log(f"SELL/Close executed @ ${price:.2f}", result)
                self.trade_log.append({
                    "time": datetime.now().isoformat(),
                    "action": "sell",
                    "price": price,
                    "result": result,
                })
        except Exception as e:
            self._log(f"Sell/close failed: {e}")

    def _log(self, message: str, data: Optional[dict] = None):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        if data:
            log_entry += f" | {json.dumps(data)}"
        print(log_entry)

    def _save_log(self):
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        with open(self.log_file, "w") as f:
            json.dump({
                "symbol": self.symbol,
                "strategy": self.strategy.name,
                "params": self.strategy.params,
                "trades": self.trade_log,
                "stopped_at": datetime.now().isoformat(),
            }, f, indent=2)


# --- Bot Management for API ---

active_bots: dict[str, TradingBot] = {}


async def start_bot(
    symbol: str,
    strategy_id: str,
    strategy_params: dict,
    connector: BaseConnector,
    timeframe: str = "1h",
    check_interval: int = 60,
) -> str:
    """Start a new bot instance.

    `connector` is built and dispatched by the caller (main.py already
    knows which broker serves which symbol) — the bot only orchestrates
    strategy + risk + execution, it doesn't need to know about brokers.
    """
    bot_id = f"{symbol}_{strategy_id}"

    if bot_id in active_bots:
        return f"Bot {bot_id} already running"

    try:
        strategy = create_strategy(strategy_id, strategy_params)
    except KeyError:
        return f"Unknown strategy: {strategy_id}"

    bot = TradingBot(
        connector=connector,
        strategy=strategy,
        symbol=symbol,
        timeframe=timeframe,
        check_interval_seconds=check_interval,
    )

    active_bots[bot_id] = bot
    asyncio.create_task(bot.start())
    return f"Bot {bot_id} started"


def stop_bot(bot_id: str) -> str:
    """Stop a running bot."""
    bot = active_bots.pop(bot_id, None)
    if bot:
        bot.stop()
        return f"Bot {bot_id} stopped"
    return f"Bot {bot_id} not found"


def list_bots() -> list[dict]:
    """List all active bots."""
    return [
        {
            "id": bot_id,
            "symbol": bot.symbol,
            "strategy": bot.strategy.name,
            "params": bot.strategy.params,
            "running": bot._running,
            "trades": len(bot.trade_log),
        }
        for bot_id, bot in active_bots.items()
    ]
