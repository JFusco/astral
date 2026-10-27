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
    enable_shadow: bool = False
    enable_exit_monitor: bool = False
    enable_research: bool = False
    enable_codex_research: bool = False
    # Validation-only inputs. from_env deliberately cannot activate this feed.
    enable_activity_feed: bool = False
    activity_mapping_path: Path | None = None
    equity_feed: str = "iex"
    crypto_location: str = "us"
    max_order: Decimal = Decimal("1000")
    max_exposure: Decimal = Decimal("0.50")
    max_group: Decimal = Decimal("0.25")
    max_quote_age: float = 15
    max_snapshot_age: float = 30
    quote_interval: float = 5
    reconcile_interval: float = 10
    shadow_interval: float = 60
    max_unprotected_risk: Decimal = Decimal("0.005")

    def __post_init__(self):
        if self.mode not in {"alpaca", "simulator"}:
            raise ValueError("ASTRAL_MODE must be alpaca or simulator; live trading is unavailable")
        if self.equity_feed not in {"iex", "sip"} or self.crypto_location != "us":
            raise ValueError("Only current IEX/SIP equity and Alpaca US crypto feeds are supported")
        if not Decimal("0") < self.max_exposure <= Decimal("0.5"):
            raise ValueError("Maximum gross exposure must be in (0, 0.5]")
        if not Decimal("0") < self.max_order <= Decimal("1000"):
            raise ValueError("This first paper release caps each order at $1,000")
        if not Decimal("0") < self.max_unprotected_risk <= Decimal("0.005"):
            raise ValueError("Unprotected full-value risk is capped at 0.5% of equity")
        if self.enable_shadow and self.enable_orders:
            raise ValueError("Shadow sessions require paper orders disabled")
        if self.enable_exit_monitor and not self.enable_orders:
            raise ValueError("Exit monitoring requires explicitly enabled paper orders")
        if self.enable_activity_feed and (self.mode != 'alpaca' or self.enable_orders or self.enable_shadow
                                          or self.enable_exit_monitor or self.enable_codex_research):
            raise ValueError('Activity accounting requires orders, shadow, exits and models disabled')

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
                   enable_shadow=os.getenv("ASTRAL_ENABLE_SHADOW", "false").lower() == "true",
                   enable_exit_monitor=os.getenv("ASTRAL_ENABLE_EXIT_MONITOR", "false").lower() == "true",
                   enable_research=os.getenv("ASTRAL_ENABLE_RESEARCH", "false").lower() == "true",
                   enable_codex_research=os.getenv("ASTRAL_ENABLE_CODEX_RESEARCH", "false").lower() == "true",
                   equity_feed=os.getenv("ASTRAL_EQUITY_FEED", "iex"))
