"""Isolated deterministic portfolio execution model. No broker or Store imports.

Every fill here is hypothetical, including fills driven by recorded quotes.
Quote depth is a participation ceiling, not proof of executable liquidity/queue.
"""
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import timedelta
from decimal import Decimal, ROUND_UP, localcontext
import hashlib
import json

from .risk import number as D, timestamp, floor_step
from .timing import decide

VERSION = 'portfolio-replay-v1'


@dataclass(frozen=True)
class Assumptions:
    initial_cash: str = '100000'
    cap_usd: str = '25'
    quantity_step: str = '0.000000001'
    minimum_quantity: str = '0.000000001'
    price_tick: str = '0.01'
    fee_bps: str = '25'
    fee_mode: str = 'quote'
    spread_multiple: str = '1'
    slippage_bps: str = '0'
    depth_fraction: str = '0.01'
    latency_seconds: int = 5
    cancel_latency_seconds: int = 5
    ttl_seconds: int = 60
    tif: str = 'ioc'
    max_entry_orders_per_packet: int = 3
    max_exit_orders: int = 3
    gap_seconds: int = 30

    def validate(self):
        if D(self.initial_cash)<=0 or not 0<D(self.cap_usd)<=25:raise ValueError('Invalid replay cash/cap')
        if not 0<=D(self.fee_bps)<=200 or not 0<=D(self.slippage_bps)<=100:raise ValueError('Invalid cost assumptions')
        if not 1<=D(self.spread_multiple)<=10 or not 0<D(self.depth_fraction)<=1:raise ValueError('Invalid spread/depth assumption')
        if min(D(self.quantity_step),D(self.minimum_quantity),D(self.price_tick))<=0:raise ValueError('Invalid venue precision')
        if self.fee_mode not in {'quote','buy-base-sell-quote'} or self.tif not in {'ioc','gtc'}:raise ValueError('Unsupported execution assumption')
        if not 0<=self.latency_seconds<=120 or not 0<=self.cancel_latency_seconds<=120:raise ValueError('Invalid latency')
        if any(type(getattr(self,k)) is not int for k in ('latency_seconds','cancel_latency_seconds','ttl_seconds','max_entry_orders_per_packet','max_exit_orders','gap_seconds')):raise ValueError('Time and attempt bounds must be integers')
        if not 1<=self.max_entry_orders_per_packet<=10:raise ValueError('Invalid entry attempt bound')
        if not 1<=self.ttl_seconds<=300 or not 1<=self.max_exit_orders<=10 or self.gap_seconds<1:raise ValueError('Invalid replay bound')


def replay(events, assumptions=Assumptions(), *, retain_details=True):
    assumptions.validate()
    with localcontext() as context:
        context.prec=40
        return Portfolio(assumptions,retain_details=retain_details).run(events)


class Portfolio:
    def __init__(self, cfg, *, retain_details=True):
        self.retain_details=retain_details
        self.cfg=cfg;self.cash=D(cfg.initial_cash);self.quantity=D(0);self.pending=None
        self.candidate=None;self.references={};self.entry_at=None;self.last_exit=None
        self.connected=True;self.quote=None;self.previous_at=None;self.last_source_at=None
        self.used_quotes=set();self.seen={};self.fills=[];self.orders=[];self.decisions=[];self.trace=[]
        self.counters=Counter();self.fees_quote=D(0);self.fees_base=D(0)
        self.highwater=self.cash;self.max_drawdown=D(0);self.exit_orders=0;self.entry_attempts=Counter()
        self.fee=D(cfg.fee_bps)/10000;self.slip=D(cfg.slippage_bps)/10000

    def reserved(self):
        if not self.pending or self.pending['side']!='buy':return D(0)
        factor=1+self.fee if self.cfg.fee_mode=='quote' else D(1)
        return self.pending['remaining']*self.pending['limit']*factor

    def fresh(self, now):
        return self.quote is not None and 0<=(now-self.quote['time']).total_seconds()<=15

    def end_order(self, status, at):
        o=self.pending
        if not o:return
        self.orders.append({'id':o['id'],'side':o['side'],'decision_at':o['at'].isoformat(),
                            'terminal_at':at.isoformat(),'status':status,'requested_quantity':str(o['requested']),
                            'filled_quantity':str(o['requested']-o['remaining']), 'limit_price':str(o['limit']),
                            'execution':'HYPOTHETICAL', 'tif':self.cfg.tif})
        self.counters[status]+=1;self.pending=None

    def cancel(self, reason, now):
        if self.pending and not self.pending.get('cancel_due'):
            self.pending['cancel_due']=now+timedelta(seconds=self.cfg.cancel_latency_seconds)
            self.pending['cancel_reason']=reason;self.counters['cancel_requested']+=1

    def eligibility(self, now):
        c=self.candidate
        return bool(c and c.get('eligible') and c.get('code_matches') and c.get('inventory_gate_passed')
                    and not c.get('entries_halted') and not c.get('broker_pending_order')
                    and timestamp(c['as_of'])<=now<=timestamp(c['expires_at']))

    def timing(self, now, pending=False):
        c=self.candidate or {}
        q={'bid':str(self.quote['bid']),'ask':str(self.quote['ask']),'at':self.quote['time'].isoformat()} if self.quote else {}
        return decide(as_of=now.isoformat(),horizon='swing',kind='crypto',quote=q,session_open=True,
                      signal=c.get('signal','hold'),latest_closed_at=c.get('latest_closed_at'),
                      research_qualified=self.eligibility(now),research_expires_at=c.get('expires_at'),
                      quantity=str(self.quantity),entry_at=self.entry_at,stop_price=self.references.get('stop'),
                      target_price=self.references.get('target'),pending_order=pending,
                      last_exit_at=self.last_exit,entries_halted=c.get('entries_halted',False))

    def submit(self, side, now, decision):
        c=self.candidate or {};step=D(self.cfg.quantity_step);tick=D(self.cfg.price_tick)
        if side=='buy':
            key=c.get('packet_sha256') or c['as_of']
            if self.entry_attempts[key]>=self.cfg.max_entry_orders_per_packet:
                self.counters['entry_attempt_limit']+=1;return
            # A depth-unit claim is an execution gate, even if a caller marks a pick eligible.
            if self.quote.get('size_unit')!='base_asset':self.counters['unverified_depth_entry']+=1;return
            limit=floor_step(self.quote['ask']*D('1.001'),tick)
            factor=1+self.fee if self.cfg.fee_mode=='quote' else D(1)
            qty=floor_step(min(D(c.get('quantity','0')),D(c.get('notional','0'))/limit,
                               D(self.cfg.cap_usd)/limit,(self.cash-self.reserved())/(limit*factor)),step)
            if qty<D(self.cfg.minimum_quantity):self.counters['insufficient_cash_or_size']+=1;return
            if not 0<D(c.get('stop','0'))<limit<D(c.get('target','0')):
                self.counters['missing_exit_references']+=1;return
            self.references={'stop':c['stop'],'target':c['target']};self.exit_orders=0
            self.entry_attempts[key]+=1
        else:
            if self.exit_orders>=self.cfg.max_exit_orders:self.counters['exit_attempt_limit']+=1;return
            limit=(self.quote['bid']*D('0.999')/tick).to_integral_value(rounding=ROUND_UP)*tick
            qty=floor_step(self.quantity,step)
            if qty<D(self.cfg.minimum_quantity):self.counters['unsellable_dust']+=1;return
            self.exit_orders+=1
        self.pending={'id':'hypothetical-'+str(self.counters['orders_created']+1),'side':side,
                      'at':now,'eligible_at':now+timedelta(seconds=self.cfg.latency_seconds),
                      'deadline':now+timedelta(seconds=self.cfg.ttl_seconds),'limit':limit,
                      'requested':qty,'remaining':qty,'reason':decision['reason']}
        self.counters['orders_created']+=1

    def attempt_fill(self, now, is_new_quote):
        o=self.pending
        if not o or not is_new_quote or not self.connected or not self.fresh(now):return
        if now<o['eligible_at'] or self.quote['time']<=o['at']:return
        key=self.quote['time'].isoformat()
        if key in self.used_quotes:return
        self.used_quotes.add(key)
        if self.quote.get('size_unit')!='base_asset':
            self.counters['unverified_depth_nonfill']+=1;return
        side=o['side'];price=self.quote['ask']*(1+self.slip) if side=='buy' else self.quote['bid']*(1-self.slip)
        depth=self.quote['ask_size'] if side=='buy' else self.quote['bid_size']
        if (side=='buy' and price>o['limit']) or (side=='sell' and price<o['limit']):
            self.counters['outside_price_collar']+=1
            if self.cfg.tif=='ioc':self.end_order('ioc-nonfill',now)
            return
        capacity=floor_step(depth*D(self.cfg.depth_fraction),D(self.cfg.quantity_step))
        qty=min(o['remaining'],capacity)
        if side=='sell':qty=min(qty,floor_step(self.quantity,D(self.cfg.quantity_step)))
        if qty<D(self.cfg.minimum_quantity):
            self.counters['insufficient_observed_depth']+=1
            if self.cfg.tif=='ioc':self.end_order('ioc-nonfill',now)
            return
        value=qty*price;fee_quote=D(0);fee_base=D(0)
        if side=='buy':
            if self.cfg.fee_mode=='quote':fee_quote=value*self.fee
            else:fee_base=qty*self.fee
            self.cash-=value+fee_quote;self.quantity+=qty-fee_base
            if not self.entry_at:self.entry_at=now.isoformat()
        else:
            fee_quote=value*self.fee;self.cash+=value-fee_quote;self.quantity-=qty
            if self.quantity==0:self.last_exit=now.isoformat();self.entry_at=None;self.references={}
        self.fees_quote+=fee_quote;self.fees_base+=fee_base;o['remaining']-=qty
        self.fills.append({'order_id':o['id'],'side':side,'at':now.isoformat(),'quote_at':key,
                           'decision_at':o['at'].isoformat(),'quantity':str(qty),'price':str(price),
                           'value':str(value),'fee_quote':str(fee_quote),'fee_base':str(fee_base),
                           'execution':'HYPOTHETICAL','observed_depth_capacity':str(capacity),
                           'cancel_pending':bool(o.get('cancel_due'))})
        self.counters['hypothetical_'+side+'_fills']+=1
        if o['remaining']==0:self.end_order('filled',now)
        elif self.cfg.tif=='ioc':self.end_order('ioc-partial',now)

    def run(self, events):
        for event in events:
            identity=event['id'];canonical=json.dumps(event,sort_keys=True,separators=(',',':'))
            if identity in self.seen:
                if self.seen[identity]!=canonical:raise ValueError('Conflicting replay event ID')
                self.counters['duplicate_events']+=1;continue
            self.seen[identity]=canonical;now=timestamp(event['observed_at'])
            if self.previous_at and now<self.previous_at:raise ValueError('Replay events must be chronological by arrival')
            if self.previous_at and (now-self.previous_at).total_seconds()>self.cfg.gap_seconds:
                self.counters['observation_gaps']+=1
            self.previous_at=now;self.counters['events']+=1;new_quote=False
            if event['type']=='quote':
                q=event['quote'];at=timestamp(q['at']);bid,ask=D(q['bid']),D(q['ask'])
                if bid<=0 or ask<bid or at>now:raise ValueError('Invalid or future quote')
                if q.get('received_at') and timestamp(q['received_at'])>now:raise ValueError('Quote not yet received')
                if self.last_source_at and at<=self.last_source_at:
                    self.counters['duplicate_or_out_of_order_quotes']+=1
                else:
                    self.last_source_at=at;mid=(bid+ask)/2;half=(ask-bid)*D(self.cfg.spread_multiple)/2
                    if mid-half<=0:raise ValueError('Stress spread invalid')
                    sizes=[D(q.get(k,'0')) for k in ('bid_size','ask_size')]
                    if min(sizes)<0:raise ValueError('Negative quote size')
                    self.quote={'time':at,'bid':mid-half,'ask':mid+half,'bid_size':sizes[0],
                                'ask_size':sizes[1],'size_unit':q.get('size_unit','unverified')};new_quote=True
                    if not self.fresh(now):self.counters['stale_quotes']+=1
            elif event['type']=='candidate':
                c=event['candidate']
                if timestamp(c['as_of'])>now or timestamp(c['expires_at'])<timestamp(c['as_of']):raise ValueError('Invalid evidence arrival')
                for key in ('quantity','notional'):
                    if D(c.get(key,'0'))<0:raise ValueError('Negative proposal')
                for flag in ('eligible','code_matches','inventory_gate_passed','entries_halted','broker_pending_order'):
                    if type(c.get(flag)) is not bool:raise ValueError('Evidence gate must be a boolean')
                self.candidate=c;self.counters['candidate_events']+=1
            elif event['type']=='connection':
                if type(event['connected']) is not bool:raise ValueError('Connection state must be boolean')
                self.connected=event['connected']
            elif event['type']!='clock':raise ValueError('Unsupported replay event')
            if self.pending and self.connected:
                if self.pending.get('cancel_due') and now>=self.pending['cancel_due']:
                    self.end_order('cancel-confirmed',now)
                elif now>=self.pending['deadline']:
                    self.cancel('time-to-live',now)
                elif self.pending['side']=='buy' and not self.eligibility(now):
                    self.cancel('evidence-invalidated',now)
                elif self.pending['side']=='buy' and self.quantity>0 and self.fresh(now):
                    check=self.timing(now)
                    if check['action']=='sell_candidate':self.cancel('protective-exit',now)
            self.attempt_fill(now,new_quote)
            if self.connected and self.fresh(now):
                decision=self.timing(now,pending=self.pending is not None)
                if self.retain_details:self.decisions.append({'at':now.isoformat(),'action':decision['action'],'reason':decision['reason']})
                if self.pending is None and decision['action'] in {'buy_candidate','sell_candidate'}:
                    self.submit('buy' if decision['action']=='buy_candidate' else 'sell',now,decision)
            marked=self.cash+(self.quantity*self.quote['bid'] if self.quote else D(0))
            if self.quote and self.fresh(now):
                self.highwater=max(self.highwater,marked)
                self.max_drawdown=max(self.max_drawdown,(self.highwater-marked)/self.highwater)
            reserve=self.reserved()
            if self.cash<0 or self.quantity<0 or reserve<0 or reserve>self.cash:raise AssertionError('Portfolio conservation violated')
            if self.retain_details:self.trace.append({'at':now.isoformat(),'event_id':identity,'cash':str(self.cash),'reserved_cash':str(reserve),
                               'available_cash':str(self.cash-reserve),'quantity':str(self.quantity),'marked_equity':str(marked),
                               'mark_fresh':self.fresh(now),'pending_side':self.pending['side'] if self.pending else None})
        mark=self.quote['bid'] if self.quote else D(0)
        return {'version':VERSION,'scope':'Hypothetical portfolio replay; never broker PAPER executions',
                'assumptions':asdict(self.cfg),'event_sha256':hashlib.sha256(json.dumps(events,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
                'initial_cash':self.cfg.initial_cash,'cash':str(self.cash),'reserved_cash':str(self.reserved()),
                'quantity':str(self.quantity),'last_bid':str(mark),'last_mark_fresh':self.fresh(self.previous_at) if self.previous_at else False,
                'marked_equity':str(self.cash+self.quantity*mark),'hypothetical_equity_change':str(self.cash+self.quantity*mark-D(self.cfg.initial_cash)),
                'hypothetical_fee_quote':str(self.fees_quote),'hypothetical_fee_base':str(self.fees_base),
                'maximum_observed_drawdown_fraction':str(self.max_drawdown),'pending_order':self.pending['side'] if self.pending else None,
                'counters':dict(self.counters),'fill_count':len(self.fills),'order_count':len(self.orders),
                'details_complete':self.retain_details,'fills':self.fills if self.retain_details else self.fills[-30:],'orders':self.orders if self.retain_details else self.orders[-30:],'decisions':self.decisions,'trace':self.trace,
                'broker_orders_created':0,'profitability_validated':False,'automatic_promotion':False,
                'limitations':['Quote-depth participation and cancel acknowledgments are explicit hypothetical assumptions',
                    'Displayed depth can disappear; repeated snapshots are not proof of replenishment or queue priority',
                    'No fills inferred during missing observations/disconnects; hidden venue fills are not modeled',
                    'Fees are scenario assumptions, not the unresolved broker accounting contract',
                    'Stale/missing final marks and unliquidated inventory remain visible; no forced final close']}
