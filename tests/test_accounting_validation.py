"""Disposable CLI keeps its GET-only request and sanitized-failure contracts."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3

import httpx
import pytest

from backend.broker import AlpacaPaper
from backend.config import Settings
from backend import activity_validation as validation

FIXTURE = Path(__file__).parent/'fixtures/activity_feed/btc-sanitized-v1'
NOW = '2030-01-01T00:00:00+00:00'


@pytest.mark.parametrize('fault', [None,'invalid-number','invalid-epoch'], ids=['success','bad-financial-value','corrupt-counter'])
def test_disposable_connected_cli_preserves_get_count_closure_inputs_and_receipt(tmp_path,monkeypatch,capsys,fault):
    source = tmp_path/'controlled-inputs';shutil.copytree(FIXTURE,source)
    mapping = json.loads((source/'mapping.json').read_text());mapping['kind'] = 'reviewed-provider'
    ledger_path = source/'ledger-selected-readonly.json'
    ledger = json.loads(ledger_path.read_text())
    if fault == 'invalid-epoch':
        ledger['state']['snapshot_epoch'] = False
        ledger_path.write_text(json.dumps(ledger))
        for name in mapping['source_files']:
            if Path(name).name == ledger_path.name:mapping['source_files'][name] = hashlib.sha256(ledger_path.read_bytes()).hexdigest()
    (source/'mapping.json').write_text(json.dumps(mapping))
    inputs = [source/name for name in ['mapping.json','ledger-selected-readonly.json','activity-sse.json','activity-sse.raw']]
    before = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    snapshot = deepcopy(ledger['state']['account_snapshot'])
    if fault == 'invalid-number':snapshot['account']['cash'] = 'private-invalid-number'
    orders = [json.loads(o['raw']) for o in ledger['rows']['orders']]
    calls,brokers,stores = [],[],[]
    def handler(request):
        calls.append((request.method,request.url.path));assert request.method == 'GET'
        if request.url.path == '/v2/account':return httpx.Response(200,json=snapshot['account'])
        if request.url.path == '/v2/positions':return httpx.Response(200,json=snapshot['positions'])
        if request.url.path == '/v2/clock':return httpx.Response(200,json=snapshot['clock'])
        if request.url.path == '/v2/orders':return httpx.Response(200,json=orders)
        assert request.url.path == '/v2beta1/events/activities'
        return httpx.Response(200,headers={'content-type':'text/event-stream'},content=(source/'activity-sse.raw').read_bytes())
    def broker(settings,store):
        obj=AlpacaPaper(settings,store,httpx.MockTransport(handler));brokers.append(obj);return obj
    original_store=validation.Store
    def store(*args,**kwargs):
        obj=original_store(*args,**kwargs);stores.append(obj);return obj
    monkeypatch.setattr('backend.broker.AlpacaPaper',broker)
    monkeypatch.setattr(validation,'Store',store)
    monkeypatch.setattr(Settings,'from_env',lambda:Settings(api_key='fixture',secret_key='fixture'))
    for name in ['backend.activity_validation.utcnow','backend.activity_feed.utcnow','backend.broker.utcnow','backend.inventory.utcnow']:
        monkeypatch.setattr(name,lambda:NOW)
    output=tmp_path/'disposable-result'
    monkeypatch.setattr('sys.argv',['activity-validation','--mapping-file',str(source/'mapping.json'),
        '--ledger-capture',str(ledger_path),'--activity-capture',str(source/'activity-sse.json'),
        '--raw-stream',str(source/'activity-sse.raw'),'--database',str(output/'database.sqlite'),
        '--output-dir',str(output),'--connected'])
    if fault:
        with pytest.raises(SystemExit) as caught:validation.main()
        assert caught.value.code == 1 and not (output/'receipt.json').exists()
        stderr=capsys.readouterr().err
        assert 'Activity validation failed: SnapshotCommitError; no source-ledger writes' in stderr
        assert 'private-invalid' not in stderr and 'Traceback' not in stderr
        assert [path for _,path in calls] == ['/v2/account','/v2/positions','/v2/clock','/v2/orders']
    else:
        validation.main();receipt=json.loads((output/'receipt.json').read_text())
        assert all(receipt['checks'].values())
        assert receipt['connected']['broker_writes'] == 0
        assert receipt['connected']['acquisition']['snapshot_epoch'] == 1
        assert [path for _,path in calls] == ['/v2/account','/v2/positions','/v2/clock','/v2/orders',
            '/v2/account','/v2beta1/events/activities','/v2/account','/v2/positions',
            '/v2/account','/v2/positions','/v2/clock']
        files=[*Path(validation.__file__).parent.glob('activity_*.py'),Path(validation.__file__).with_name('evidence_codec.py'),
               Path(validation.__file__).with_name('accounting_snapshot.py')]
        assert receipt['implementation_sha256'] == {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    assert len(brokers)==1 and brokers[0].http.is_closed
    for obj in stores:
        with pytest.raises(sqlite3.ProgrammingError,match='closed database'):obj.db.execute('SELECT 1')
    assert {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs} == before
