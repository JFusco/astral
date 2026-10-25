from copy import deepcopy
import importlib.util
from pathlib import Path

import pytest
import json
import sqlite3

spec=importlib.util.spec_from_file_location('overnight_watch',Path(__file__).resolve().parents[1]/'scripts/overnight_watch.py')
watch=importlib.util.module_from_spec(spec);spec.loader.exec_module(watch)


@pytest.mark.parametrize('field',['orders','model','exit','mode','shadow','paper'])
def test_overnight_observer_rejects_permission_expansion(field):
    state={'mode':'alpaca','paper_only':True,'orders_enabled':False,'shadow':{'enabled':True},
           'research':{'model_enabled':False},'risk_policy':{'local_exit_monitor':False}}
    watch.safety(state);changed=deepcopy(state)
    if field=='orders':changed['orders_enabled']=True
    if field=='model':changed['research']['model_enabled']=True
    if field=='exit':changed['risk_policy']['local_exit_monitor']=True
    if field=='mode':changed['mode']='simulator'
    if field=='shadow':changed['shadow']['enabled']=False
    if field=='paper':changed['paper_only']=False
    with pytest.raises(ValueError):watch.safety(changed)


def test_observer_counts_lost_write_and_http_failure(tmp_path,monkeypatch):
    path=tmp_path/'audit.sqlite'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE events(seq INTEGER,type TEXT,payload TEXT)')
        db.executemany('INSERT INTO events VALUES(?,?,?)',[(1,'api_request',json.dumps({'method':'GET','status':429})),
            (2,'api_request_failed',json.dumps({'method':'POST'})),(3,'intent_committed','{}')])
    monkeypatch.setattr(watch,'DB',path)
    result=watch.audit(0)
    assert result['methods']=={'GET':1,'POST':1} and result['errors']==2 and result['new_order_events']==1
    assert watch.audit(3)['methods']=={}
