"""Frozen research contract and append-only observations. No execution interface."""
from collections import Counter
from datetime import timedelta
from pathlib import Path
import hashlib
import json

from .config import ROOT
from .risk import number as D, timestamp, price_signal
from .store import utcnow, dumps

MANIFEST = ROOT / "experiments/btc-daily-swing-v1.json"
SOURCES = ("backend/risk.py", "backend/timing.py", "backend/research.py", "backend/experiment.py")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def source_hashes(root=ROOT):
    return {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in SOURCES}


def contract(path=MANIFEST, root=ROOT):
    if not path.exists(): return None
    value = json.loads(path.read_text())
    frozen = value.pop("manifest_sha256")
    if digest(value) != frozen: raise ValueError("Frozen experiment manifest changed")
    value["manifest_sha256"] = frozen
    value["code_matches"] = value["source_sha256"] == source_hashes(root)
    return value


def register(store):
    value = contract()
    if value is None: return None
    prior = store.get("frozen_experiment")
    if prior and prior["manifest_sha256"] != value["manifest_sha256"]:
        raise ValueError("Existing experiment cannot be silently replaced")
    if prior is None:
        prior = {"id": value["id"], "manifest_sha256": value["manifest_sha256"], "registered_at": utcnow()}
        store.put("frozen_experiment", prior)
        store.event("experiment_registered", prior)
    return {**value, "registered_at": prior["registered_at"]}


def observe(store, packet, timing, context):
    value = register(store)
    if not value or packet.get("symbol") != value["symbol"]: return
    store.db.execute("""CREATE TABLE IF NOT EXISTS experiment_observations(
        id TEXT PRIMARY KEY,experiment TEXT NOT NULL,at TEXT NOT NULL,payload TEXT NOT NULL)""")
    now = utcnow()
    if packet.get("facts", {}).get("experiment_manifest") != value["manifest_sha256"]: return
    if timestamp(packet["as_of"]) < timestamp(value["registered_at"]): return
    payload = {"experiment": value["id"], "manifest_sha256": value["manifest_sha256"],
               "recorded_at": now, "code_matches": value["code_matches"], "packet": packet,
               "timing": timing, "context": context, "execution_enabled": False, "fill_assumed": False,
               "scope": "Prospective evidence and veto journal; no simulated position or portfolio"}
    key = digest({"experiment": value["manifest_sha256"], "packet_hash": packet["input_hash"]})
    with store.transaction():
        cursor = store.db.execute("INSERT OR IGNORE INTO experiment_observations VALUES(?,?,?,?)",
                                 (key, value["id"], now, dumps(payload)))
        if cursor.rowcount: store.event("experiment_observation", {"id": key, "code_matches": value["code_matches"], "execution_enabled": False})


def state(store):
    value = contract()
    if value is None: return None
    prior = store.get("frozen_experiment")
    rows = []
    if store.rows("SELECT name FROM sqlite_master WHERE name='experiment_observations'"):
        rows = store.rows("SELECT at,payload FROM experiment_observations WHERE experiment=? ORDER BY at DESC LIMIT 12", (value["id"],))
        count = store.rows("SELECT COUNT(*) n FROM experiment_observations WHERE experiment=?", (value["id"],))[0]["n"]
    else: count = 0
    return {"id": value["id"], "manifest_sha256": value["manifest_sha256"], "code_matches": value["code_matches"],
            "registered_at": prior["registered_at"] if prior else None, "observations": count,
            "last_observation_at": rows[0]["at"] if rows else None, "notional_cap_usd": value["notional_cap_usd"],
            "execution_enabled": False, "fill_assumed": False, "promotion_enabled": False,
            "scope": "Prospective evidence journal; portfolio replay and profitability remain unvalidated",
            "history_diagnostic": store.get("experiment_diagnostic"),
            "recent": [{"at": r["at"], "code_matches": json.loads(r["payload"])["code_matches"],
                        "action": json.loads(r["payload"])["timing"]["action"],
                        "vetoes": json.loads(r["payload"])["packet"]["vetoes"]} for r in rows]}


def diagnose(history):
    """Retrospective price-only prefixes. Never pretend these were known earlier."""
    if history.get("bar_semantics") != "executed-trades-only" or not history.get("complete_page_traversal"):
        raise ValueError("Completed same-venue execution history required")
    rows = history["rows"]
    if len(rows) < 51: raise ValueError("At least 51 daily bars required")
    clean = [];previous = None;results = []
    for raw in rows:
        when = timestamp(raw["t"])
        if previous and when-previous != timedelta(days=1): raise ValueError("Missing or unordered daily interval")
        if when+timedelta(days=1) > timestamp(history["received_at"]): raise ValueError("Incomplete bar")
        o,h,l,c,v = (D(raw[k]) for k in ("o","h","l","c","v"))
        if min(o,h,l,c,v) <= 0 or l > min(o,c) or h < max(o,c) or l > h: raise ValueError("Invalid executed-trade OHLC")
        clean.append((h,l,c));previous=when
        if len(clean) < 51: continue
        # Match the live evidence window of at most 90 bars exactly.
        price = price_signal(clean[-90:])
        results.append({"closed_at": (when+timedelta(days=1)).isoformat(),
                        **{key: str(val) for key,val in price.items()}})
    return {"scope": "Retrospective price-only signal diagnostic; development dataset already inspected",
            "history_input_sha256": history["input_sha256"], "observed_at": history["received_at"],
            "daily_bars": len(rows), "evaluated_prefixes": len(results),
            "signal_counts": dict(Counter(row["signal"] for row in results)), "rows": results,
            "fills_assumed": False, "pnl_computed": False, "untouched_holdout": False,
            "point_in_time_news_available": False, "profitability_validated": False,
            "limitations": ["First 50 bars are warmup; no parameter search",
                "Raw price hypothesis only; live cost, liquidity, news and risk gates still apply",
                "No historical executable quotes, queue positions or complete news/calendar revisions",
                "No cash, hypothetical inventory, costs, return or fill probability inferred from candles"]}
