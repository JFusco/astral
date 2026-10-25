"""Read-only venue discovery. A listing is never execution authorization."""
import hashlib
import json

from .config import SYMBOLS
from .risk import number


def discover_crypto(raw_assets, as_of):
    rows, seen = [], set()
    for raw in raw_assets:
        pair = raw.get("symbol", "")
        reasons = []
        if not raw.get("id"): reasons.append("Missing stable venue asset ID")
        if pair in seen: reasons.append("Duplicate venue pair")
        seen.add(pair)
        if raw.get("class") != "crypto": reasons.append("Asset class is not verified crypto")
        if not pair.endswith("/USD") or pair.count("/") != 1: reasons.append("USD quote pair required")
        if raw.get("status") != "active" or raw.get("tradable") is not True: reasons.append("Venue asset is inactive or not tradable")
        for field in ("min_trade_increment", "min_order_size", "price_increment"):
            try:
                if number(raw.get(field)) <= 0: raise ValueError()
            except (ValueError, TypeError): reasons.append("Missing or invalid "+field)
        approved = any(value == (pair, "crypto") for value in SYMBOLS.values())
        rows.append({"asset_id": raw.get("id"), "pair": pair, "venue": "alpaca", "location": "us",
                     "status": raw.get("status"), "tradable": raw.get("tradable") is True,
                     "increment": raw.get("min_trade_increment"), "minimum": raw.get("min_order_size"),
                     "tick": raw.get("price_increment"), "metadata_eligible": not reasons,
                     "metadata_vetoes": reasons, "execution_allowlisted": approved,
                     "research_ready": False, "execution_enabled": False,
                     "remaining_requirements": ["Fresh quotes and normalized depth", "Point-in-time liquidity and signal history",
                                                "News and protocol or supply event coverage", "Identity and listing review", "Portfolio risk and strategy validation"]})
    # Duplicate identities invalidate every occurrence, including the first.
    ids = [r["asset_id"] for r in rows]
    for row in rows:
        if ids.count(row["asset_id"]) > 1 or sum(r["pair"] == row["pair"] for r in rows) > 1:
            row["metadata_eligible"] = False
            row["metadata_vetoes"].append("Duplicate venue identity requires review")
    result = {"version": "crypto-discovery-v1", "as_of": as_of, "venue": "alpaca", "location": "us",
              "scope": "Active-asset API response; discovery only, not a trade recommendation", "assets": sorted(rows, key=lambda r:r["pair"])}
    result["input_hash"] = hashlib.sha256(json.dumps(result,sort_keys=True,separators=(",", ":")).encode()).hexdigest()
    return result
