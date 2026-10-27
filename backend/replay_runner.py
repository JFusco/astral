"""Read-only ledger export, fixed future window and offline stress receipts.

No .env, broker, Engine, credential, model or network imports. Results are written
only to separate replay files, never to the trading ledger or fill table.
"""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import json
from pathlib import Path
import sqlite3

from .config import ROOT
from .experiment import contract, digest
from .portfolio_replay import Assumptions, replay
from .risk import timestamp, number as D
from .evidence_codec import unpack_text

HOLDOUT=ROOT/'experiments/btc-forward-holdout-v1.json'
CODE=('backend/portfolio_replay.py','backend/replay_runner.py','backend/risk.py','backend/timing.py','backend/research.py','backend/experiment.py','backend/evidence_codec.py')


def code_hashes():
    return {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in CODE}


def connect_readonly(path):
    db=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True)
    db.row_factory=sqlite3.Row;db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
    return db


def register_holdout(db_path, path=HOLDOUT):
    frozen=contract()
    if not frozen or not frozen['code_matches']:raise ValueError('Matching frozen BTC strategy required')
    if path.exists():
        value=json.loads(path.read_text());saved=value.pop('sha256')
        if digest(value)!=saved:raise ValueError('Forward evaluation contract changed')
        if value['strategy_manifest_sha256']!=frozen['manifest_sha256']:raise ValueError('Forward strategy identity changed')
        return {**value,'sha256':saved,'code_matches':value['source_sha256']==code_hashes()}
    db=connect_readonly(db_path)
    try:
        bound=db.execute("SELECT value FROM state WHERE key='frozen_experiment'").fetchone()
        if not bound or json.loads(bound[0])['manifest_sha256']!=frozen['manifest_sha256']:
            raise ValueError('Ledger has no matching frozen registration')
        seq=db.execute('SELECT COALESCE(MAX(seq),0) FROM events').fetchone()[0]
    finally:db.close()
    now=datetime.now(timezone.utc)
    value={'id':'btc-forward-holdout-v1','strategy_manifest_sha256':frozen['manifest_sha256'],
           'source_sha256':code_hashes(),'starts_at':now.isoformat(),'ends_at':(now+timedelta(days=14)).isoformat(),
           'baseline_event_seq':seq,'symbol':'BTC','horizon':'daily swing','model_arm':'deterministic no-model baseline',
           'source':'Existing Alpaca US quote arrivals and registered prospective research packets',
           'policy':'Fixed future evaluation window; never move cutoff, tune strategy or replace missing observations',
           'execution_model':Assumptions().__dict__,
           'criteria':{'automatic_promotion':False,'profitability_pass':False,'minimum_observation_days':14,
                       'max_quote_gap_seconds':30,'coverage':'Retain all gaps, rejects, expired evidence and unliquidated inventory',
                       'review':'Require adequate qualified-trade, cost and regime coverage; no trade count or return automatically proves an edge'},
           'exclusions':['Previously inspected history is development data only','Actual crypto depth units remain unverified',
                         'Queue priority, hidden fills during outages and impact require additional validation']}
    value['sha256']=digest(value);path.parent.mkdir(exist_ok=True)
    with path.open('x') as f:json.dump(value,f,indent=2);f.write('\n')
    return {**value,'code_matches':True}


def export_events(db_path, *, starts_at, ends_at, after_seq=0, expected_manifest=None):
    start,end=timestamp(starts_at),timestamp(ends_at)
    if end<start:raise ValueError('Invalid replay window')
    db=connect_readonly(db_path);events=[];issues=[];quote_times=[];packets=0
    try:
        maxseq=db.execute('SELECT COALESCE(MAX(seq),0) FROM events').fetchone()[0]
        if maxseq<after_seq:raise ValueError('Ledger sequence regressed; retain the evaluation gap')
        for row in db.execute("SELECT seq,at,payload FROM events WHERE type='quotes' AND seq>? AND at>=? AND at<=? ORDER BY seq",(after_seq,starts_at,ends_at)):
            try:
                known=timestamp(row['at']);q=json.loads(unpack_text(row['payload'])).get('BTC')
                if q is None:continue
                if not start<=known<=end:continue
                if q.get('source')!='alpaca-us':raise ValueError('Wrong quote venue')
                source_at=timestamp(q['at'])
                if source_at>known or (q.get('received_at') and timestamp(q['received_at'])>known):raise ValueError('Quote not observable at arrival')
                if source_at<start:issues.append({'event_seq':row['seq'],'reason':'Quote source predates window boundary'});continue
                events.append({'id':'quote:'+str(row['seq']),'type':'quote','observed_at':row['at'],'quote':q})
                quote_times.append(known)
            except (ValueError,KeyError,TypeError) as exc:issues.append({'event_seq':row['seq'],'reason':str(exc)[:120]})
        for row in db.execute('SELECT id,at,payload FROM experiment_observations WHERE at>=? AND at<=? ORDER BY at',(starts_at,ends_at)):
            d=json.loads(row['payload']);known=timestamp(row['at'])
            if not start<=known<=end:continue
            p=d['packet'];ctx=d['context'];facts=p['facts']
            if p['symbol']!='BTC' or p.get('facts',{}).get('experiment_manifest')!=d.get('manifest_sha256') or (expected_manifest and d.get('manifest_sha256')!=expected_manifest):
                issues.append({'observation_id':row['id'],'reason':'Experiment identity mismatch'});continue
            if timestamp(p['as_of'])>known:
                issues.append({'observation_id':row['id'],'reason':'Future research decision'});continue
            candidate={'as_of':p['as_of'],'expires_at':p['expires_at'],'eligible':p['eligible'],
                       'code_matches':d['code_matches'],'inventory_gate_passed':d['timing'].get('inventory_gate_passed',False),
                       'entries_halted':ctx.get('entries_halted',True),'broker_pending_order':ctx.get('pending_order',True),
                       'signal':facts.get('signal','hold'),'latest_closed_at':facts.get('latest_closed_daily_bar'),
                       'quantity':facts.get('proposed_quantity','0'),'notional':facts.get('proposed_notional','0'),
                       'stop':facts.get('planned_stop'),'target':facts.get('target'),'vetoes':p['vetoes'],
                       'packet_sha256':p['input_hash'],'manifest_sha256':d['manifest_sha256']}
            events.append({'id':'candidate:'+row['id'],'type':'candidate','observed_at':row['at'],'candidate':candidate});packets+=1
    finally:db.close()
    if len(events)>300000:raise ValueError('Replay event budget exceeded; no incomplete success report')
    events.sort(key=lambda e:(timestamp(e['observed_at']),e['id']))
    points=[start]+quote_times+[end]
    gaps=[{'from':a.isoformat(),'until':b.isoformat(),'seconds':(b-a).total_seconds()} for a,b in zip(points,points[1:]) if (b-a).total_seconds()>30]
    return events,{'quotes':len(quote_times),'research_packets':packets,'issues':issues,'quote_gaps':gaps,
                   'max_quote_gap_seconds':max(((b-a).total_seconds() for a,b in zip(points,points[1:])),default=0),
                   'starts_at':starts_at,'ends_at':ends_at,'snapshot_max_event_seq':maxseq}


def synthetic_events(*, depth='100', outage=False, gap=False, expired=False, halted=False):
    origin=datetime(2026,10,25,12,tzinfo=timezone.utc)
    def at(s):return (origin+timedelta(seconds=s)).isoformat()
    data=[]
    for s in range(0,186,5):
        if gap and 15<=s<=120:continue
        bid='90' if gap and s>120 else '105' if s>=45 else '100'
        data.append({'id':'fixture-quote:'+str(s),'type':'quote','observed_at':at(s),
                     'quote':{'at':at(s),'bid':bid,'ask':str(D(bid)+D('.02')),'bid_size':depth,'ask_size':depth,
                              'size_unit':'base_asset','source':'synthetic-fixture'}})
    data.append({'id':'fixture-pick','type':'candidate','observed_at':at(1),
                 'candidate':{'as_of':at(1),'expires_at':at(3 if expired else 300),'eligible':True,'code_matches':True,
                              'inventory_gate_passed':True,'entries_halted':halted,'broker_pending_order':False,
                              'signal':'entry_candidate','latest_closed_at':at(-1),'quantity':'0.249','notional':'25','stop':'98','target':'104'}})
    if outage:
        data.extend([{'id':'offline','type':'connection','observed_at':at(10),'connected':False},
                     {'id':'online','type':'connection','observed_at':at(130),'connected':True}])
    return sorted(data,key=lambda e:(timestamp(e['observed_at']),e['id']))


def stress_suite():
    base=Assumptions()
    cases=[('base',base,{}),('fees-3x',replace(base,fee_bps='75'),{}),
           ('fees-8x',replace(base,fee_bps='200'),{}),('spread-2x',replace(base,spread_multiple='2'),{}),
           ('spread-3x',replace(base,spread_multiple='3'),{}),('slippage-10bps',replace(base,slippage_bps='10'),{}),
           ('latency-30s',replace(base,latency_seconds=30),{}),('latency-120s',replace(base,latency_seconds=120),{}),
           ('partial-ioc',base,{'depth':'0.02'}),('zero-depth',base,{'depth':'0'}),
           ('buy-fee-in-base',replace(base,fee_mode='buy-base-sell-quote'),{}),
           ('disconnect',base,{'outage':True}),('price-gap',base,{'gap':True}),
           ('research-expired',base,{'expired':True}),('entry-halt',base,{'halted':True}),
           ('gtc-partials-cancel',replace(base,tif='gtc',cancel_latency_seconds=30),{'depth':'0.02'})]
    results=[]
    for name,cfg,kw in cases:
        result=replay(synthetic_events(**kw),cfg)
        result['scenario']=name;result['data_scope']='synthetic mechanics fixture; not market performance'
        results.append(result)
    return results


def summary(result):
    return {k:result[k] for k in ('scope','counters','fill_count','order_count','cash','reserved_cash','quantity','pending_order','hypothetical_equity_change','last_mark_fresh','event_sha256','profitability_validated')}


def build_report(db_path, *, register=False, directory=None):
    directory=Path(directory or ROOT/'runtime');directory.mkdir(exist_ok=True)
    with (directory/'portfolio-replay.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        frozen=contract()
        if not frozen or not frozen['code_matches']:raise ValueError('Frozen strategy code drift')
        if not HOLDOUT.exists() and not register:raise ValueError('Future evaluation window is not registered')
        forward=register_holdout(db_path)
        if not forward['code_matches']:raise ValueError('Forward evaluation replay code changed; preserve the registered version')
        now=datetime.now(timezone.utc);end=min(now,timestamp(forward['ends_at']))
        db=connect_readonly(db_path)
        try:prior=json.loads(db.execute("SELECT value FROM state WHERE key='frozen_experiment'").fetchone()[0])
        finally:db.close()
        observed_events,observed_coverage=export_events(db_path,starts_at=prior['registered_at'],ends_at=end.isoformat(),expected_manifest=frozen['manifest_sha256'])
        forward_events,forward_coverage=export_events(db_path,starts_at=forward['starts_at'],ends_at=end.isoformat(),after_seq=forward['baseline_event_seq'],expected_manifest=frozen['manifest_sha256'])
        observed=replay(observed_events,retain_details=False);holdout=replay(forward_events,retain_details=False);scenarios=stress_suite()
        matured=now>=timestamp(forward['ends_at'])
        report={'version':'replay-report-v1','at':now.isoformat(),'strategy_manifest_sha256':frozen['manifest_sha256'],
                'source_sha256':code_hashes(),'observed':observed,'observed_coverage':observed_coverage,
                'forward':{'contract':forward,'matured':matured,'status':'awaiting-review' if matured else 'collecting',
                           'coverage':forward_coverage,'replay':holdout,'profitability_validated':False},
                'scenarios':scenarios,'broker_orders_created':0,'model_calls':0,'automatic_promotion':False}
        stamp=now.strftime('%Y%m%dT%H%M%S%fZ');receipt=directory/('portfolio-replay-'+stamp+'.json')
        with receipt.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
        receipt.chmod(0o600)
        brief={'version':report['version'],'at':report['at'],'code_matches':forward['code_matches'],
               'scope':'Offline execution model; all fills hypothetical','strategy_manifest_sha256':frozen['manifest_sha256'],
               'observed':summary(observed),'observed_coverage':observed_coverage,
               'forward':{'id':forward['id'],'starts_at':forward['starts_at'],'ends_at':forward['ends_at'],
                          'status':report['forward']['status'],'matured':matured,'coverage':forward_coverage,'replay':summary(holdout)},
               'synthetic_scenarios':len(scenarios),'synthetic_scenarios_with_fills':sum(bool(r['fills']) for r in scenarios),
               'broker_orders_created':0,'model_calls':0,'profitability_validated':False,'automatic_promotion':False,
               'limitations':observed['limitations'],'receipt':receipt.name}
        temp=directory/'portfolio-replay-latest.tmp';temp.write_text(json.dumps(brief,indent=2)+'\n');temp.chmod(0o600)
        temp.replace(directory/'portfolio-replay-latest.json')
        return brief


def report_state():
    try:
        value=json.loads((ROOT/'runtime/portfolio-replay-latest.json').read_text())
        # A historical report cannot claim current replay-code compatibility.
        value['code_matches']=json.loads(HOLDOUT.read_text())['source_sha256']==code_hashes()
        return value
    except (OSError,ValueError,KeyError):return None
