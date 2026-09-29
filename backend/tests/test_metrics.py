from backtester.metrics import calculate_metrics


def test_no_trades_returns_zeroed_metrics():
    m = calculate_metrics([], [10000.0], 10000.0)
    assert m["total_trades"] == 0
    assert m["profit_factor"] == 0


def test_profit_factor_normal_case():
    trades = [{"pnl": 10}, {"pnl": -5}, {"pnl": 20}, {"pnl": -10}]
    m = calculate_metrics(trades, [10000, 10015], 10000.0)
    # gross_profit=30, gross_loss=15
    assert m["profit_factor"] == 2.0


def test_profit_factor_no_losses_is_capped_not_a_dollar_amount():
    """Regression: the old code fell back to `gross_loss = 1` when there
    were no losing trades, so profit_factor became `gross_profit / 1`— a
    dollar amount masquerading as a ratio. All-wins should report a large,
    clearly-a-ratio number instead."""
    trades = [{"pnl": 500}, {"pnl": 300}]
    m = calculate_metrics(trades, [10000, 10800], 10000.0)
    assert m["profit_factor"] == 9999.0


def test_profit_factor_all_breakeven_is_zero_not_infinite():
    trades = [{"pnl": 0}, {"pnl": 0}]
    m = calculate_metrics(trades, [10000, 10000], 10000.0)
    assert m["profit_factor"] == 0.0


def test_drawdown_pct_uses_local_peak_not_global_peak():
    """Regression: the old code divided the worst dollar drawdown by the
    single global peak of the whole equity curve. When the worst drawdown
    happens relative to an earlier, smaller peak — before an unrelated new
    all-time high later on — that diluted the reported % drawdown."""
    equity_curve = [100, 130, 90, 300, 280]
    trades = [{"pnl": 180}]  # content doesn't matter for this assertion

    m = calculate_metrics(trades, equity_curve, 100.0)

    # Worst dollar drawdown is 130 - 90 = 40, against the *local* peak of
    # 130 (not the eventual global peak of 300): 40/130 = ~30.77%.
    assert m["max_drawdown"] == 40.0
    assert abs(m["max_drawdown_pct"] - 30.77) < 0.01
    # The old, buggy formula would have produced 40/300*100 = 13.33%.
    assert abs(m["max_drawdown_pct"] - 13.33) > 1


def test_sharpe_scales_with_periods_per_year():
    """Regression: a hardcoded sqrt(252) annualizes as if every bar were a
    full trading day, overstating Sharpe on any finer timeframe."""
    equity_curve = [10000, 10100, 10050, 10200]
    trades = [{"pnl": 200}]

    daily = calculate_metrics(trades, equity_curve, 10000.0, periods_per_year=252)
    hourly = calculate_metrics(trades, equity_curve, 10000.0, periods_per_year=252 * 24)

    # Same returns, higher annualization factor => higher reported Sharpe.
    assert hourly["sharpe_ratio"] > daily["sharpe_ratio"]
