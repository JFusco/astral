from copy import deepcopy
from dataclasses import replace
from datetime import datetime,timedelta,timezone
from decimal import Decimal as D,localcontext
import json
import sqlite3
import pytest

from backend.portfolio_replay import Assumptions,replay
from backend.replay_runner import synthetic_events,stress_suite,export_events

BASE=datetime(2026,10,25,12,tzinfo=timezone.utc)
def at(s):return (BASE+timedelta(seconds=s)).isoformat()
def q(s,bid='100',ask='100.02',depth='100',**extra):
    quote={'at':at(s),'bid':bid,'ask':ask,'bid_size':depth,'ask_size':depth,'size_unit':'base_asset','source':'synthetic-fixture'}
    quote.update(extra)
    return {'id':'q:'+str(s),'type':'quote','observed_at':at(s),'quote':quote}
def pick(s=1,**extra):
    c={'as_of':at(s),'expires_at':at(300),'eligible':True,'code_matches':True,'inventory_gate_passed':True,
       'entries_halted':False,'broker_pending_order':False,'signal':'entry_candidate','latest_closed_at':at(-1),
       'quantity':'0.249','notional':'25','stop':'98','target':'104'};c.update(extra)
    return {'id':'pick:'+str(s),'type':'candidate','observed_at':at(s),'candidate':c}
def clock(s):return {'id':'clock:'+str(s),'type':'clock','observed_at':at(s)}


def test_cash_is_reserved_before_fill_and_price_collar_bounds_purchase():
    initial=[q(0),pick()];r=replay(initial)
    assert not r['fills'] and D(r['reserved_cash'])>0
    assert D(r['trace'][-1]['available_cash'])<D(r['cash'])
    filled=replay(initial+[q(6)])
    assert len(filled['fills'])==1 and filled['fills'][0]['at']>filled['fills'][0]['decision_at']
    assert D(filled['fills'][0]['value'])<=25 and filled['reserved_cash']=='0'
    assert D(filled['cash'])==D('100000')-D(filled['fills'][0]['value'])-D(filled['fills'][0]['fee_quote'])


def test_quote_fees_round_trip_and_base_fee_dust_are_explicit():
    base=replay(synthetic_events())
    assert [f['side'] for f in base['fills']]==['buy','sell']
    assert base['quantity']=='0.000' and D(base['hypothetical_fee_quote'])>0
    asset=replay(synthetic_events(),replace(Assumptions(),fee_mode='buy-base-sell-quote'))
    gross=sum(D(f['quantity']) for f in asset['fills'] if f['side']=='buy')
    sold=sum(D(f['quantity']) for f in asset['fills'] if f['side']=='sell')
    assert gross-sold-D(asset['hypothetical_fee_base'])==D(asset['quantity'])
    assert D(asset['quantity'])>=0 and not asset['profitability_validated']


@pytest.mark.parametrize('field,value',[('eligible',False),('code_matches',False),('inventory_gate_passed',False),('entries_halted',True),('broker_pending_order',True),('signal','hold'),('latest_closed_at',at(2)),('expires_at',at(1))])
def test_each_entry_gate_remains_active(field,value):
    candidate=pick(**{field:value})
    if field=='expires_at':candidate=pick(2,as_of=at(0),expires_at=value)
    r=replay([q(0),candidate,q(6)])
    assert not r['fills']


def test_unverified_depth_cannot_be_turned_into_hypothetical_execution():
    r=replay([q(0,size_unit='unverified'),pick(),q(6,size_unit='unverified')])
    assert not r['orders'] and not r['fills']
    assert r['counters']['unverified_depth_entry']>0


def test_ioc_partial_is_terminal_and_never_oversells_net_base_inventory():
    cfg=replace(Assumptions(),fee_mode='buy-base-sell-quote')
    r=replay([q(0,depth='.02'),pick(),q(6,depth='.02'),q(12,'105','105.02',depth='.02'),q(18,'105','105.02',depth='.02')],cfg)
    assert r['orders'][0]['status']=='ioc-partial'
    assert sum(D(f['quantity']) for f in r['fills'] if f['side']=='sell')<=sum(D(f['quantity'])-D(f['fee_base']) for f in r['fills'] if f['side']=='buy')
    assert all(D(row['quantity'])>=0 for row in r['trace'])


def test_cancel_keeps_reservation_and_models_fill_race_until_ack():
    cfg=replace(Assumptions(),tif='gtc',cancel_latency_seconds=30,latency_seconds=0)
    rows=[q(0,depth='.02'),pick(),q(6,depth='.02'),q(12,'90','90.02',depth='.02'),q(18,'90','90.02',depth='.02'),clock(43)]
    r=replay(rows,cfg)
    assert r['fills'][1]['cancel_pending']
    assert D(r['trace'][3]['reserved_cash'])>0 and D(r['trace'][4]['reserved_cash'])>0
    assert r['orders'][0]['status']=='cancel-confirmed' and r['reserved_cash']=='0'
    assert r['pending_order'] is None  # Last executable quote is stale; no fictional stop fill.


def test_expiry_requests_cancel_but_keeps_a_possible_racing_fill_visible():
    events=[q(0),pick(expires_at=at(3)),q(6),q(12)]
    racing=replay(events)
    assert len(racing['fills'])==1 and racing['fills'][0]['cancel_pending']
    assert racing['reserved_cash']=='0'
    canceled=replay(events,replace(Assumptions(),latency_seconds=30))
    assert not canceled['fills'] and canceled['orders'][0]['status']=='cancel-confirmed'


def test_stop_gap_fills_only_subsequent_observed_bid_inside_sell_limit():
    r=replay([q(0),pick(),q(6),q(12,'90','90.02'),q(18,'89','89.02'),q(24,'89','89.02')])
    sell=[f for f in r['fills'] if f['side']=='sell']
    assert sell and D(sell[0]['price'])==89
    assert sell[0]['at']==at(24) and sell[0]['price']!='98'
    assert any(o['status']=='ioc-nonfill' for o in r['orders'])


def test_stale_or_repeated_quote_cannot_fill_order_or_regenerate_depth():
    source=q(0);later=q(6);later['quote']['at']=at(0)
    r=replay([source,pick(),later,clock(20),q(21,at=at(0))])
    assert not r['fills'] and r['counters']['duplicate_or_out_of_order_quotes']==2
    stale=q(20);stale['quote']['at']=at(1)
    assert not replay([q(0),pick(),stale])['fills']


def test_duplicate_arrivals_deduplicate_and_conflicting_ids_fail():
    events=[q(0),pick(),q(6)];r=replay(events+[deepcopy(events[-1])])
    assert len(r['fills'])==1 and r['counters']['duplicate_events']==1
    bad=deepcopy(events[-1]);bad['quote']['ask']='101'
    with pytest.raises(ValueError,match='Conflicting'):replay(events+[bad])


def test_future_append_does_not_change_earlier_fills_or_reservations():
    early=[q(0),pick(),q(6)];a=replay(early);b=replay(early+[q(12,'10','10.02'),q(18,'10','10.02')])
    assert a['trace']==b['trace'][:len(a['trace'])]
    assert a['fills']==b['fills'][:len(a['fills'])]
    with localcontext() as c:
        c.prec=7
        assert replay(early)==a


@pytest.mark.parametrize('attack',['future-quote','future-receipt','future-evidence','negative','nan','reorder'])
def test_bad_inputs_fail_closed(attack):
    events=[q(0),pick(),q(6)]
    if attack=='future-quote':events[-1]['quote']['at']=at(7)
    if attack=='future-receipt':events[-1]['quote']['received_at']=at(7)
    if attack=='future-evidence':events[1]['candidate']['as_of']=at(7)
    if attack=='negative':events[-1]['quote']['bid_size']='-1'
    if attack=='nan':events[-1]['quote']['ask']='NaN'
    if attack=='reorder':events=[events[-1],*events[:-1]]
    with pytest.raises(ValueError):replay(events)


def test_cash_exhaustion_and_pending_orders_never_double_spend():
    r=replay([q(0),pick(),pick(2),pick(3),q(10)],replace(Assumptions(),initial_cash='5',latency_seconds=5))
    assert r['counters']['orders_created']==1
    assert all(0<=D(t['reserved_cash'])<=D(t['cash']) and D(t['available_cash'])>=0 for t in r['trace'])
    assert D(r['fills'][0]['value'])+D(r['fills'][0]['fee_quote'])<=5


def test_disconnect_and_unliquidated_position_remain_visible():
    events=[q(0),pick(),q(6),{'id':'off','type':'connection','observed_at':at(7),'connected':False},q(12,'50','50.02')]
    r=replay(events)
    assert len(r['fills'])==1 and D(r['quantity'])>0
    assert D(r['hypothetical_equity_change'])<0
    assert not r['orders'][-1]['side']=='sell'


def test_stress_matrix_preserves_invariants_and_costs_do_not_improve_identical_fills():
    suite=stress_suite();assert len(suite)==16
    by={r['scenario']:r for r in suite}
    assert D(by['fees-8x']['hypothetical_equity_change'])<D(by['fees-3x']['hypothetical_equity_change'])<D(by['base']['hypothetical_equity_change'])
    for r in suite:
        assert r['broker_orders_created']==0 and not r['automatic_promotion']
        assert all(D(t['cash'])>=D(t['reserved_cash'])>=0 and D(t['quantity'])>=0 for t in r['trace'])
    assert not by['zero-depth']['fills'] and not by['entry-halt']['fills'] and not by['research-expired']['fills']


def test_ttl_never_releases_reserve_before_modeled_ack():
    cfg=replace(Assumptions(),latency_seconds=120,cancel_latency_seconds=30,ttl_seconds=10)
    r=replay([q(0),pick(),clock(12),clock(20),clock(43)],cfg)
    assert D(r['trace'][2]['reserved_cash'])>0 and D(r['trace'][3]['reserved_cash'])>0
    assert r['reserved_cash']=='0' and r['orders'][0]['status']=='cancel-confirmed'


def test_export_uses_recorded_arrivals_and_keeps_gaps_without_writing_db(tmp_path):
    dbpath=tmp_path/'source.sqlite';db=sqlite3.connect(dbpath)
    db.executescript('CREATE TABLE events(seq INTEGER PRIMARY KEY,at TEXT,type TEXT,payload TEXT);CREATE TABLE experiment_observations(id TEXT,at TEXT,payload TEXT);')
    for seq,sec in [(1,0),(2,6),(3,70)]:
        quote=q(sec)['quote'];quote['source']='alpaca-us'
        db.execute('INSERT INTO events VALUES(?,?,?,?)',(seq,at(sec),'quotes',json.dumps({'BTC':quote})))
    db.commit();db.close();before=dbpath.read_bytes()
    events,coverage=export_events(dbpath,starts_at=at(1),ends_at=at(80),after_seq=1)
    assert len(events)==2 and events[0]['id']=='quote:2'
    assert coverage['max_quote_gap_seconds']==64 and len(coverage['quote_gaps'])==1
    assert dbpath.read_bytes()==before
    with pytest.raises(ValueError,match='regressed'):export_events(dbpath,starts_at=at(1),ends_at=at(80),after_seq=999)


def test_halt_or_lost_entry_permission_does_not_block_a_protective_exit():
    rows=[q(0),pick(),q(6),pick(7,eligible=False,entries_halted=True,signal='hold'),q(12,'90','90.02'),q(18,'90','90.02')]
    r=replay(rows)
    assert [f['side'] for f in r['fills']]==['buy','sell']
    assert r['quantity']=='0.000'


def test_exit_attempt_limit_preserves_unliquidated_quantity():
    rows=[q(0),pick(),q(6),q(12,'90','90.02'),q(18,'80','80.02'),q(24,'70','70.02'),q(30,'60','60.02'),q(36,'50','50.02')]
    r=replay(rows)
    assert len([o for o in r['orders'] if o['side']=='sell'])==3
    assert D(r['quantity'])>0 and r['counters']['exit_attempt_limit']>0


def test_candidate_updates_do_not_rewrite_held_position_exit_references():
    rows=[q(0),pick(),q(6),pick(7,signal='hold',stop='1',target='1000'),q(12,'97','97.02'),q(18,'97','97.02')]
    r=replay(rows)
    assert [f['side'] for f in r['fills']]==['buy','sell']
    assert any('stop' in d['reason'] for d in r['decisions'])


def test_compact_mode_preserves_ledger_totals_without_hiding_fill_count():
    events=synthetic_events();full=replay(events);compact=replay(events,retain_details=False)
    assert not compact['trace'] and not compact['decisions'] and not compact['details_complete']
    for key in ('cash','reserved_cash','quantity','hypothetical_equity_change','counters','event_sha256','fill_count'):
        assert full[key]==compact[key]


def test_holdout_contract_never_slides_and_changed_execution_code_is_visible(tmp_path,monkeypatch):
    from backend import replay_runner as runner
    path=tmp_path/'forward.json';ledger=tmp_path/'source.sqlite'
    db=sqlite3.connect(ledger);db.executescript('CREATE TABLE state(key TEXT,value TEXT);CREATE TABLE events(seq INTEGER PRIMARY KEY);')
    db.execute('INSERT INTO state VALUES(?,?)',('frozen_experiment',json.dumps({'manifest_sha256':'fixed'})))
    db.execute('INSERT INTO events VALUES(12)');db.commit();db.close()
    monkeypatch.setattr(runner,'contract',lambda:{'code_matches':True,'manifest_sha256':'fixed'})
    monkeypatch.setattr(runner,'code_hashes',lambda:{'replay':'v1'})
    first=runner.register_holdout(ledger,path)
    again=runner.register_holdout(ledger,path)
    assert first['starts_at']==again['starts_at'] and first['ends_at']==again['ends_at']
    assert (datetime.fromisoformat(first['ends_at'])-datetime.fromisoformat(first['starts_at'])).days==14
    assert first['baseline_event_seq']==12
    monkeypatch.setattr(runner,'code_hashes',lambda:{'replay':'v2'})
    assert not runner.register_holdout(ledger,path)['code_matches']
    raw=json.loads(path.read_text());raw['starts_at']=at(1);path.write_text(json.dumps(raw))
    with pytest.raises(ValueError,match='contract changed'):runner.register_holdout(ledger,path)


def test_nonboolean_gate_or_connection_cannot_be_treated_as_permission():
    with pytest.raises(ValueError,match='boolean'):replay([q(0),pick(eligible='false')])
    with pytest.raises(ValueError,match='boolean'):replay([{'id':'bad','type':'connection','observed_at':at(0),'connected':'false'}])


def test_nonfills_have_bounded_entry_attempts_per_evidence_packet():
    r=replay(synthetic_events(depth='0'))
    assert r['counters']['orders_created']==3 and r['counters']['entry_attempt_limit']>0
    assert not r['fills'] and r['pending_order'] is None and r['reserved_cash']=='0'


def test_invalid_exit_references_never_create_an_entry():
    r=replay([q(0),pick(stop='101',target='102'),q(6)])
    assert not r['fills'] and r['counters']['missing_exit_references']>0


def test_fractional_asset_fee_keeps_unsellable_dust_in_inventory():
    cfg=replace(Assumptions(),fee_mode='buy-base-sell-quote',fee_bps='25.123456')
    r=replay(synthetic_events(),cfg)
    assert 0<D(r['quantity'])<D(cfg.quantity_step)
    assert r['counters']['unsellable_dust']>0


def test_replay_report_is_visible_only_in_the_book_that_records_its_receipt(tmp_path,monkeypatch):
    from backend.config import Settings
    from backend.engine import Engine
    from backend.store import Store
    fake={'receipt':'fixed-report.json','scope':'hypothetical'}
    monkeypatch.setattr('backend.engine.replay_state',lambda:fake)
    cfg=Settings(db_path=tmp_path/'book.sqlite',api_key='fixture',secret_key='fixture')
    store=Store(cfg.db_path,'alpaca');engine=Engine(cfg,store)
    assert engine.replay_view() is None
    store.put('portfolio_replay_receipt','different-report.json');assert engine.replay_view() is None
    store.put('portfolio_replay_receipt','fixed-report.json');assert engine.replay_view()==fake
    engine.settings=replace(cfg,api_key='',secret_key='');assert engine.replay_view() is None
    import asyncio
    asyncio.run(engine.broker.close());store.close()
