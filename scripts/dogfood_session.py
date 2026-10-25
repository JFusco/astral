"""Bounded, GET-only Alpaca dogfood session using a private copied ledger."""
import argparse
import asyncio
from dataclasses import replace
import fcntl
import json
import os
from pathlib import Path
import sqlite3
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.config import Settings, ROOT
from backend.engine import Engine
from backend.broker import BrokerFailure
from backend.store import Store, utcnow


def lab_path(original, database):
    if Path(database).name != database or not database.endswith('.sqlite'):
        raise ValueError('Use a SQLite filename within the private runtime directory')
    path = (ROOT/'runtime'/database).resolve()
    source = original.db_path.resolve()
    if path == source or (path.exists() and source.exists() and os.path.samefile(path, source)):
        raise ValueError('Lab database must differ from the primary ledger')
    return path


def isolate_experiment_workers(engine):
    async def noop():
        pass
    engine.liquidity_cycle = noop
    engine.replay_cycle = noop


async def main(seconds, with_model, database='astral-dogfood.sqlite'):
    original = Settings.from_env()
    path = lab_path(original, database)
    lock_file = open(str(path)+'.lock','a')
    fcntl.flock(lock_file,fcntl.LOCK_EX|fcntl.LOCK_NB)
    if not path.exists() and original.db_path.exists():
        with sqlite3.connect('file:'+str(original.db_path)+'?mode=ro',uri=True) as source, sqlite3.connect(path) as target:
            source.backup(target)
        path.chmod(0o600)
    settings=replace(original,mode='alpaca',db_path=path,enable_orders=False,enable_exit_monitor=False,
                     enable_shadow=True,shadow_interval=10,enable_research=True,enable_codex_research=with_model,
                     enable_news=True)
    store=Store(path,'alpaca');engine=Engine(settings,store)
    isolate_experiment_workers(engine)
    before_orders=store.rows('SELECT COUNT(*) n FROM orders')[0]['n']
    cursor=store.rows('SELECT COALESCE(MAX(seq),0) n FROM events')[0]['n']
    before_shadow=store.rows('SELECT COUNT(*) n FROM shadow')[0]['n']
    started=utcnow();deadline=time.monotonic()+seconds
    try:
        await engine.start()
        try: await engine.refresh_news()
        except BrokerFailure: engine.worker('news','error','Entitlement or source unavailable; research vetoed')
        try: await engine.refresh_fees()
        except BrokerFailure: engine.worker('fees','error','Fee coverage unavailable; discrepancies remain flagged')
        await engine.shadow_cycle()
        print(json.dumps({'phase':'read-only-connected','connected':engine.connected,'orders_enabled':False}),flush=True)
        research=await engine.research_cycle()
        while time.monotonic()<deadline: await asyncio.sleep(1)
        await engine.reconcile()
        state=engine.state()
        requests=[json.loads(r['payload']) for r in store.rows("SELECT payload FROM events WHERE seq>? AND type='api_request'",(cursor,))]
        methods={m:sum(r['method']==m for r in requests) for m in sorted({r['method'] for r in requests})}
        new_orders=store.rows('SELECT COUNT(*) n FROM orders')[0]['n']-before_orders
        summary={'scope':'bounded authenticated Alpaca shadow; separate copied private ledger; no broker orders',
                 'started_at':started,'ended_at':utcnow(),'connected':state['connected'],'broker_methods':methods,
                 'broker_write_requests':sum(n for m,n in methods.items() if m!='GET'),'new_local_orders':new_orders,
                 'new_shadow_decisions':store.rows('SELECT COUNT(*) n FROM shadow')[0]['n']-before_shadow,
                 'shadow_counts':state['shadow']['counts'],'inventory_status':state['inventory']['status'],
                 'inventory_differences':state['inventory']['differences'],'fee_records':len(state['fee_activities']),
                 'news_records':len(state['news']),'research_symbols':len(research['packets']),
                 'eligible_symbols':[p['symbol'] for p in research['packets'] if p['eligible']],
                 'model_status':research['review']['status'],'model':research['review'].get('model'),
                 'reasoning_effort':research['review'].get('effort'),'model_usage':research['review'].get('usage'),
                 'model_actual_usd':None,'research_summary':(research['review'].get('review') or {}).get('summary'),
                 'timing_counts':store.rows("SELECT json_extract(result,'$.action') action,COUNT(*) count FROM timing GROUP BY action"),
                 'downstream_timing_counts':store.rows("SELECT json_extract(result,'$.before_inventory_gate.action') action,json_extract(result,'$.before_inventory_gate.reason') reason,COUNT(*) count FROM timing WHERE at>=? GROUP BY action,reason",(started,)),
                 'research_vetoes':{p['symbol']:p['vetoes'] for p in research['packets']},
                 'profitability_validated':False}
        assert not summary['broker_write_requests'] and not new_orders
        (ROOT/'runtime/dogfood-latest.json').write_text(json.dumps(summary,indent=2))
        print(json.dumps(summary,indent=2),flush=True)
    finally:
        await engine.stop();store.close();fcntl.flock(lock_file,fcntl.LOCK_UN);lock_file.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--seconds',type=int,default=90)
    parser.add_argument('--with-model',action='store_true');parser.add_argument('--database',default='astral-dogfood.sqlite');args=parser.parse_args()
    if not 30<=args.seconds<=300: parser.error('seconds must be between 30 and 300')
    asyncio.run(main(args.seconds,args.with_model,args.database))
