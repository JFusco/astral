"""Explicit, bounded PAPER-only CLI. No web API can enable this pilot."""
import argparse
import asyncio
from dataclasses import replace
import fcntl
import json
import os
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.config import ROOT,Settings
from backend.engine import Engine
from backend.pilot import ExecutionPilot
from backend.store import Store


async def main(run_id,execute):
    if not execute:raise ValueError('An explicitly authorized execution test requires --execute')
    db=ROOT/'runtime/astral-stage2.sqlite'
    if not db.exists():raise ValueError('Existing bound paper ledger required; no fresh account baseline is created')
    with open(str(db)+'.lock','a') as lock,open(ROOT/'runtime/paper-execution-pilot.lock','a') as account_lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(account_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        cfg=replace(Settings.from_env(),mode='alpaca',db_path=db,enable_orders=True,enable_shadow=False,enable_research=False,
                    enable_codex_research=False,enable_exit_monitor=False,enable_news=False)
        store=Store(db,'alpaca');e=Engine(cfg,store)
        if not store.get('account_binding'):raise ValueError('Existing paper-account identity binding required')
        pilot=ExecutionPilot(e,run_id)
        try:
            result=await pilot.run()
            print(json.dumps({k:result.get(k) for k in ('run_id','scope','phase','outcome','entry_permits','exit_permits','equity_change_usd','fees_reconciled')},indent=2),flush=True)
        finally:
            p=ROOT/'runtime/execution-pilot-final.json';fd=os.open(p,os.O_CREAT|os.O_TRUNC|os.O_WRONLY,0o600)
            with os.fdopen(fd,'w') as f:json.dump(store.get('execution_pilot'),f,indent=2)
            await e.stop();store.close()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-id',required=True);p.add_argument('--execute',action='store_true');args=p.parse_args()
    asyncio.run(main(args.run_id,args.execute))
