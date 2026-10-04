"""Regression test for a routing bug found while clicking through the
frontend's Bot page: /api/bot/stop/{bot_id} used a plain string path
parameter, but bot_id is built as f"{symbol}_{strategy_id}" and symbol
values (e.g. "BTC/USDT") contain a "/" -- so the real bot_id for that
symbol could never match the route at all, and clicking "Stop" in the UI
always 404'd. Every other route in main.py that embeds a symbol already
used the `:path` converter for exactly this reason; /api/bot/stop/{bot_id}
was the one spot that didn't.

Inserts a fake bot directly into trading.bot.active_bots rather than
going through POST /api/bot/start, so this test exercises only the
routing fix -- not a real network call to Binance's testnet, which
starting a real bot would trigger in the background.
"""

import os

# BinanceConfig has no defaults, so importing main.py (which calls
# load_config() at module scope) needs these set even though this test
# never touches Binance for real -- same as backend/.env.example's dummy
# local-preview values.
os.environ.setdefault("BINANCE__API_KEY", "dummy-test-key")
os.environ.setdefault("BINANCE__API_SECRET", "dummy-test-secret")
os.environ.setdefault("BINANCE__TESTNET", "true")

from unittest.mock import MagicMock  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
import trading.bot as bot_module  # noqa: E402
from strategies.registry import create_strategy  # noqa: E402
from trading.bot import TradingBot  # noqa: E402

client = TestClient(main.app)


def test_stop_route_accepts_a_bot_id_containing_a_slash():
    bot_id = "BTC/USDT_sma_crossover"
    fake_bot = MagicMock()
    bot_module.active_bots[bot_id] = fake_bot
    try:
        resp = client.post(f"/api/bot/stop/{bot_id}")
        assert resp.status_code == 200
        assert "stopped" in resp.json()["message"]
        fake_bot.stop.assert_called_once()
        assert bot_id not in bot_module.active_bots
    finally:
        bot_module.active_bots.pop(bot_id, None)


def test_stopping_an_unknown_bot_id_reports_not_found_in_the_message_not_a_404():
    # bot_stop's own contract: a bot_id with no match returns a 200 with
    # a "not found" message (see trading/bot.py::stop_bot), not an HTTP
    # 404 -- that status is reserved for the route itself not matching at
    # all, which was the actual bug here.
    resp = client.post("/api/bot/stop/does-not-exist")
    assert resp.status_code == 200
    assert "not found" in resp.json()["message"]


def test_log_file_path_is_sanitized_for_symbols_with_a_slash():
    # Companion bug to the routing one above, same root cause: "BTC/USDT"
    # embedded unescaped in a path segment used to silently create a
    # stray "bot_BTC" directory (results/bot_BTC/USDT_<strategy>.json)
    # instead of a single flat results/bot_BTC-USDT_<strategy>.json file.
    bot = TradingBot(
        connector=MagicMock(), strategy=create_strategy("sma_crossover", {}), symbol="BTC/USDT"
    )
    assert "/" not in os.path.basename(bot.log_file)
    assert os.path.dirname(bot.log_file).endswith("results")
