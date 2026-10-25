from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json

import httpx
import pytest

from backend.market_depth import validate_book
from backend.bea_calendar import parse_bea
from backend.fee_evidence import record_fee, validate_activity
from backend.broker import AlpacaPaper
from backend.config import Settings
from backend.store import Store, dumps, utcnow
from backend.readiness import view
from backend.readiness import calendar_coverage
from test_service import run, engine


NOW='2026-10-25T12:00:00Z'
def book():return {'t':NOW,'b':[{'p':'100','s':'2'},{'p':'99.99','s':'3'}],'a':[{'p':'100.02','s':'4'},{'p':'100.03','s':'5'}]}
def quote():return {'at':NOW,'bid':'100','ask':'100.02','bid_size':'2','ask_size':'4','source':'alpaca-us'}


def test_exact_same_venue_depth_contract_and_capacity():
    result=validate_book('BTC',book(),quote(),received_at=NOW)
    assert result['status']=='validated' and result['size_unit']=='base_asset'
    assert result['top_one_percent_cap_usd']=='2.00'
    assert result['buy_one_percent_capacity_usd']=='9.0023'
    assert not result['execution_enabled'] and not result['fill_guaranteed']


@pytest.mark.parametrize('attack',['stale','future','mismatch','size-mismatch','unsorted','duplicate','crossed','negative','nan','venue','distant'])
def test_book_normalization_fails_closed(attack):
    b=book();q=quote();received=NOW
    if attack=='stale':received='2026-10-25T12:00:20Z'
    if attack=='future':b['t']='2026-10-25T12:00:01Z'
    if attack=='mismatch':q['ask']='101'
    if attack=='size-mismatch':q['bid_size']='200'
    if attack=='unsorted':b['b'].reverse()
    if attack=='duplicate':b['b'].append(deepcopy(b['b'][0]))
    if attack=='crossed':b['a'][0]['p']='90'
    if attack=='negative':b['a'][0]['s']='-1'
    if attack=='nan':b['b'][0]['s']='NaN'
    if attack=='venue':q['source']='kraken'
    if attack=='distant':q['at']='2026-10-25T11:59:58Z'
    with pytest.raises(ValueError):validate_book('BTC',b,q,received_at=received)


def test_quote_adapter_preserves_prices_and_units_unknown_if_book_fails(tmp_path):
    cfg=Settings(db_path=tmp_path/'book.sqlite',api_key='fixture',secret_key='fixture')
    store=Store(cfg.db_path,'alpaca')
    now=utcnow();b={**book(),'t':now}
    def handler(request):
        if 'orderbooks' in request.url.path:return httpx.Response(403)
        if '/crypto/' in request.url.path:return httpx.Response(200,json={'quotes':{'BTC/USD':{'t':now,'bp':100,'ap':100.02,'bs':2,'as':4}}})
        return httpx.Response(200,json={'quotes':{}})
    broker=AlpacaPaper(cfg,store,httpx.MockTransport(handler));result=run(broker.quotes())
    assert result['BTC']['size_unit']=='unverified' and result['BTC']['at']==now
    assert result['BTC']['depth_status']=='book readback unavailable'
    run(broker.close());store.close()


def test_quote_adapter_retains_raw_book_and_versions_new_normalization(tmp_path):
    cfg=Settings(db_path=tmp_path/'book.sqlite',api_key='fixture',secret_key='fixture');store=Store(cfg.db_path,'alpaca')
    now=utcnow();b={**book(),'t':now}
    def handler(request):
        if 'orderbooks' in request.url.path:return httpx.Response(200,json={'orderbooks':{'BTC/USD':b}})
        if '/crypto/' in request.url.path:return httpx.Response(200,json={'quotes':{'BTC/USD':{'t':now,'bp':100,'ap':100.02,'bs':2,'as':4}}})
        return httpx.Response(200,json={'quotes':{}})
    broker=AlpacaPaper(cfg,store,httpx.MockTransport(handler))
    for _ in range(2):result=run(broker.quotes())
    assert result['BTC']['size_unit']=='base_asset' and result['BTC']['size_unit_version']=='alpaca-us-depth-v1'
    assert store.rows('SELECT COUNT(*) n FROM depth_snapshots')[0]['n']==1
    run(broker.close());store.close()


def fee(**kwargs):return {'id':'f1','activity_type':'CFEE','symbol':'BTCUSD','status':'executed','qty':'-.000001',**kwargs}


@pytest.mark.parametrize('change',[{'qty':'NaN'},{'qty':'1'},{'qty':'0'},{'symbol':'UNKNOWN'},{'qty':None}])
def test_missing_or_invalid_asset_fee_never_adjusts_inventory(change):
    with pytest.raises(ValueError):validate_activity(fee(**change))


def test_fee_revisions_retained_without_overwriting_confirmed_debit(engine):
    s=engine.store;original=fee();record_fee(s,original)
    s.db.execute('INSERT INTO activities VALUES(?,?,?,?)',('f1','CFEE',utcnow(),dumps(original)))
    changed=fee(qty='-.000002')
    with pytest.raises(ValueError,match='Confirmed fee changed'):record_fee(s,changed)
    assert len(s.rows('SELECT * FROM activity_revisions'))==2
    assert json.loads(s.rows('SELECT payload FROM activities')[0]['payload'])==original
    assert s.get('fee_reconciliation_required') and engine.inventory()['status']=='needs-review'


def test_late_fee_window_still_includes_original_fill_after_three_days(engine):
    s=engine.store
    # Only the query window is tested; this observation cannot create a fill/order.
    s.db.execute('INSERT INTO fills VALUES(?,?,?,?)',('old','unused','2020-01-01',dumps({'at':'2020-01-01T12:00:00Z'})))
    queries=[]
    async def fetch(after):queries.append(after);return []
    engine.broker.fee_activities=fetch
    run(engine.refresh_fees())
    assert datetime.fromisoformat(queries[0])<datetime(2020,1,1,tzinfo=timezone.utc)
    assert not s.rows('SELECT * FROM activities')


def bea_html():return b'''<table id="release-schedule-table"><thead><tr><th>Year 2026</th><th></th><th>Release</th></tr></thead><tbody><tr><td><div>October 29</div><small>8:30 AM</small></td><td>News</td><td>GDP and PCE</td></tr><tr><td><div>November 4</div><small>8:30 AM</small></td><td>News</td><td>Trade</td></tr></tbody></table>'''


def test_bea_dates_preserve_clock_text_without_inventing_release_timezone():
    rows=parse_bea(bea_html());assert len(rows)==2
    assert rows[0]['event_start']=='2026-10-29T00:00:00-04:00'
    assert rows[1]['event_start']=='2026-11-04T00:00:00-05:00'
    assert '8:30 AM' in rows[0]['source_clock_text']
    assert rows[0]['created_at'] is None and 'unspecified' in rows[0]['precision']
    with pytest.raises(ValueError):parse_bea(bea_html().replace(b'8:30 AM',b'TBD',1))
    with pytest.raises(ValueError):parse_bea(b'<html>Access denied</html>')


def test_gate_view_does_not_turn_partial_calendar_or_low_volume_into_permission(engine):
    result=view(engine.store)
    assert result['policy_changed'] is False and not result['execution_enabled']
    assert all(not r['events']['passed'] and not r['liquidity']['passed'] for r in result['symbols'])
    assert all(not r['paper_trade_authorized'] for r in result['symbols'])


def test_calendar_flags_and_hash_strings_alone_cannot_certify_coverage():
    import hashlib
    now=datetime(2026,10,25,12,tzinfo=timezone.utc)
    calendar={'symbol':'BTC','categories':{}};proofs={}
    for category in ('fomc','bea','bls','scheduled-protocol','venue-maintenance'):
        proof={'symbol':'BTC','category':category,'source_url':'https://fixture.test/calendar',
               'checked_at':now.isoformat(),'coverage_from':now.isoformat(),'coverage_until':(now+timedelta(days=2)).isoformat()}
        sha=hashlib.sha256(dumps(proof).encode()).hexdigest();proofs[sha]=proof
        calendar['categories'][category]={'status':'verified','checked_at':now.isoformat(),
             'coverage_from':now.isoformat(),'coverage_until':(now+timedelta(days=2)).isoformat(),
             'source_url':proof['source_url'],'retained_evidence_sha256':sha}
    assert not calendar_coverage(calendar,'BTC',now)['passed']
    assert calendar_coverage(calendar,'BTC',now,proofs)['passed']
    calendar['categories']['bls']['coverage_until']=(now+timedelta(minutes=1)).isoformat()
    assert calendar_coverage(calendar,'BTC',now,proofs)['missing_categories']==['bls']


def test_adequate_daily_volume_cannot_override_a_subminimum_depth_cap(engine):
    s=engine.store;now=utcnow();quotes=s.get('quotes');quotes['BTC'].update(ask='100',at=now,size_unit='base_asset',
        depth={'at':now,'status':'validated','top_one_percent_cap_usd':'.50'})
    s.put('quotes',quotes);assets=s.get('assets');assets['BTC'].update(minimum='.01',tradable=True);s.put('assets',assets)
    s.put('trade_history:BTC',{'rows':[{'dollar_volume':'2000000'}]*21,'bar_semantics':'executed-trades-only',
                             'complete_page_traversal':True,'received_at':now})
    row=view(s)['symbols'][0]
    assert not row['liquidity']['passed'] and not row['liquidity']['top_cap_fits_venue_minimum']
    quotes['BTC']['depth']['top_one_percent_cap_usd']='2';s.put('quotes',quotes)
    assert view(s)['symbols'][0]['liquidity']['passed']
    assert not view(s)['symbols'][0]['paper_trade_authorized']


def test_official_category_proofs_never_promote_missing_categories(engine):
    from backend.calendar_evidence import retain_scopes
    now=datetime(2026,10,25,12,tzinfo=timezone.utc)
    catalog={'source_id':'bea-calendar','source_url':'https://www.bea.gov/news/schedule',
             'checked_at':now.isoformat(),'retained_body_sha256':'a'*64,
             'events':[{'event_start':'2026-10-29T00:00:00-04:00','event_end_exclusive':'2026-10-30T00:00:00-04:00',
                        'headline':'fixture only','precision':'date only'}]}
    retain_scopes(engine.store,{'calendar_catalogs':[catalog]},now.isoformat())
    # This is a synthetic source-catalog fixture, not a connected BEA readback.
    saved=engine.store.get('event_calendars')['BTC']
    assert saved['status']=='partial' and list(saved['categories'])==['bea']
    proofs={r['sha256']:json.loads(r['payload']) for r in engine.store.rows('SELECT * FROM event_calendar_evidence')}
    result=calendar_coverage(saved,'BTC',now,proofs)
    assert not result['passed'] and 'bea' not in result['missing_categories'] and 'bls' in result['missing_categories']
    catalog['source_url']='https://untrusted.test/calendar'
    retain_scopes(engine.store,{'calendar_catalogs':[catalog]},now.isoformat())
    assert len(engine.store.rows('SELECT * FROM event_calendar_evidence'))==3
