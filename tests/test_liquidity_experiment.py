from copy import deepcopy
from datetime import datetime,timedelta,timezone
import json
import sqlite3

import pytest

from backend.liquidity import evaluate
from backend.market_depth import validate_book
from backend import liquidity_runner as runner
from backend.experiment import contract
from backend.store import Store,dumps

NOW=datetime(2026,10,25,12,tzinfo=timezone.utc)


def inputs(now=NOW):
    at=now.isoformat();end=now.replace(hour=0,minute=0,second=0,microsecond=0)
    raw={'t':at,'b':[{'p':'100','s':'.8'},{'p':'99.99','s':'1000'}],
         'a':[{'p':'100.02','s':'.8'},{'p':'100.03','s':'1000'}]}
    quote={'at':at,'source':'alpaca-us','bid':'100','ask':'100.02','bid_size':'.8','ask_size':'.8','size_unit':'base_asset'}
    quote['depth']=validate_book('BTC',raw,quote,received_at=at)
    history={'source':'alpaca-us-executed-trades','bar_semantics':'executed-trades-only','complete_page_traversal':True,
             'received_at':at,'input_sha256':'a'*64,
             'rows':[{'t':(end-timedelta(days=21-i)).isoformat(),'dollar_volume':'205874.6'} for i in range(21)]}
    return {'quote':quote,'raw_book':raw,'history':history,'asset':{'at':at,'tradable':True,'increment':'.000001','minimum':'.01','price_increment':'.01'}}


def test_baseline_rejects_while_separate_half_depth_model_can_cover_25():
    result=evaluate(inputs(),as_of=NOW.isoformat())
    assert result['status']=='evaluated' and not result['baseline']['liquidity_passed']
    assert result['baseline']['top_one_percent_cap_usd']=='0.800'
    cases={r['name']:r for r in result['scenarios']}
    assert cases['base_half_depth']['feasible_quote_model']
    assert not cases['ninety_nine_percent_depth_loss']['feasible_quote_model']
    assert not cases['double_fees']['feasible_quote_model']
    assert not cases['two_percent_exit_gap']['feasible_quote_model']
    assert not cases['no_exit_depth']['feasible_quote_model']
    assert not result['execution_enabled'] and not result['fill_assumed'] and not result['profitability_validated']


@pytest.mark.parametrize('attack',['stale-book','book-mismatch','history-gap','future-history','wrong-venue','stale-metadata','bad-unit','unverified-history','nan-volume'])
def test_corrupt_stale_and_unverified_evidence_does_not_become_liquidity_pass(attack):
    x=inputs()
    if attack=='stale-book':x['raw_book']['t']=(NOW-timedelta(seconds=16)).isoformat()
    if attack=='book-mismatch':x['raw_book']['a'][0]['s']='1'
    if attack=='history-gap':x['history']['rows'].pop(1)
    if attack=='future-history':x['history']['received_at']=(NOW+timedelta(seconds=1)).isoformat()
    if attack=='wrong-venue':x['quote']['source']='external'
    if attack=='stale-metadata':x['asset']['at']=(NOW-timedelta(hours=2)).isoformat()
    if attack=='bad-unit':x['quote']['size_unit']='unverified'
    if attack=='unverified-history':x['history']['bar_semantics']='quotes'
    if attack=='nan-volume':x['history']['rows'][0]['dollar_volume']='NaN'
    result=evaluate(x,as_of=NOW.isoformat())
    assert result['status']=='invalid-evidence' and not result['execution_enabled']


def test_daily_turnover_cap_and_fee_reduced_exit_minimum_are_binding():
    x=inputs()
    for r in x['history']['rows']:r['dollar_volume']='5000'
    result=evaluate(x,as_of=NOW.isoformat())
    assert result['target_notional_usd']=='1.0000'
    assert all(not r['feasible_quote_model'] for r in result['scenarios'])
    x=inputs();x['asset']['minimum']='.2497'
    result=evaluate(x,as_of=NOW.isoformat())
    assert any('fee-reduced exit' in r for r in result['scenarios'][0]['reasons'])


def seed(path,when):
    s=Store(path,'alpaca');s.put('account_binding','fixture-only-paper-id')
    s.put('frozen_experiment',{'id':'btc-daily-swing-v1','manifest_sha256':contract()['manifest_sha256'],'registered_at':when.isoformat()})
    s.db.execute('CREATE TABLE depth_snapshots(id TEXT PRIMARY KEY,at TEXT,symbol TEXT,payload TEXT)')
    append(s,when)
    return s


def append(s,when):
    x=inputs(when);sha=x['quote']['depth']['raw_sha256']
    s.db.execute('INSERT OR IGNORE INTO depth_snapshots VALUES(?,?,?,?)',(sha,when.isoformat(),'BTC',dumps(x['raw_book'])))
    s.put('trade_history:BTC',x['history']);s.put('assets',{'BTC':x['asset']})
    s.event('quotes',{'BTC':x['quote']})


def test_registration_excludes_old_data_keeps_main_ledger_readonly_and_output_deduplicated(tmp_path,monkeypatch):
    path=tmp_path/'main.sqlite';manifest=tmp_path/'experiment.json';output=tmp_path/'separate.sqlite'
    s=seed(path,datetime.now(timezone.utc)-timedelta(minutes=1));reg=runner.register(path,manifest)
    moment=datetime.fromisoformat(reg['starts_at'])+timedelta(seconds=1)
    monkeypatch.setattr(runner,'now',lambda:moment.isoformat())
    first=runner.observe(path,manifest,output)
    assert first['invalid_samples']==1 and 'Pre-registration' in first['latest']['reasons'][0]
    append(s,moment)
    before={t:s.rows('SELECT COUNT(*) n FROM '+t)[0]['n'] for t in ('orders','fills','events')}
    result=runner.observe(path,manifest,output);runner.observe(path,manifest,output)
    assert result['samples']==2 and runner.state(path,manifest,output)['samples']==2
    assert result['challenger_base_feasible']==1 and result['baseline_liquidity_passes']==0
    assert {t:s.rows('SELECT COUNT(*) n FROM '+t)[0]['n'] for t in before}==before
    with runner.readonly(path) as ro:
        with pytest.raises(sqlite3.OperationalError):ro.execute("DELETE FROM events")
    moment+=timedelta(seconds=61)
    assert runner.state(path,manifest,output)['status']=='stale'
    append(s,moment);result=runner.observe(path,manifest,output)
    assert result['sample_gaps_over_45s']==1
    moment=datetime.fromisoformat(reg['ends_at'])+timedelta(seconds=1)
    assert runner.observe(path,manifest,output)['status']=='window-ended'
    assert runner.state(path,manifest,output)['samples']==3
    s.close()


def test_manifest_tampering_and_code_drift_block_sampling(tmp_path,monkeypatch):
    path=tmp_path/'main.sqlite';manifest=tmp_path/'manifest.json';out=tmp_path/'out.sqlite'
    s=seed(path,datetime.now(timezone.utc));runner.register(path,manifest)
    monkeypatch.setattr(runner,'hashes',lambda:{'changed':'code'})
    with pytest.raises(ValueError,match='code drift'):runner.observe(path,manifest,out)
    value=json.loads(manifest.read_text());value['policy']['notional_cap']='100'
    manifest.write_text(json.dumps(value))
    with pytest.raises(ValueError,match='contract changed'):runner.load(manifest)
    assert not out.exists();s.close()
