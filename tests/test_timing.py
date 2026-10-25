from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from backend.timing import decide, replay


def event(seconds=0,bid='100',ask='100.01',**kw):
    at=(datetime(2026,10,25,12,tzinfo=timezone.utc)+timedelta(seconds=seconds)).isoformat()
    result=dict(as_of=at,kind='crypto',quote={'bid':bid,'ask':ask,'at':at},session_open=True,signal='entry_candidate',
                latest_closed_at='2026-10-25T11:59:59+00:00',research_qualified=True,
                research_expires_at='2026-10-25T12:05:00+00:00',stop_price='98',target_price='104')
    result.update(kw);return result


@pytest.mark.parametrize('case',['pending','unqualified','expired','future-bar','pre-close-quote','halted','closed','stale','no-bars','no-signal','cooldown'])
def test_entry_timing_fail_closed(case):
    e=event()
    if case=='pending':e['pending_order']=True
    if case=='unqualified':e['research_qualified']=False
    if case=='expired':e['research_expires_at']='2026-10-25T11:59:00Z'
    if case=='future-bar':e['latest_closed_at']='2026-10-25T12:01:00Z'
    if case=='pre-close-quote':e['quote']['at']=e['latest_closed_at']
    if case=='halted':e['entries_halted']=True
    if case=='closed':e.update(kind='etf',session_open=False)
    if case=='stale':e['quote']['at']='2026-10-25T11:59:00Z'
    if case=='no-bars':e['latest_closed_at']=None
    if case=='no-signal':e['signal']='hold'
    if case=='cooldown':e['last_exit_at']='2026-10-25T11:59:00Z'
    assert decide(**e,horizon='intraday')['action']=='wait'


@pytest.mark.parametrize('bid,signal,age,reason',[('97','hold',0,'stop'),('105','hold',0,'target'),('100','exit_review',0,'trend'),('100','hold',3600,'holding')])
def test_exit_rules_work_without_entry_permission(bid,signal,age,reason):
    e=event(age,bid=bid,ask=str(Decimal(bid)+Decimal('.01')),signal=signal,research_qualified=False)
    result=decide(**e,horizon='intraday',quantity='1',entry_at='2026-10-25T12:00:00Z',entries_halted=True)
    assert result['action']=='sell_candidate' and reason in result['reason']
    assert not result['fill_assumed']


def test_replay_never_fills_on_signal_quote_or_at_an_unavailable_stop_price():
    events=[event(),event(1),event(2,bid='90',ask='90.01'),event(3,bid='89',ask='89.01')]
    result=replay(events)
    assert [t['side'] for t in result['trades']]==['buy','sell']
    assert Decimal(result['trades'][1]['price'])==89
    assert all(t['at']>t['signal_at'] for t in result['trades'])
    assert not result['profitability_validated']


def test_replay_cost_and_slippage_stress_cannot_improve_same_round_trip():
    events=[event(),event(1),event(2,bid='105',ask='105.01'),event(3,bid='105',ask='105.01')]
    base=replay(events)
    stress=replay(events,fee_bps='75',extra_slippage_bps='50')
    assert Decimal(stress['cash_change'])<Decimal(base['cash_change'])


def test_entry_cancels_if_research_expires_during_latency():
    result=replay([event(),event(360)])
    assert result['trades'][0]['side']=='canceled-entry' and result['open_quantity']=='0'


def test_future_data_append_does_not_change_prior_decision():
    prefix=[event(),event(1)]
    earlier=replay(prefix)
    later=replay(prefix+[event(2,bid='50',ask='50.01'),event(3,bid='49',ask='49.01')])
    assert later['trades'][:len(earlier['trades'])]==earlier['trades']
    assert len(earlier['trades'])==1 and len(later['trades'])==2
