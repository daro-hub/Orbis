from typing import Callable, Type

from .base import BaseStrategy

_REGISTRY: dict[str, Type[BaseStrategy]] = {}


def register_strategy(strategy_id: str) -> Callable[[Type[BaseStrategy]], Type[BaseStrategy]]:
    """Class decorator: makes a strategy discoverable by id without any
    caller having to hardcode an if/elif chain over concrete classes."""

    def decorator(cls: Type[BaseStrategy]) -> Type[BaseStrategy]:
        _REGISTRY[strategy_id] = cls
        return cls

    return decorator


def get_strategy_class(strategy_id: str) -> Type[BaseStrategy] | None:
    return _REGISTRY.get(strategy_id)


def create_strategy(strategy_id: str, params: dict) -> BaseStrategy:
    cls = get_strategy_class(strategy_id)
    if cls is None:
        raise KeyError(strategy_id)
    return cls(**params)


def describe_strategies() -> list[dict]:
    """List every registered strategy with its default params, for the
    /api/backtest/strategies endpoint and the bot's strategy picker."""
    described = []
    for strategy_id, cls in _REGISTRY.items():
        default = cls()
        described.append({"id": strategy_id, "name": default.name, "params": default.params})
    return described
