"""One bounded GET-only research cycle on the existing paper ledger. No model."""
import asyncio
from dataclasses import replace
import fcntl
import json
from pathlib import Path
import sqlite3
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.config import Settings,ROOT
from backend.engine import Engine
from backend.store import Store,utcnow
from backend import experiment


async def main():
    cfg=replace(Settings.from_env(),enable_orders=False,enable_exit_monitor=False,
                enable_shadow=False,enable_research=True,enable_codex_research=False)
    if cfg.mode!='alpaca':raise SystemExit('This command requires the existing Alpaca PAPER ledger')
    frozen=experiment.contract()
    if not frozen or not frozen['code_matches']:raise SystemExit('A frozen matching strategy is required')
    with open(str(cfg.db_path)+'.lock','a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        stamp=utcnow().replace(':','').replace('.','')
        backup=ROOT/'runtime'/('before-research-'+stamp+'.sqlite')
        source=sqlite3.connect(cfg.db_path.resolve().as_uri()+'?mode=ro',uri=True)
        destination=sqlite3.connect(backup);source.backup(destination);destination.close();source.close();backup.chmod(0o600)
        store=Store(cfg.db_path,cfg.mode);engine=Engine(cfg,store)
        before={t:store.rows('SELECT COUNT(*) n FROM '+t)[0]['n'] for t in ('orders','fills')}
        async def forbidden(*args,**kwargs):raise RuntimeError('Research command attempted a broker write')
        engine.broker.submit=forbidden;engine.broker.cancel=forbidden
        try:
            experiment.register(store)
            await engine.refresh_quotes();await engine.reconcile()
            await engine.refresh_news();await engine.refresh_fees()
            result=await engine.research_cycle()
            after={t:store.rows('SELECT COUNT(*) n FROM '+t)[0]['n'] for t in ('orders','fills')}
            receipt={'at':utcnow(),'experiment':experiment.state(store),'orders_enabled':False,'model_enabled':False,
                     'counts_before':before,'counts_after':after,'new_orders':after['orders']-before['orders'],
                     'new_fills':after['fills']-before['fills'],'broker_position_count':len(store.get('account_snapshot')['positions']),
                     'fee_activity_records':store.rows('SELECT COUNT(*) n FROM activities')[0]['n'],
                     'fee_coverage':store.get('fee_coverage'),'inventory':engine.inventory(),
                     'packets':[{'symbol':p['symbol'],'eligible':p['eligible'],'facts':p['facts'],'vetoes':p['vetoes'],
                                 'input_hash':p['input_hash'],'context_records':sum(e['id'].startswith('public:') for e in p['evidence'])} for p in result['packets']]}
            out=ROOT/'runtime'/('research-cycle-'+stamp+'.json');out.write_text(json.dumps(receipt,indent=2)+'\n');out.chmod(0o600)
            (ROOT/'runtime/frozen-research-latest.json').write_text(json.dumps(receipt,indent=2)+'\n')
            print(json.dumps({'receipt':str(out),'observations':receipt['experiment']['observations'],'new_orders':receipt['new_orders'],
                              'new_fills':receipt['new_fills'],'fee_records':receipt['fee_activity_records'],'inventory_status':receipt['inventory']['status'],
                              'packets':receipt['packets']}))
        finally:
            await engine.stop();store.close()


if __name__=='__main__':asyncio.run(main())
