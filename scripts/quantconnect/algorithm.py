"""Compare both implementations in cloud memory; export aggregate diagnostics only."""
from AlgorithmImports import QCAlgorithm, Resolution, Market, TimeZones
from datetime import timedelta, timezone
from decimal import Decimal
from scripts.quantconnect.model import (
    CONTRACT, START, END, FROZEN_MANIFEST, FIELDS, validate_bar, evaluate,
)
from backend.risk import price_signal
import json

BUNDLE_ID = "unprepared"
TOLERANCE = Decimal("1e-20")


def as_utc(value):
    # Coinbase bar times and the algorithm timezone are UTC. LEAN may expose
    # those bar times without tzinfo while its algorithm clock is aware.
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


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
        self._bars = self._signals = self._mismatches = 0
        self._counts = {name: 0 for name in ("hold", "entry_candidate", "exit_review")}
        self._errors = {key: Decimal(0) for key in FIELDS if key != "signal"}
        self.log("ASTRAL_QC|M|" + "|".join((
            CONTRACT, "coinbase", "BTCUSD", str(START), str(END), FROZEN_MANIFEST, BUNDLE_ID,
        )))

    def on_data(self, data):
        if self._symbol not in data.bars:
            return
        bar = data.bars[self._symbol]
        start, end, now = as_utc(bar.time), as_utc(bar.end_time), as_utc(self.utc_time)
        day = start.date()
        if day < START or day >= END:
            return
        if (bar.is_fill_forward or start.hour or start.minute or start.second or start.microsecond
                or end != start + timedelta(days=1) or now < end):
            raise ValueError("Expected completed, non-filled daily UTC trade bars")
        if self._previous is None and day != START:
            raise ValueError("Missing first historical day")
        _, high, low, close, _ = validate_bar(day,
            (bar.open, bar.high, bar.low, bar.close, bar.volume), self._previous)
        self._previous = day
        self._bars += 1
        self._window = (self._window + [(high, low, close)])[-90:]
        if len(self._window) < 51:
            return
        expected = price_signal(self._window)
        observed = evaluate(self._window)
        self._signals += 1
        self._counts[expected["signal"]] += 1
        different = expected["signal"] != observed["signal"]
        for key in self._errors:
            error = abs(expected[key] - observed[key])
            if not error.is_finite():
                raise ValueError("Non-finite comparison result")
            self._errors[key] = max(self._errors[key], error)
            different = different or error > TOLERANCE
        self._mismatches += int(different)

    def on_end_of_algorithm(self):
        orders = sum(1 for _ in self.transactions.get_orders())
        if orders or self.portfolio.invested:
            raise RuntimeError("Zero-order comparison boundary violated")
        if self._bars != (END - START).days or self._signals != self._bars - 50:
            raise ValueError("Historical coverage is incomplete")
        summary = {"bars": self._bars, "signals": self._signals, "orders": orders,
                   "mismatched_signals": self._mismatches, "signal_counts": self._counts,
                   "max_absolute_errors": {key: str(value) for key, value in self._errors.items()}}
        self.log("ASTRAL_QC|R|" + json.dumps(summary, sort_keys=True, separators=(",", ":")))
