"""Quote-only liquidity experiment. No orders, fills, positions, P&L or promotion."""
from dataclasses import asdict, dataclass
from datetime import timedelta
from decimal import Decimal, ROUND_DOWN, localcontext

from .market_depth import validate_book
from .risk import number as D, timestamp


@dataclass(frozen=True)
class Policy:
    version: str = "btc-liquidity-depth-v1"
    notional_cap: str = "25"
    daily_turnover_fraction: str = "0.0002"  # 2 bps of observed venue daily turnover
    level_participation: str = "0.01"
    retained_depth_fraction: str = "0.5"     # Model half of displayed size disappearing
    collar_bps: str = "10"
    max_spread_bps: str = "10"
    max_round_trip_cost_bps: str = "75"
    fee_bps_per_side: str = "25"            # Unconfirmed assumption, not an accounting fee
    max_history_age_seconds: int = 1800
    max_asset_age_seconds: int = 3600


SCENARIOS = (
    ("base_half_depth", "0.5", "25", "1", "0"),
    ("ninety_percent_depth_loss", "0.1", "25", "1", "0"),
    ("ninety_nine_percent_depth_loss", "0.01", "25", "1", "0"),
    ("double_fees", "0.5", "50", "1", "0"),
    ("five_times_spread", "0.5", "25", "5", "0"),
    ("two_percent_exit_gap", "0.5", "25", "1", "200"),
    ("no_exit_depth", "0", "25", "1", "0"),
)


def floor(value, step):
    if step<=0:raise ValueError("Invalid quantity increment")
    return (value/step).to_integral_value(rounding=ROUND_DOWN)*step


def turnover(history, now, policy):
    if (history.get("source")!="alpaca-us-executed-trades" or history.get("bar_semantics")!="executed-trades-only"
        or history.get("complete_page_traversal") is not True
        or not 0<=(now-timestamp(history["received_at"])).total_seconds()<=policy.max_history_age_seconds):
        raise ValueError("Unverified, stale or future history")
    rows=history["rows"][-21:]
    if len(rows)!=21:raise ValueError("21 completed daily bars required")
    previous=None
    for row in rows:
        t=timestamp(row["t"])
        if t.hour or t.minute or t.second or t.microsecond or t.utcoffset()!=timedelta(0):raise ValueError("Expected UTC daily bar")
        if t+timedelta(days=1)>now or (previous and t-previous!=timedelta(days=1)):raise ValueError("Incomplete/unordered daily history")
        if D(row["dollar_volume"])<=0:raise ValueError("Missing executed-trade dollar volume")
        previous=t
    if now-(previous+timedelta(days=1))>timedelta(days=1):raise ValueError("Daily history has not rolled forward")
    # Match baseline: preceding 20 days, not the latest completed signal day.
    return sum((D(r["dollar_volume"]) for r in rows[:-1]),Decimal(0))/20


def walk(levels, quantity, reference, policy, depth_fraction):
    remaining=quantity;value=Decimal(0);used=0;worst=reference
    for price,size in levels:
        available=size*D(policy.level_participation)*depth_fraction
        take=min(remaining,available)
        if take>0:value+=take*price;remaining-=take;used+=1;worst=price
        if remaining<=0:break
    return {"covered":remaining<=0,"quantity":str(quantity-remaining),"notional":str(value),"levels_used":used,
            "average_price":str(value/quantity) if remaining<=0 and quantity>0 else None,"worst_price":str(worst)}


def evaluate(snapshot, *, as_of, policy=Policy()):
    with localcontext() as ctx:
        ctx.prec=40
        try:return _evaluate(snapshot,as_of,policy)
        except (ValueError,KeyError,TypeError,ArithmeticError) as exc:
            return {"version":policy.version,"status":"invalid-evidence","reasons":[str(exc)[:200]],
                    "as_of":as_of,"execution_enabled":False,"fill_assumed":False,"profitability_validated":False}


def _evaluate(snapshot, as_of, policy):
    now=timestamp(as_of);quote=snapshot["quote"];raw=snapshot["raw_book"];asset=snapshot["asset"]
    depth=validate_book("BTC",raw,quote,received_at=as_of)
    if quote.get("size_unit")!="base_asset" or quote.get("depth",{}).get("raw_sha256")!=depth["raw_sha256"]:
        raise ValueError("Quote is not bound to this normalized raw depth")
    if asset.get("tradable") is not True or not 0<=(now-timestamp(asset["at"])).total_seconds()<=policy.max_asset_age_seconds:
        raise ValueError("Stale, future or untradable venue metadata")
    step,minimum,tick=(D(asset[k]) for k in ("increment","minimum","price_increment"))
    if min(step,minimum,tick)<=0:raise ValueError("Invalid venue minima/tick")
    adv=turnover(snapshot["history"],now,policy);bid,ask=D(quote["bid"]),D(quote["ask"])
    collar=D(policy.collar_bps)/10000
    # A modeled IOC buy limit must stay INSIDE the collar after tick rounding.
    limit=floor(ask*(1+collar),tick)
    if limit<ask:raise ValueError("Venue tick cannot represent a buy inside collar")
    buys=[(D(r["p"]),D(r["s"])) for r in raw["a"] if ask<=D(r["p"])<=limit and D(r["s"])>0]
    sells=[(D(r["p"]),D(r["s"])) for r in raw["b"] if bid*(1-collar)<=D(r["p"])<=bid and D(r["s"])>0]
    base_fraction=D(policy.retained_depth_fraction)
    def capacity(levels):return sum((p*s*D(policy.level_participation)*base_fraction for p,s in levels),Decimal(0))
    quantity_cap=min(sum((s*D(policy.level_participation)*base_fraction for _,s in buys),Decimal(0)),
                     sum((s*D(policy.level_participation)*base_fraction for _,s in sells),Decimal(0)))
    budget=min(D(policy.notional_cap),adv*D(policy.daily_turnover_fraction))
    target=floor(budget/limit,step)
    qty=floor(min(target,quantity_cap),step)
    fee=D(policy.fee_bps_per_side)/10000
    exit_qty=floor(qty*(1-fee),step)
    # Venue FAQ states a USD minimum as well as metadata's base-quantity minimum.
    minimum_usd=D("1")
    sized=qty>=minimum and exit_qty>=minimum and qty*ask>=minimum_usd and exit_qty*bid>=minimum_usd
    spread=(ask-bid)/((ask+bid)/2)*10000
    baseline_budget=min(D(policy.notional_cap),D(depth["top_one_percent_cap_usd"]))
    baseline_qty=floor(baseline_budget/limit,step)
    baseline_pass=adv>=1000000 and baseline_qty>=minimum and baseline_qty*ask>=minimum_usd
    scenarios=[]
    for name,retained,fee_bps,spread_multiple,gap in SCENARIOS:
        buy=walk(buys,qty,ask,policy,D(retained));sell_qty=floor(qty*(1-D(fee_bps)/10000),step)
        sell=walk(sells,sell_qty,bid,policy,D(retained));reasons=[];cost=None
        if not sized or sell_qty<minimum or sell_qty*bid<minimum_usd:reasons.append("Rounded entry or fee-reduced exit below venue minimum")
        if qty<target:reasons.append("Full target size not covered; reduced feasible size is diagnostic only")
        if not buy["covered"] or not sell["covered"]:reasons.append("Displayed participation depth cannot cover both modeled legs")
        if spread*D(spread_multiple)>D(policy.max_spread_bps):reasons.append("Stressed spread exceeds experiment cap")
        if qty>0 and sell_qty>0 and buy["covered"] and sell["covered"]:
            buy_slip=max(Decimal(0),(D(buy["average_price"])/ask-1)*10000)
            sell_slip=max(Decimal(0),(1-D(sell["average_price"])/bid)*10000)
            # Fees and flooring are modeled in received BTC and received USD.
            spent=D(buy["notional"])
            received=D(sell["notional"])*(1-D(fee_bps)/10000)
            cost=(1-received/spent)*10000+spread*(D(spread_multiple)-1)+D(gap)
            if cost>D(policy.max_round_trip_cost_bps):reasons.append("Modeled round-trip cost exceeds experiment cap")
        else:buy_slip=sell_slip=None;reasons.append("Modeled round-trip cost unavailable")
        scenarios.append({"name":name,"feasible_quote_model":not reasons,"reasons":reasons,
                          "depth_retained":retained,"fee_bps_per_side":fee_bps,"round_trip_cost_bps":str(cost) if cost is not None else None,
                          "buy_walk_bps":str(buy_slip) if buy_slip is not None else None,"sell_walk_bps":str(sell_slip) if sell_slip is not None else None,
                          "buy":buy,"sell":sell,"fill_assumed":False})
    return {"version":policy.version,"as_of":as_of,"status":"evaluated","policy":asdict(policy),
            "average_daily_dollars":str(adv),"spread_bps":str(spread),"target_notional_usd":str(budget),
            "target_quantity":str(target),"modeled_quantity":str(qty),"modeled_max_entry_value":str(qty*limit),
            "modeled_exit_quantity_after_assumed_fee":str(exit_qty),"modeled_buy_limit":str(limit),
            "capacity_usd_after_half_depth_loss":{"buy":str(capacity(buys)),"sell":str(capacity(sells))},
            "baseline":{"id":"btc-daily-swing-v1","liquidity_passed":baseline_pass,"top_one_percent_cap_usd":depth["top_one_percent_cap_usd"],"quantity":str(baseline_qty)},
            "scenarios":scenarios,"execution_enabled":False,"fill_assumed":False,"profitability_validated":False,
            "scope":"Liquidity/cost comparison only; fees assumed, no queue/impact/fill probability or signal/portfolio authorization"}
