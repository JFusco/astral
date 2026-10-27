"""Bounded overnight observation of the existing GET-only localhost paper lab."""
import argparse
import asyncio
from datetime import datetime, timezone, timedelta
import hashlib
import fcntl
import json
import os
from pathlib import Path
import sqlite3
import sys
import time

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.evidence_codec import unpack_text
DB = ROOT/'runtime/astral-dogfood.sqlite'
URL = 'http://127.0.0.1:8766/api/state'


def now():return datetime.now(timezone.utc).isoformat()


def safety(state):
    expected = [state.get('mode') == 'alpaca', state.get('paper_only') is True,
                state.get('orders_enabled') is False, state.get('shadow',{}).get('enabled') is True,
                state.get('research',{}).get('model_enabled') is False,
                state.get('risk_policy',{}).get('local_exit_monitor') is False]
    if not all(expected):raise ValueError('Observed service is outside the approved read-only paper experiment')


def audit(after):
    # Opening a missing database must never create an empty apparent success.
    with sqlite3.connect('file:'+str(DB)+'?mode=ro',uri=True) as connection:
        events=connection.execute('SELECT seq,type,payload FROM events WHERE seq>? ORDER BY seq',(after,)).fetchall()
        methods={};errors=0
        for _,kind,payload in events:
            item=json.loads(unpack_text(payload))
            if kind in {'api_request','api_request_failed'}:
                method=item.get('method','unknown');methods[method]=methods.get(method,0)+1
            if kind=='api_request' and item.get('status',200)>=400:errors+=1
            if kind in {'api_request_failed','worker_error'}:errors+=1
        return {'cursor':events[-1][0] if events else after,'methods':methods,'errors':errors,
                'new_order_events':sum(kind=='intent_committed' for _,kind,_ in events),
                'new_fill_events':sum(kind=='fill' for _,kind,_ in events)}


def write_summary(path,value):
    temporary=path.with_suffix('.tmp')
    with open(temporary,'w') as stream:json.dump(value,stream,indent=2)
    os.chmod(temporary,0o600);os.replace(temporary,path)


async def watch(hours,interval):
    directory=ROOT/'runtime';directory.mkdir(exist_ok=True)
    run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
    checkpoints=directory/('overnight-'+run_id+'.jsonl')
    summary_path=directory/'overnight-latest.json'
    started=now();deadline=time.monotonic()+hours*3600;cursor=None;previous='0'*64
    summary={'run_id':run_id,'status':'starting','started_at':started,
             'planned_end_at':(datetime.now(timezone.utc)+timedelta(hours=hours)).isoformat(),
             'scope':'Live market data and deterministic paper shadow only; no broker trades or model calls',
             'checkpoints':0,'unavailable_samples':0,'degraded_market_samples':0,'broker_methods':{},'api_or_worker_errors':0,
             'new_order_events':0,'new_fill_events':0,'profitability_validated':False,'checkpoints_path':str(checkpoints)}
    async with httpx.AsyncClient(timeout=15,follow_redirects=False,trust_env=False) as client:
        with open(checkpoints,'x') as log:
            os.chmod(checkpoints,0o600)
            try:
                while time.monotonic()<deadline:
                    record={'at':now()}
                    try:
                        response=await client.get(URL);response.raise_for_status();state=response.json();safety(state)
                        if cursor is None:
                            cursor=state['sequence'];summary['starting_sequence']=cursor
                        result=audit(cursor);cursor=result['cursor']
                        for method,count in result['methods'].items():summary['broker_methods'][method]=summary['broker_methods'].get(method,0)+count
                        summary['api_or_worker_errors']+=result['errors']
                        summary['new_order_events']+=result['new_order_events'];summary['new_fill_events']+=result['new_fill_events']
                        if any(m!='GET' and n for m,n in summary['broker_methods'].items()) or summary['new_order_events']:
                            raise ValueError('Broker write or new local order detected; experiment is not clean')
                        record.update(connected=state['connected'],sequence=state['sequence'],
                            inventory_status=state['inventory']['status'],inventory_differences=state['inventory']['differences'],
                            shadow_counts=state['shadow']['counts'],timing=state['timing'],
                            eligible_symbols=[p['symbol'] for p in state['research']['packets'] if p['eligible']],
                            quotes=[{'symbol':a['symbol'],'quote':a['quote'],'fresh':a['quote_fresh']} for a in state['assets']],
                            worker_errors=[w for w in state['workers'] if w['status']=='error'])
                        summary['latest_connected']=state['connected'];summary['latest_inventory_status']=state['inventory']['status']
                        summary['latest_shadow_counts']=state['shadow']['counts'];summary['latest_eligible_symbols']=record['eligible_symbols']
                        degraded=not state['connected'] or any(not a['quote_fresh'] for a in state['assets'] if a['type']=='crypto')
                        summary['degraded_market_samples']+=int(degraded)
                        summary['status']='degraded' if degraded else 'observing'
                    except httpx.HTTPError:
                        record.update(connected=False,error='Local service unavailable; no current market observation')
                        summary['unavailable_samples']+=1;summary['latest_connected']=False;summary['status']='degraded'
                    except (ValueError,KeyError,sqlite3.Error):
                        summary['status']='failed';summary['error']='Safety or ledger contract failed; no clean overnight result claimed'
                        record['error']=summary['error']
                    encoded=json.dumps({'previous_hash':previous,**record},sort_keys=True,separators=(',',':'))
                    previous=hashlib.sha256(encoded.encode()).hexdigest()
                    log.write(json.dumps({'hash':previous,'previous_hash':json.loads(encoded)['previous_hash'],**record})+'\n');log.flush();os.fsync(log.fileno())
                    summary['checkpoints']+=1;summary['last_checkpoint_at']=record['at'];summary['last_hash']=previous
                    write_summary(summary_path,summary)
                    if summary['checkpoints']==1:print(json.dumps({'status':summary['status'],'planned_end_at':summary['planned_end_at'],'report':str(summary_path)}),flush=True)
                    if summary['status']=='failed':return 1
                    await asyncio.sleep(min(interval,max(0,deadline-time.monotonic())))
                summary['status']='completed-with-gaps' if summary['unavailable_samples'] or summary['degraded_market_samples'] or summary['api_or_worker_errors'] else 'completed'
            except asyncio.CancelledError:
                summary['status']='interrupted';raise
            finally:
                summary['updated_at']=now();write_summary(summary_path,summary)
    print(json.dumps({'status':summary['status'],'checkpoints':summary['checkpoints'],'report':str(summary_path)}),flush=True)
    return 0


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--hours',type=float,default=8);parser.add_argument('--interval',type=int,default=60)
    args=parser.parse_args()
    if not 0<args.hours<=8 or not 10<=args.interval<=300:parser.error('Use up to 8 hours and a 10-300 second checkpoint interval')
    with open(ROOT/'runtime/overnight-watch.lock','a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        raise SystemExit(asyncio.run(watch(args.hours,args.interval)))
