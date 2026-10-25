import asyncio,json,sqlite3,sys
from dataclasses import replace
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.config import Settings,ROOT
from backend.broker import AlpacaPaper
from backend.store import Store,utcnow
async def main():
 cfg=replace(Settings.from_env(),enable_orders=False,enable_shadow=False,enable_exit_monitor=False,enable_research=False,enable_codex_research=False,db_path=ROOT/'runtime/gate-investigation.sqlite')
 s=Store(cfg.db_path,'alpaca');b=AlpacaPaper(cfg,s)
 src=sqlite3.connect((ROOT/'runtime/astral-stage2.sqlite').resolve().as_uri()+'?mode=ro',uri=True)
 ids=[r[0] for r in src.execute('SELECT client_id FROM orders WHERE external=0')];src.close()
 out={'at':utcnow(),'orders':[],'activity_queries':{},'books':[]}
 try:
  for cid in ids:out['orders'].append(await b.get_order(cid))
  for key,path in [('all','/v2/account/activities'),('CFEE','/v2/account/activities/CFEE'),('FEE','/v2/account/activities/FEE')]:
   try:out['activity_queries'][key]=await b.request('GET',path,params={'after':'2026-10-24','direction':'asc','page_size':100},critical=True)
   except Exception as exc:out['activity_queries'][key]={'error':str(exc)}
  for _ in range(3):
   raw=await b.request('GET','/v1beta3/crypto/us/latest/orderbooks',data=True,params={'symbols':'BTC/USD,ETH/USD,SOL/USD'})
   quotes=await b.quotes();out['books'].append({'received_at':utcnow(),'raw':raw,'quotes':quotes})
  snap=await b.snapshot();out['positions']=snap['positions'];out['equity']=snap['account'].get('equity');out['crypto_status']=snap['account'].get('crypto_status')
  target=ROOT/'runtime/gate-investigation-readback.json';target.write_text(json.dumps(out,indent=2)+'\n');target.chmod(0o600)
  print(json.dumps({'orders':len(out['orders']),'activity_counts':{k:len(v) if isinstance(v,list) else v for k,v in out['activity_queries'].items()},'positions':len(out['positions']),'books':[{k:{'at':v.get('t'),'bids':len(v.get('b',[])),'asks':len(v.get('a',[])),'top_bid':v.get('b',[None])[0],'top_ask':v.get('a',[None])[0]} for k,v in (batch['raw'] or {}).get('orderbooks',{}).items()} for batch in out['books']]}))
 finally:await b.close();s.close()
asyncio.run(main())
