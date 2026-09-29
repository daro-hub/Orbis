import strategies  # noqa: F401 - registers built-in strategies as a side effect
from strategies.example_sma import RSIStrategy, SMAcrossoverStrategy
from strategies.registry import create_strategy, describe_strategies, get_strategy_class


def test_builtin_strategies_are_registered_on_import():
    assert get_strategy_class("sma_crossover") is SMAcrossoverStrategy
    assert get_strategy_class("rsi") is RSIStrategy
    assert get_strategy_class("nonexistent") is None


def test_create_strategy_passes_params_through():
    strat = create_strategy("sma_crossover", {"fast_period": 5, "slow_period": 20})
    assert isinstance(strat, SMAcrossoverStrategy)
    assert strat.params == {"fast_period": 5, "slow_period": 20}


def test_create_strategy_unknown_id_raises_keyerror():
    try:
        create_strategy("does_not_exist", {})
        assert False, "expected KeyError"
    except KeyError:
        pass


def test_describe_strategies_lists_defaults():
    described = {s["id"]: s for s in describe_strategies()}
    assert described["sma_crossover"]["params"] == {"fast_period": 10, "slow_period": 30}
    assert described["rsi"]["params"] == {"period": 14, "oversold": 30, "overbought": 70}
