"""Same-venue REST book/quote validation. Visible depth never guarantees a fill."""
from decimal import Decimal, localcontext
import hashlib
import json

from .risk import number as D, timestamp

VERSION = "alpaca-us-depth-v1"
SOURCES = ["https://docs.alpaca.markets/us/docs/real-time-crypto-pricing-data",
           "https://alpaca.markets/learn/visualizing-orderbook-data-with-alpaca-crypto-api"]


def validate_book(symbol, raw, quote, *, received_at):
    with localcontext() as context:
        context.prec = 40
        return _validate(symbol, raw, quote, received_at)


def _validate(symbol, raw, quote, received_at):
    if symbol not in {"BTC", "ETH", "SOL"} or quote.get("source") != "alpaca-us":
        raise ValueError("Unsupported symbol or execution venue")
    now, book_at, quote_at = timestamp(received_at), timestamp(raw["t"]), timestamp(quote["at"])
    if not 0 <= (now-book_at).total_seconds() <= 15 or not 0 <= (now-quote_at).total_seconds() <= 15:
        raise ValueError("Book or quote is stale/future-dated")
    if abs((book_at-quote_at).total_seconds()) > 1:
        raise ValueError("Book and quote are not contemporaneous")
    sides = {}
    for side in ("b", "a"):
        rows = raw[side]
        if not isinstance(rows, list) or len(rows) > 500: raise ValueError("Invalid book depth budget")
        levels = [(D(r["p"]), D(r["s"])) for r in rows]
        if any(p <= 0 or size < 0 for p, size in levels): raise ValueError("Invalid book level")
        levels = [(p, size) for p, size in levels if size > 0]
        prices = [p for p, _ in levels]
        if not levels or len(prices) != len(set(prices)) or prices != sorted(prices, reverse=side=="b"):
            raise ValueError("Book must have unique, ordered, nonempty sides")
        sides[side] = levels
    bid, ask = sides["b"][0][0], sides["a"][0][0]
    if ask < bid: raise ValueError("Crossed orderbook")
    for side, price_key, size_key in (("b", "bid", "bid_size"), ("a", "ask", "ask_size")):
        if sides[side][0] != (D(quote[price_key]), D(quote[size_key])):
            raise ValueError("Book top and latest quote disagree; no size normalization")
    # Alpaca's level-2 guide defines sizes as quantities of the underlying asset.
    # Its current REST p/s schema is checked against the same-venue quote fields.
    # No equities round-lot multiplier or USD-size conversion is applied.
    result = {"version": VERSION, "symbol": symbol, "venue": "alpaca-us", "at": raw["t"],
              "received_at": received_at, "status": "validated", "size_unit": "base_asset",
              "unit_basis": "Underlying-asset quantities in Alpaca level-2 guide; matched current REST book/quote",
              "unit_sources": SOURCES, "quote_at": quote["at"],
              "raw_sha256": hashlib.sha256(json.dumps(raw, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
              "bid_levels": len(sides["b"]), "ask_levels": len(sides["a"]),
              "spread_bps": str((ask-bid)/((ask+bid)/2)*10000),
              "top_bid_notional": str(bid*sides["b"][0][1]), "top_ask_notional": str(ask*sides["a"][0][1]),
              "top_one_percent_cap_usd": str(min(bid*sides["b"][0][1], ask*sides["a"][0][1])*D(".01")),
              "fill_guaranteed": False, "execution_enabled": False}
    for key, levels, reference, is_buy in (("buy", sides["a"], ask, True), ("sell", sides["b"], bid, False)):
        collar = reference*(D("1.001") if is_buy else D(".999"))
        eligible = [(p, size) for p, size in levels if (p <= collar if is_buy else p >= collar)]
        result[key+"_visible_notional_inside_10bps"] = str(sum((p*s for p, s in eligible), Decimal(0)))
        result[key+"_one_percent_capacity_usd"] = str(sum((p*s*D(".01") for p, s in eligible), Decimal(0)))
    return result
