from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


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


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter="__", env_file=".env", extra="ignore")

    binance: BinanceConfig
    capital: CapitalConfig
    symbols: SymbolsConfig = SymbolsConfig()


def load_config() -> AppConfig:
    return AppConfig()
