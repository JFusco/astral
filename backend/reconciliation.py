"""Read-only reconciliation analysis. Hypotheses cannot become ledger entries."""
from decimal import Decimal, ROUND_UP, localcontext


def audit_crypto(*, symbol, orders, activities, positions, fee_rate="0.0025", increment="0.000000001"):
    """Compare authoritative gross executions and positions; explain, never waive.

    Fee rate and per-fill upward rounding are explicit hypotheses unless an
    executed CFEE record independently confirms the debit. No mutation or order
    capability is available here. Scope is the supplied bounded history window.
    """
    canonical = lambda s: str(s).replace("/", "")
    key = canonical(symbol)
    with localcontext() as context:
        context.prec = 40
        rate, step = Decimal(fee_rate), Decimal(increment)
        if not 0 <= rate < 1 or step <= 0:
            raise ValueError("Invalid fee hypothesis")
        selected = [o for o in orders if canonical(o.get("symbol")) == key]
        by_id = {o["id"]: o for o in selected}
        if len(by_id) != len(selected): raise ValueError("Duplicate broker order IDs")
        fills = [a for a in activities if a.get("activity_type") == "FILL" and canonical(a.get("symbol")) == key]
        seen, errors, details = {}, [], []
        for f in fills:
            if f["id"] in seen and f != seen[f["id"]]: raise ValueError("Conflicting execution ID")
            seen[f["id"]] = f
        fills = list(seen.values())
        for f in fills:
            if f.get("order_id") not in by_id: errors.append("Execution references an order outside the supplied window")
            if f.get("side") not in {"buy", "sell"} or Decimal(f["qty"]) <= 0 or Decimal(f["price"]) <= 0:
                raise ValueError("Invalid execution")
        for order in selected:
            children = [f for f in fills if f["order_id"] == order["id"]]
            qty = sum((Decimal(f["qty"]) for f in children), Decimal(0))
            value = sum((Decimal(f["qty"])*Decimal(f["price"]) for f in children), Decimal(0))
            matched = qty == Decimal(order["filled_qty"] or "0") and all(f["side"] == order["side"] for f in children)
            price_matches = qty == 0 or abs(value-qty*Decimal(order["filled_avg_price"])) <= Decimal("0.00000001")
            if not matched or not price_matches: errors.append("Gross execution records differ from cumulative order readback")
            details.append({"client_order_id": order.get("client_order_id"), "side": order["side"], "partial_execution_count": len(children),
                            "gross_quantity": str(qty), "gross_value": str(value), "order_quantity_matches": matched, "order_value_matches": price_matches})
        gross = sum((Decimal(f["qty"])*(1 if f["side"] == "buy" else -1) for f in fills), Decimal(0))
        fee_rows = [a for a in activities if a.get("activity_type") == "CFEE" and canonical(a.get("symbol")) == key and a.get("status") == "executed"]
        fees = {}
        for row in fee_rows:
            if row["id"] in fees and fees[row["id"]] != row: raise ValueError("Conflicting fee ID")
            fees[row["id"]] = row
        confirmed = sum((Decimal(f["qty"]) for f in fees.values()), Decimal(0))
        position = sum((Decimal(p["qty"]) for p in positions if canonical(p.get("symbol")) == key), Decimal(0))
        delta = position-gross-confirmed
        hypothesis = sum(((Decimal(f["qty"])*rate/step).to_integral_value(rounding=ROUND_UP)*step for f in fills if f["side"] == "buy"), Decimal(0))
        return {"symbol": symbol, "scope": "Supplied broker-history window; does not assert complete account history", "orders": details,
                "execution_count": len(fills), "gross_net_quantity": str(gross), "confirmed_asset_fee_quantity": str(confirmed),
                "broker_position_quantity": str(position), "unexplained_quantity": str(delta), "errors": errors,
                "status": "matched" if delta == 0 and not errors else "needs-confirmation",
                "fee_hypothesis": {"rate": str(rate), "asset_increment": str(step), "rounding": "UP separately per buy execution; unverified assumption",
                                   "quantity": str(hypothesis), "matches_unexplained_debit": delta == -hypothesis and hypothesis > 0,
                                   "confirmed": False, "source": "https://docs.alpaca.markets/us/docs/crypto-fees"},
                "execution_authorized": False, "ledger_adjustment_created": False}
