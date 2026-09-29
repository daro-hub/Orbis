# Importing the package registers the built-in strategies with
# strategies.registry (each is decorated with @register_strategy there) —
# anything doing `import strategies` or `from strategies import ...` is
# enough to make them discoverable, without callers needing to know the
# concrete module a given strategy id lives in.
from . import example_sma  # noqa: F401
