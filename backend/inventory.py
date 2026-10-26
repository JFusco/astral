"""Inventory attribution is evidence, not a substitute for broker availability."""
from decimal import Decimal
import json

from .broker import D
from .config import SYMBOLS
from .custody import analyze, retained

BOOKS = ("manual", "swing", "intraday", "external")


def canonical_symbol(raw):
    return next((s for s, (b, _) in SYMBOLS.items() if b.replace("/", "") == raw.replace("/", "")), None)


def book_for(intent):
    name = intent.get("strategy_id", "manual")
    return name if name in {"swing", "intraday"} else "manual"


def attribute(store, snapshot):
    orders = {r["client_id"]: r for r in store.rows("SELECT * FROM orders")}
    balances, owners, errors, entries = {}, {}, [], {}
    if store.get("fee_reconciliation_required"):
        errors.append({"reason": "Confirmed fee revision requires reconciliation review"})
    for row in store.rows("SELECT payload FROM fills ORDER BY rowid"):
        fill = json.loads(row["payload"])
        order = orders[fill["client_id"]]
        book = "external" if order["external"] else book_for(json.loads(order["request"]).get("intent", {}))
        symbol = canonical_symbol(fill["symbol"]) or fill["symbol"]
        buckets = balances.setdefault(symbol, {b: Decimal(0) for b in BOOKS})
        times = entries.setdefault(symbol, {b: None for b in BOOKS})
        qty = D(fill["quantity"])
        if fill["side"] == "buy":
            if buckets[book] <= 0: times[book] = fill["at"]
            buckets[book] += qty
            owners.setdefault(symbol, set()).add(book)
        else:
            buckets[book] -= qty
            if buckets[book] <= 0: times[book] = None
            if buckets[book] < 0:
                errors.append({"symbol": symbol, "book": book, "reason": "Sell exceeds attributed inventory"})
    gross_books = {s: {b: str(q) for b,q in buckets.items()} for s,buckets in balances.items()}
    # CFEE is a signed asset debit. A late fee without an order ID cannot be
    # assigned across multiple strategy owners. Keep that ambiguity visible.
    for row in store.rows("SELECT payload FROM activities WHERE type='CFEE'"):
        fee = json.loads(row["payload"])
        if fee.get("status") != "executed" or not fee.get("qty"): continue
        symbol = canonical_symbol(fee.get("symbol", ""))
        if symbol not in balances: continue
        if len(owners.get(symbol, set())) == 1:
            owner = next(iter(owners[symbol]))
            balances[symbol][owner] += D(fee["qty"])
        else:
            errors.append({"symbol": symbol, "reason": "Fee cannot be assigned to a unique strategy"})
    paper = store.get('mode') == 'alpaca'
    custody = analyze(**retained(store), snapshot=snapshot, account_id=store.get('account_binding'), mode='alpaca') if paper else {'issues': [], 'additional_debits': {}}
    errors.extend(custody['issues'])
    for symbol, books in custody['additional_debits'].items():
        for book, qty in books.items():
            balances[symbol][book] -= D(qty)
            if balances[symbol][book] <= 0:entries[symbol][book] = None
    actual = {canonical_symbol(p["symbol"]) or p["symbol"]: D(p["qty"]) for p in snapshot.get("positions", [])}
    differences = []
    assets = store.get("assets", {})
    for symbol in set(actual) | set(balances):
        expected = sum(balances.get(symbol, {}).values(), Decimal(0))
        delta = actual.get(symbol, Decimal(0))-expected
        tolerance = D(assets.get(symbol, {}).get("increment") or "0")
        if abs(delta) > tolerance:
            differences.append({"symbol": symbol, "broker_qty": str(actual.get(symbol, 0)),
                                "ledger_qty": str(expected), "difference": str(delta),
                                "reason": "Unreconciled inventory; fees, external activity or missing history"})
    return {"books": {s: {b: str(q) for b, q in v.items()} for s, v in balances.items()},
            **({"gross_books": gross_books, "custody_reconciliation": custody} if paper else {}),
            "entry_times": entries,
            "differences": differences, "errors": errors,
            "status": "needs-review" if differences or errors else "matched",
            "fee_scope": "Recorded CFEE asset debits; ambiguous fees remain unassigned"}
