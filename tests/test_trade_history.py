import asyncio
from copy import deepcopy
from decimal import Decimal,localcontext
import httpx
import pytest

from backend.broker import AlpacaPaper,BrokerFailure
from backend.config import Settings
from backend.store import Store
from backend.trade_history import aggregate_daily


def batch():
    return [{'i':1,'p':'100','s':'2','t':'2026-10-23T01:00:00.000000001Z'},
            {'i':2,'p':'101','s':'3','t':'2026-10-23T01:00:00.000000002Z'},
            {'i':3,'p':'99','s':'1','t':'2026-10-24T02:00:00Z'},
            {'i':4,'p':'102','s':'4','t':'2026-10-25T01:00:00Z'}]


def aggregate(rows):
    return aggregate_daily(rows,start='2026-10-23T00:00:00Z',end='2026-10-25T02:00:00Z',known_at='2026-10-25T02:01:00Z')


def test_trade_only_bars_deduplicate_and_exclude_incomplete_day():
    data=batch();r=aggregate(data+data)
    assert len(r['rows'])==2 and r['trade_count']==4
    assert r['rows'][0]['o']=='100' and r['rows'][0]['c']=='101'
    assert r['rows'][0]['v']=='5' and r['rows'][0]['dollar_volume']=='503'
    assert r['bar_semantics']=='executed-trades-only'
    with localcontext() as c:
        c.prec=6
        assert aggregate(data)==r


@pytest.mark.parametrize('bad',['duplicate-id','negative-size','future','no-id'])
def test_bad_trade_records_fail_closed(bad):
    rows=batch()
    if bad=='duplicate-id':rows.append({**rows[0],'p':'999'})
    if bad=='negative-size':rows[0]['s']='-1'
    if bad=='future':rows[0]['t']='2027-01-01T00:00:00Z'
    if bad=='no-id':rows[0].pop('i')
    with pytest.raises(ValueError):aggregate(rows)


def test_missing_trade_day_is_not_filled_from_quotes():
    r=aggregate([batch()[0],batch()[-1]])
    assert len(r['rows'])==1
    assert r['rows'][0]['t'].startswith('2026-10-23')


def test_provider_pagination_must_finish_before_history_is_accepted(tmp_path):
    cfg=Settings(db_path=tmp_path/'db.sqlite',api_key='fixture',secret_key='fixture');s=Store(cfg.db_path,'alpaca')
    calls=[]
    def response(req):
        calls.append(req)
        return httpx.Response(200,json={'trades':{'BTC/USD':[]},'next_page_token':'stuck'})
    b=AlpacaPaper(cfg,s,httpx.MockTransport(response))
    async def check():
        with pytest.raises(BrokerFailure,match='did not advance'):await b.crypto_trade_history('BTC')
        await b.close()
    asyncio.run(check());assert len(calls)==2 and s.get('trade_history:BTC') is None
    s.close()


def test_history_shares_completed_days_and_reconstructs_each_immutable_batch(tmp_path):
    from datetime import datetime,timedelta,timezone
    import json
    cfg=Settings(db_path=tmp_path/'history.sqlite',api_key='fixture',secret_key='fixture')
    store=Store(cfg.db_path,'alpaca')
    boundary=datetime.now(timezone.utc).replace(hour=0,minute=0,second=0,microsecond=0)
    records=[{'i':i+1,'p':str(100+i),'s':'2','t':(boundary+timedelta(days=i-3,seconds=1)).strftime('%Y-%m-%dT%H:%M:%SZ')}
             for i in range(4)]
    # In the first two minutes after midnight, the fetch end is still yesterday.
    # Use a fixed synthetic clock so the partial-day fixture is always in range.
    class Clock(datetime):
        @classmethod
        def now(cls,tz=None):return (boundary+timedelta(hours=12)).astimezone(tz)
    from unittest.mock import patch
    calls=[]
    def handler(request):
        calls.append(request)
        return httpx.Response(200,json={'trades':{'BTC/USD':deepcopy(records)}})
    broker=AlpacaPaper(cfg,store,httpx.MockTransport(handler))
    store.db.execute('CREATE TABLE market_batches(id TEXT PRIMARY KEY,at TEXT NOT NULL,symbol TEXT NOT NULL,payload TEXT NOT NULL)')
    legacy=('BTC:legacy','old','BTC','[ {"retained": "byte for byte"} ]')
    store.db.execute('INSERT INTO market_batches VALUES(?,?,?,?)',legacy)
    histories=[]
    async def exercise():
        with patch('datetime.datetime',Clock),patch('backend.broker.utcnow',lambda:Clock.now(timezone.utc).isoformat()):
            histories.append(await broker.crypto_trade_history('BTC'))
            first_days=store.rows('SELECT * FROM market_trade_days')
            assert await broker.crypto_trade_history('BTC')==histories[0]
            assert len(calls)==1
            cached=store.get('trade_history:BTC')
            cached['received_at']=(Clock.now(timezone.utc)-timedelta(seconds=1501)).isoformat()
            store.put('trade_history:BTC',cached)
            records.append({'i':5,'p':'104','s':'3','t':(boundary+timedelta(hours=3)).strftime('%Y-%m-%dT%H:%M:%SZ')})
            histories.append(await broker.crypto_trade_history('BTC'))
            assert len(calls)==2 and histories[0]['input_sha256']!=histories[1]['input_sha256']
            assert len(store.rows('SELECT * FROM market_trade_days'))==len(first_days)+1
            for row in first_days:
                assert store.rows('SELECT * FROM market_trade_days WHERE id=?',(row['id'],))[0]==row
            saved_maps=store.rows('SELECT * FROM market_batch_maps')
            # A later fetch with identical records cannot overwrite its mapping.
            cached=store.get('trade_history:BTC');cached['received_at']=(Clock.now(timezone.utc)-timedelta(seconds=1501)).isoformat()
            store.put('trade_history:BTC',cached);await broker.crypto_trade_history('BTC')
            assert store.rows('SELECT * FROM market_batch_maps')==saved_maps
        for history in histories:
            mapping=json.loads(store.rows('SELECT payload FROM market_batch_maps WHERE id=?',
                                         ('BTC:'+history['input_sha256'],))[0]['payload'])
            restored=[]
            for key in mapping['day_keys']:
                restored.extend(json.loads(store.rows('SELECT payload FROM market_trade_days WHERE id=?',(key,))[0]['payload']))
            rebuilt=aggregate_daily(restored,start=mapping['start'],end=mapping['end'],known_at=mapping['received_at'])
            assert rebuilt==history
        assert tuple(store.rows('SELECT * FROM market_batches')[0].values())==legacy
        await broker.close()
    asyncio.run(exercise());store.close()
