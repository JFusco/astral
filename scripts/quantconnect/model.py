"""Independent port of the registered BTC price hypothesis, for comparison only."""
from datetime import date, timedelta
from decimal import Decimal, localcontext

CONTRACT = "btc-signal-parity-v2"
START = date(2025, 1, 1)
END = date(2025, 7, 1)  # Exclusive; historical development data only.
FROZEN_MANIFEST = "a1cd3a0ed46e16460f8d7aa47f54ee795239b4405456b63bc766a46223ee7f08"
FIELDS = ("atr", "fast_mean", "slow_mean", "breakout", "signal")


def validate_bar(day, values, previous=None):
    if not START <= day < END or (previous is not None and day != previous + timedelta(days=1)):
        raise ValueError("Out-of-period, missing, duplicated or unordered daily bar")
    if len(values) != 5:
        raise ValueError("Expected open, high, low, close and volume")
    numbers = tuple(Decimal(str(value)) for value in values)
    if any(not value.is_finite() or value <= 0 for value in numbers):
        raise ValueError("Daily OHLCV must be finite and positive")
    opening, high, low, close, _ = numbers
    if low > min(opening, close) or high < max(opening, close) or low > high:
        raise ValueError("Invalid daily OHLC range")
    return numbers


def evaluate(window):
    """Reinitialize Wilder ATR within each capped window, as frozen v1 does."""
    if not 51 <= len(window) <= 90:
        raise ValueError("Expected 51 to 90 completed bars")
    with localcontext() as context:
        context.prec = 34
        ranges = []
        for previous, current in zip(window, window[1:]):
            high, low, _ = current
            ranges.append(max(high - low, abs(high - previous[2]), abs(low - previous[2])))
        atr = sum(ranges[:14], Decimal(0)) / Decimal(14)
        for true_range in ranges[14:]:
            atr = (Decimal(13) * atr + true_range) / Decimal(14)
        if atr <= 0:
            raise ValueError("Expected positive volatility")
        fast = sum(row[2] for row in window[-20:]) / Decimal(20)
        slow = sum(row[2] for row in window[-50:]) / Decimal(50)
        breakout = max(row[0] for row in window[-21:-1])
        signal = "hold"
        if window[-1][2] > fast and fast > slow and window[-1][2] > breakout:
            signal = "entry_candidate"
        elif window[-1][2] < slow:
            signal = "exit_review"
        return dict(zip(FIELDS, (atr, fast, slow, breakout, signal)))
