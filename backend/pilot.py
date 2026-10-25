"""One explicitly authorized execution experiment; never an alpha strategy.

Uses the normal durable order engine. Historical accounting discrepancies remain
visible; broker custody and a flat account bound this mechanical paper test.
"""
import asyncio
from datetime import datetime, timezone, timedelta
import re

from .broker import BrokerFailure, D, TERMINAL
from .engine import RuleViolation, age
from .store import utcnow


class ExecutionPilot:
    def __init__(self, engine, run_id, *, hold_seconds=20):
        if not re.fullmatch(r"[a-zA-Z0-9-]{8,20}", run_id) or not 0 <= hold_seconds <= 60:
            raise ValueError("Invalid bounded pilot configuration")
        if not engine.settings.enable_orders or engine.settings.enable_shadow or engine.settings.enable_research or engine.settings.enable_codex_research or engine.settings.enable_exit_monitor:
            raise ValueError("Pilot requires sole order authority; strategies, research and exit workers disabled")
        self.e, self.store, self.run_id, self.hold_seconds = engine, engine.store, run_id, hold_seconds
        prior = self.store.get("execution_pilot")
        if prior and prior["run_id"] != run_id:
            raise RuleViolation("A pilot already consumed this experiment; no new run ID may buy again")
        self.state = prior or {"run_id":run_id, "scope":"execution-test-only; no research or profitability claim", "phase":"created",
                               "started_at":utcnow(), "entry_deadline":(datetime.now(timezone.utc)+timedelta(seconds=120)).isoformat(),
                               "entry_permits":0, "exit_permits":0, "cancel_permits":[], "max_entry_usd":"25",
                               "max_exit_attempts":3, "holding_seconds":hold_seconds, "orders":[], "model_calls":0}
        self.submit_original, self.cancel_original = self.e.broker.submit, self.e.broker.cancel
        self.e.broker.submit, self.e.broker.cancel = self.submit, self.cancel
        self.save()

    def save(self):
        self.store.put("execution_pilot",self.state)

    def cid(self, side, attempt=0):
        return f"astral-pilot-{self.run_id}-{side}"+(str(attempt) if side=='sell' else '')

    def active_orders(self, exclude=None):
        return [o for o in self.store.rows("SELECT * FROM orders") if o['status'] not in TERMINAL and o['client_id'] != exclude]

    async def submit(self, payload):
        # Independent final boundary immediately before the broker request.
        if payload.get('symbol') != 'BTC/USD' or payload.get('type') != 'limit' or payload.get('time_in_force') != 'ioc':
            raise BrokerFailure('Pilot permits BTC/USD IOC limit orders only',403)
        cid = payload['client_order_id'];qty, price = D(payload['qty']),D(payload['limit_price'])
        if qty <= 0 or price <= 0 or self.active_orders(cid): raise BrokerFailure('Pilot quantity or outstanding-order gate failed',403)
        snap = await self.e.broker.snapshot()
        if await self.e.broker.open_orders():
            raise BrokerFailure('Broker has an outstanding order; pilot write blocked',403)
        if self.store.get('account_binding') != snap['account']['id']:
            raise BrokerFailure('Pilot account identity changed',403)
        if any(p['symbol'].replace('/','') != 'BTCUSD' for p in snap['positions']):
            raise BrokerFailure('Pilot requires no other positions',403)
        held = sum((D(p['qty']) for p in snap['positions']),D(0))
        quote = self.store.get('quotes',{}).get('BTC',{})
        if not 0 <= age(quote.get('at')) <= 15: raise BrokerFailure('Pilot quote unavailable',403)
        bid,ask=D(quote['bid']),D(quote['ask'])
        if ask < bid or bid <= 0: raise BrokerFailure('Pilot quote invalid',403)
        if payload['side']=='buy':
            if cid != self.cid('buy') or self.state['entry_permits'] or held != 0 or qty*price > D('25') or age(self.state['entry_deadline']) > 0:
                raise BrokerFailure('Pilot entry budget, expiry or single-entry gate failed',403)
            if (ask-bid)/((ask+bid)/2) > D('.002') or not ask <= price <= ask*D('1.001'):
                raise BrokerFailure('Pilot entry spread or price bound failed',403)
            self.state['entry_permits']=1
        elif payload['side']=='sell':
            entry=self.store.order(self.cid('buy'))
            if not entry or entry['status'] not in TERMINAL:
                raise BrokerFailure('Entry outcome must be terminal before pilot exit',403)
            import json
            gross=D(json.loads(entry['raw']).get('filled_qty') or 0)
            expected=self.cid('sell',self.state['exit_permits'])
            if cid != expected or self.state['exit_permits'] >= 3 or not 0 < qty <= held <= gross or not bid*D('.999') <= price <= bid:
                raise BrokerFailure('Pilot exit ownership, budget or price gate failed',403)
            self.state['exit_permits']+=1
        else:
            raise BrokerFailure('Invalid pilot side',403)
        # Consume authority BEFORE sending, including when the response is lost.
        self.state['orders'].append(cid);self.state['phase']='entry-requested' if payload['side']=='buy' else 'exit-requested'
        with self.store.transaction():
            self.save();self.store.event('pilot_write_permit',{'run_id':self.run_id,'client_id':cid,'side':payload['side'],'notional_bound':str(qty*price)})
        return await self.submit_original(payload)

    async def cancel(self, broker_id):
        import json
        rows=[o for o in self.store.rows('SELECT * FROM orders') if o['client_id'] in self.state['orders'] and json.loads(o['raw']).get('id')==broker_id]
        if len(rows)!=1 or broker_id in self.state['cancel_permits']:
            raise BrokerFailure('Pilot cancel is not authorized or was already attempted',403)
        self.state['cancel_permits'].append(broker_id);self.save()
        return await self.cancel_original(broker_id)

    async def terminal(self,cid):
        for _ in range(20):
            try:
                await self.e.reconcile()
            except BrokerFailure:
                self.e.connected=False
                await asyncio.sleep(1)
                continue
            row=self.store.order(cid)
            if row and row['status'] in TERMINAL:return self.e.order_view(row)
            await asyncio.sleep(1)
        # Never place a second order or infer a cancel on an unknown outcome.
        row=self.store.order(cid)
        if row and row['status']!='unknown' and self.e.order_view(row)['broker'].get('id'):
            await self.e.cancel(cid)
            for _ in range(5):
                await self.e.reconcile();row=self.store.order(cid)
                if row['status'] in TERMINAL:return self.e.order_view(row)
                await asyncio.sleep(1)
        raise RuleViolation('Pilot order outcome remains uncertain; manual reconciliation required')

    async def run(self):
        import json
        if self.state['phase']=='completed':return self.state
        try:
            await self.e.refresh_quotes();await self.e.reconcile()
            if 'before' not in self.state:
                self.state['before']={'equity':self.e.store.get('account_snapshot')['account']['equity'],'inventory':self.e.inventory()};self.save()
            entry=self.store.order(self.cid('buy'))
            if not entry:
                if self.state['entry_permits']:raise RuleViolation('Entry authority consumed without a recoverable order record')
                # Stable flat custody and fresh quote checks precede the entry.
                for i in range(3):
                    await self.e.refresh_quotes();await self.e.reconcile()
                    snap=self.store.get('account_snapshot');q=self.store.get('quotes')['BTC']
                    if snap['positions'] or self.active_orders() or not self.e.connected or not 0<=age(q['at'])<=15:
                        raise RuleViolation('Pilot requires stable flat account, no working orders and fresh quotes')
                    if i<2:await asyncio.sleep(1)
                self.state['phase']='entry-preflight-passed';self.save()
                await self.e.place({'client_order_id':self.cid('buy'),'symbol':'BTC','side':'buy','notional':25.0,'execution':'bounded','ttl_seconds':20,'strategy_id':'lifecycle_test'})
            entry=await self.terminal(self.cid('buy'))
            self.state['entry']=entry['broker'];self.save()
            if D(entry['broker'].get('filled_qty') or 0)==0:
                self.state.update(phase='completed',outcome='entry-not-filled',ended_at=utcnow());self.save();return self.state
            filled_at=entry['broker'].get('filled_at') or entry['broker'].get('submitted_at')
            while age(filled_at)<self.state['holding_seconds']:
                await self.e.refresh_quotes()
                bid=D(self.store.get('quotes')['BTC']['bid']);basis=D(entry['broker']['filled_avg_price'])
                if bid<=basis*D('.995') or bid>=basis*D('1.005'):break
                await asyncio.sleep(min(3,max(.01,self.state['holding_seconds']-age(filled_at))))
            # Resume any prior exit before considering a bounded residual exit.
            for cid in self.state['orders']:
                if '-sell' in cid:await self.terminal(cid)
            for _ in range(3):
                await self.e.refresh_quotes();await self.e.reconcile()
                snap=self.store.get('account_snapshot')
                held=sum((D(p['qty']) for p in snap['positions'] if p['symbol'].replace('/','')=='BTCUSD'),D(0))
                if held==0:
                    self.state.update(phase='completed',outcome='round-trip-flat-confirmed',ended_at=utcnow(),
                                      after={'equity':snap['account']['equity'],'inventory':self.e.inventory()},
                                      equity_change_usd=str(D(snap['account']['equity'])-D(self.state['before']['equity'])),fees_reconciled=False)
                    self.save();return self.state
                if self.state['exit_permits']>=3:raise RuleViolation('Pilot residual exit-attempt budget exhausted')
                cid=self.cid('sell',self.state['exit_permits'])
                notional=min(D('1000'),max(D('26'),held*D(self.store.get('quotes')['BTC']['ask'])*D('1.01')))
                await self.e.place({'client_order_id':cid,'symbol':'BTC','side':'sell','notional':float(notional),'execution':'bounded','ttl_seconds':20,'strategy_id':'lifecycle_test'})
                await self.terminal(cid)
            raise RuleViolation('Residual position requires operator review')
        except (BrokerFailure,RuleViolation,ValueError,KeyError):
            self.state.update(phase='attention',outcome='Readback or pilot guard failed; no blind retry',updated_at=utcnow());self.save()
            raise
