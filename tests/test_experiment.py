from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import pytest

from backend import experiment
from backend.risk import price_signal, propose
from backend.research import screen
from backend.public_context import evidence_for
from backend.calendar_context import parse_fomc
from backend.store import Store
from test_risk import inputs
from test_dogfood import selection_fixture


def history():
    data=inputs()
    return {"bar_semantics":"executed-trades-only", "complete_page_traversal":True,
            "received_at":data["as_of"], "input_sha256":"fixture",
            "rows":[{"t":b["at"], **{k:b[v] for k,v in (("o","open"),("h","high"),("l","low"),("c","close"),("v","volume"))}} for b in data["bars"]]}


def test_prefix_diagnostic_reuses_live_math_and_never_assumes_fills():
    h=history();result=experiment.diagnose(h)
    assert result["evaluated_prefixes"]==11
    assert result["rows"][-1]["signal"]==propose(**inputs())["signal"]
    assert not result["fills_assumed"] and not result["pnl_computed"] and not result["untouched_holdout"]
    longer=deepcopy(h);longer["rows"][-1]["c"]="10000";longer["rows"][-1]["h"]="10001"
    assert experiment.diagnose(longer)["rows"][:-1]==result["rows"][:-1]


@pytest.mark.parametrize("bad", ["midpoints","missing","future","negative"])
def test_diagnostic_rejects_bad_history(bad):
    h=history()
    if bad=="midpoints":h["bar_semantics"]="midpoints"
    if bad=="missing":h["rows"].pop(12)
    if bad=="future":h["received_at"]=h["rows"][-1]["t"]
    if bad=="negative":h["rows"][0]["v"]="-1"
    with pytest.raises(ValueError):experiment.diagnose(h)


def test_frozen_contract_detects_edit_and_code_drift(tmp_path):
    value=deepcopy(experiment.contract());assert value["code_matches"]
    value.pop("code_matches");path=tmp_path/"contract.json";path.write_text(json.dumps(value))
    value["notional_cap_usd"]="1000";path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="manifest changed"):experiment.contract(path)
    value["manifest_sha256"]=experiment.digest({k:v for k,v in value.items() if k!="manifest_sha256"})
    path.write_text(json.dumps(value))
    for source in experiment.SOURCES:
        dest=tmp_path/source;dest.parent.mkdir(exist_ok=True);dest.write_text("drift")
    assert not experiment.contract(path,tmp_path)["code_matches"]


def test_cap_and_drift_cannot_be_removed_by_research_evidence():
    data=selection_fixture();frozen=experiment.contract()
    packet=screen(**data,experiment=frozen)
    assert float(packet["facts"]["proposed_notional"])<=25
    frozen["code_matches"]=False
    assert any("code changed" in s for s in screen(**data,experiment=frozen)["vetoes"])


def test_observations_deduplicate_and_do_not_create_trades(tmp_path):
    store=Store(tmp_path/"audit.sqlite","alpaca");frozen=experiment.register(store)
    data=selection_fixture();data["as_of"]=datetime.now(timezone.utc).isoformat()
    packet=screen(**data,experiment=frozen)
    for _ in range(3):experiment.observe(store,packet,{"action":"wait"},{})
    assert experiment.state(store)["observations"]==1
    assert not store.rows("SELECT * FROM orders") and not store.rows("SELECT * FROM fills")
    packet["as_of"]="2020-01-01T00:00:00Z";packet["input_hash"]="old"
    experiment.observe(store,packet,{"action":"wait"},{})
    assert experiment.state(store)["observations"]==1
    store.close()


def fomc_html():
    return ("<h4>2026 FOMC Meetings</h4>"+"".join('<div class="fomc-meeting__month"><strong>'+m+'</strong></div><div class="fomc-meeting__date">'+d+'</div>' for m,d in [("January","27-28"),("March","17-18*"),("April","28-29"),("June","16-17*"),("July","28-29"),("September","15-16*"),("October","27-28"),("December","8-9*")])).encode()


def test_fomc_dates_are_conservative_local_intervals_not_invented_release_times():
    rows=parse_fomc(fomc_html());october=rows[-2]
    assert october["event_start"]=="2026-10-27T00:00:00-04:00"
    assert october["event_end_exclusive"]=="2026-10-29T00:00:00-04:00"
    assert rows[-1]["event_start"].endswith("-05:00")
    cross=parse_fomc(fomc_html().replace(b"January",b"Jan/Feb",1).replace(b"27-28",b"31-1",1))[0]
    assert cross["event_end_exclusive"].startswith("2026-02-02")
    vote=parse_fomc(fomc_html().replace(b"27-28",b"22 (notation vote)",1))[0]
    assert vote["event_end_exclusive"].startswith("2026-01-23")
    assert october["created_at"] is None
    with pytest.raises(ValueError):parse_fomc(fomc_html().replace(b"27-28",b"TBD",1))
    with pytest.raises(ValueError):parse_fomc(b"<html>Calendar unavailable</html>")


def context(at="2026-10-26T05:00:00Z"):
    row=parse_fomc(fomc_html())[-2]
    row.update(id="meeting", revision="r1",source="Federal Reserve",source_id="fomc-calendar",category="macro-calendar",symbols=[],first_seen_at=at)
    return {"status":"available","as_of":at,"sources":[{"id":"fomc-calendar","fresh":True,"status":"connected","last_success_at":at}],"items":[row]}


def test_scoped_calendar_context_can_veto_but_never_claim_complete_coverage():
    data=context();e,v,status=evidence_for("BTC",data,data["as_of"])
    assert len(e)==1 and v and "context" in status
    fixture=selection_fixture();fixture["calendar"]=None
    packet=screen(**fixture,public_context=data)
    assert any("events are unknown" in s for s in packet["vetoes"])
    assert packet["facts"]["event_calendar_status"]=="unknown"
    data["items"][0]["first_seen_at"]="2027-01-01T00:00:00Z"
    assert evidence_for("BTC",data,data["as_of"])[:2]==([],[])


def test_stale_source_or_future_revision_is_excluded():
    data=context();data["sources"][0]["fresh"]=False
    assert evidence_for("BTC",data,data["as_of"])[0]==[]
    data["sources"][0]["fresh"]=True;data["items"][0]["updated_at"]="2027-01-01T00:00:00Z"
    assert evidence_for("BTC",data,data["as_of"])[0]==[]


def test_connected_research_refreshes_after_history_and_never_writes_orders(tmp_path,monkeypatch):
    import asyncio
    from backend.config import Settings,SYMBOLS
    from backend.engine import Engine
    from backend.broker import Simulator
    from backend.risk import timestamp
    cfg=Settings(mode='alpaca',db_path=tmp_path/'research.sqlite',api_key='fixture',secret_key='fixture',enable_research=True)
    store=Store(cfg.db_path,cfg.mode);broker=Simulator(cfg,store);engine=Engine(cfg,store,broker)
    order=[];h=history();now=datetime.now(timezone.utc)
    shift=now.replace(hour=0,minute=0,second=0,microsecond=0)-timestamp(h['received_at'])
    for row in h['rows']:row['t']=(timestamp(row['t'])+shift).isoformat()
    h['received_at']=now.isoformat();h['coverage']='fixture';h['source']='fixture'
    async def bars(symbol):order.append('history:'+symbol);return deepcopy(h)
    async def context_read():return {'status':'unavailable','items':[],'sources':[]}
    async def forbidden(*args,**kwargs):raise AssertionError('Research attempted broker mutation')
    original=engine.refresh_quotes
    async def refresh():order.append('quotes');return await original()
    broker.research_bars=bars;broker.submit=forbidden;broker.cancel=forbidden
    engine.refresh_quotes=refresh;monkeypatch.setattr('backend.engine.read_context',context_read)
    async def exercise():
        await engine.refresh_quotes();await engine.reconcile();order.clear()
        result=await engine.research_cycle()
        assert order[:len(SYMBOLS)]==['history:'+s for s in SYMBOLS]
        assert order[len(SYMBOLS)]=='quotes'
        assert len(result['packets'])==8 and not any(p['eligible'] for p in result['packets'])
        assert experiment.state(store)['observations']==1
        assert not store.rows('SELECT * FROM orders') and not store.rows('SELECT * FROM fills')
        await broker.close()
    asyncio.run(exercise());store.close()
