"""Validate provider fee records without estimating missing fees or rewriting fills."""
import hashlib
import json
from .risk import number as D


def validate_activity(item):
    if not isinstance(item, dict) or not item.get("id") or item.get("activity_type") not in {"CFEE", "FEE"}:
        raise ValueError("Unrecognized fee activity")
    if item.get("status") != "executed":
        return "pending-confirmation"
    if item["activity_type"] == "CFEE":
        # Positive refunds, unknown currencies and missing quantities need a
        # separate verified contract; they cannot silently change custody here.
        symbol = str(item.get("symbol", "")).replace("/", "")
        if symbol not in {"BTCUSD", "ETHUSD", "SOLUSD"} or D(item.get("qty")) >= 0:
            raise ValueError("Executed asset fee must identify a supported pair and a negative finite debit")
    elif D(item.get("net_amount")) > 0:
        raise ValueError("Positive fee cash adjustment requires review")
    return "confirmed-provider-record"


def record_fee(store, item):
    if not isinstance(item, dict) or not item.get("id"):
        raise ValueError("Unrecognized fee activity")
    try:
        canonical = json.dumps(item, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except ValueError:
        # Preserve nonfinite provider numbers as explicit evidence, never debits.
        safe = json.loads(json.dumps(item), parse_constant=lambda value: {"nonfinite_number": value})
        canonical = json.dumps(safe, sort_keys=True, separators=(",", ":"), allow_nan=False)
    revision = hashlib.sha256(canonical.encode()).hexdigest()
    store.db.execute("""CREATE TABLE IF NOT EXISTS activity_revisions(
        id TEXT NOT NULL,revision TEXT NOT NULL,at TEXT NOT NULL,payload TEXT NOT NULL,PRIMARY KEY(id,revision))""")
    from .store import utcnow
    store.db.execute("INSERT OR IGNORE INTO activity_revisions VALUES(?,?,?,?)", (item["id"], revision, utcnow(), canonical))
    existing = store.rows("SELECT payload FROM activities WHERE id=?", (item["id"],))
    if existing:
        prior = json.loads(existing[0]["payload"])
        if prior.get("status") == "executed" and prior != item:
            store.put("fee_reconciliation_required", {"id": item["id"], "at": utcnow(),
                       "reason": "Previously confirmed provider fee changed; review retained revisions"})
            raise ValueError("Confirmed fee changed; retained revision requires reconciliation review")
    return validate_activity(item)
