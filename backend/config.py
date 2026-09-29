from pathlib import Path
from typing import Optional

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

# Absolute, not "./.env": pydantic-settings resolves a relative env_file
# against the process's current working directory, which is wherever the
# server happens to be launched from — not necessarily this package's
# folder.
_ENV_FILE = Path(__file__).resolve().parent / ".env"


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
    model_config = SettingsConfigDict(env_nested_delimiter="__", env_file=_ENV_FILE, extra="ignore")

    binance: BinanceConfig
    # Capital.com needs a separate demo account (capital.com), so it's kept
    # optional: the app boots and serves BTC/USDT fine with only Binance
    # configured, and NASDAQ/Gold report themselves as unavailable instead
    # of crashing the whole backend at startup.
    capital: Optional[CapitalConfig] = None
    symbols: SymbolsConfig = SymbolsConfig()

    # Comma-separated list of origins allowed to call the API. Defaults to
    # the local Next.js dev server only — broaden via env for a deployed
    # frontend, never with a bare "*" alongside real order placement.
    allowed_origins: str = "http://localhost:3000"

    # Optional shared secret required (via X-API-Key) on endpoints that
    # place orders or start/stop bots. Left unset, those endpoints stay
    # open — fine for local dev, not for a public deployment.
    api_key: Optional[str] = None

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


def load_config() -> AppConfig:
    return AppConfig()
