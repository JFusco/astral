from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[1]
PAPER_URL = "https://paper-api.alpaca.markets"
DATA_URL = "https://data.alpaca.markets"
SYMBOLS = {"BTC": ("BTC/USD", "crypto"), "ETH": ("ETH/USD", "crypto"),
           "SOL": ("SOL/USD", "crypto"), "SPY": ("SPY", "etf"),
           "QQQ": ("QQQ", "etf"), "GLD": ("GLD", "etf"),
           "TLT": ("TLT", "etf"), "IWM": ("IWM", "etf")}


@dataclass(frozen=True)
class Settings:
    mode: str = "alpaca"
    db_path: Path = ROOT / "runtime/astral-alpaca.sqlite"
    api_key: str = field(default="", repr=False)
    secret_key: str = field(default="", repr=False)
    enable_orders: bool = False
    enable_news: bool = False
    equity_feed: str = "iex"
    crypto_location: str = "us"
    max_order: Decimal = Decimal("1000")
    max_exposure: Decimal = Decimal("0.50")
    max_group: Decimal = Decimal("0.25")
    max_quote_age: float = 15
    max_snapshot_age: float = 30
    quote_interval: float = 5
    reconcile_interval: float = 10

    def __post_init__(self):
        if self.mode not in {"alpaca", "simulator"}:
            raise ValueError("ASTRAL_MODE must be alpaca or simulator; live trading is unavailable")
        if self.equity_feed not in {"iex", "sip"} or self.crypto_location != "us":
            raise ValueError("Only current IEX/SIP equity and Alpaca US crypto feeds are supported")
        if not Decimal("0") < self.max_exposure <= Decimal("0.5"):
            raise ValueError("Maximum gross exposure must be in (0, 0.5]")
        if not Decimal("0") < self.max_order <= Decimal("1000"):
            raise ValueError("This first paper release caps each order at $1,000")

    @property
    def configured(self):
        return self.mode == "simulator" or bool(self.api_key and self.secret_key)

    @classmethod
    def from_env(cls):
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env", override=False)
        for name in ("APCA_API_BASE_URL", "ALPACA_BASE_URL", "ASTRAL_ALPACA_BASE_URL"):
            if os.getenv(name) and os.environ[name].rstrip("/") != PAPER_URL:
                raise ValueError(f"{name}: only the fixed Alpaca paper host is permitted")
        if os.getenv("ALPACA_PAPER_TRADE", "true").lower() != "true":
            raise ValueError("Live trading is unavailable")
        mode = os.getenv("ASTRAL_MODE", "alpaca")
        return cls(mode=mode,
                   db_path=Path(os.getenv("ASTRAL_DB_PATH", str(ROOT / f"runtime/astral-{mode}.sqlite"))),
                   api_key=os.getenv("ALPACA_PAPER_API_KEY", ""),
                   secret_key=os.getenv("ALPACA_PAPER_SECRET_KEY", ""),
                   enable_orders=os.getenv("ASTRAL_ENABLE_PAPER_ORDERS", "false").lower() == "true",
                   enable_news=os.getenv("ASTRAL_ENABLE_NEWS", "false").lower() == "true",
                   equity_feed=os.getenv("ASTRAL_EQUITY_FEED", "iex"))
