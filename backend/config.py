import json
from pathlib import Path
from pydantic import BaseModel


class BinanceConfig(BaseModel):
    api_key: str
    api_secret: str
    testnet: bool = True


class CapitalConfig(BaseModel):
    api_key: str
    identifier: str
    password: str
    demo: bool = True


class SymbolsConfig(BaseModel):
    bitcoin: str = "BTC/USDT"
    nasdaq: str = "US100"
    gold: str = "GOLD"


class AppConfig(BaseModel):
    binance: BinanceConfig
    capital: CapitalConfig
    symbols: SymbolsConfig


def load_config(path: str | None = None) -> AppConfig:
    if path is None:
        path = str(Path(__file__).parent.parent / "config.json")
    with open(path, "r") as f:
        data = json.load(f)
    return AppConfig(**data)
