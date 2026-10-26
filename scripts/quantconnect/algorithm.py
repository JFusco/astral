"""Cloud entry point; package with compare prepare before uploading main.py."""
from AlgorithmImports import QCAlgorithm, Resolution, Market, TimeZones
from datetime import timedelta
from scripts.quantconnect.model import (
    CONTRACT, START, END, FROZEN_MANIFEST, FIELDS, validate_bar, evaluate,
)
import hashlib

BUNDLE_ID = "unprepared"


class AstralBtcSignalParity(QCAlgorithm):
    def initialize(self):
        if self.live_mode:
            raise RuntimeError("Signal comparison refuses every live deployment, including paper")
        if BUNDLE_ID == "unprepared":
            raise RuntimeError("Package the pinned comparison before running")
        self.set_time_zone(TimeZones.UTC)
        self.set_start_date(START.year, START.month, START.day)
        self.set_end_date(END.year, END.month, END.day)
        self.set_cash(100000)
        self._symbol = self.add_crypto(
            "BTCUSD", Resolution.DAILY, market=Market.COINBASE, fill_forward=False,
        ).symbol
        self._window = []
        self._previous = None
        self._bars = self._signals = 0
        self._digest = hashlib.sha256()
        self.log("ASTRAL_QC|M|" + "|".join((
            CONTRACT, "coinbase", "BTCUSD", str(START), str(END), FROZEN_MANIFEST, BUNDLE_ID,
        )))

    def _emit(self, content):
        self._digest.update((content + "\n").encode())
        self.log("ASTRAL_QC|" + content)

    def on_data(self, data):
        if self._symbol not in data.bars:
            return
        bar = data.bars[self._symbol]
        day = bar.time.date()
        if day >= END:
            return
        if (bar.is_fill_forward or bar.time.hour or bar.time.minute or bar.time.second
                or bar.end_time != bar.time + timedelta(days=1)
                or self.utc_time < bar.end_time):
            raise ValueError("Expected completed, non-filled daily UTC trade bars")
        if self._previous is None and day != START:
            raise ValueError("Missing first historical day")
        values = tuple(str(value) for value in (bar.open, bar.high, bar.low, bar.close, bar.volume))
        opening, high, low, close, volume = validate_bar(day, values, self._previous)
        self._previous = day
        self._bars += 1
        self._emit("B|" + "|".join((str(day), *values)))
        self._window = (self._window + [(high, low, close)])[-90:]
        if len(self._window) >= 51:
            result = evaluate(self._window)
            self._signals += 1
            self._emit("S|" + "|".join((str(day), *(str(result[key]) for key in FIELDS))))

    def on_end_of_algorithm(self):
        orders = sum(1 for _ in self.transactions.get_orders())
        if orders or self.portfolio.invested:
            raise RuntimeError("Zero-order comparison boundary violated")
        if self._bars != (END - START).days or self._signals != self._bars - 50:
            raise ValueError("Historical coverage is incomplete")
        self.log(f"ASTRAL_QC|E|{self._bars}|{self._signals}|{orders}|{self._digest.hexdigest()}")
