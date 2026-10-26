"""Account ownership through public broker methods; no real provider writes."""
import asyncio
import os
import selectors
import subprocess
import sys
from types import SimpleNamespace

import httpx
import pytest

from backend import executor_ownership
from backend.broker import AlpacaPaper, BrokerFailure
from backend.config import Settings
from backend.store import Store
from test_service import run


@pytest.fixture
def adapters(tmp_path, monkeypatch):
    monkeypatch.setattr(executor_ownership, "LOCK_DIRECTORY", tmp_path / "account-locks")
    opened = []

    def create(identity="paper-account-a", *, enabled=True):
        cfg = Settings(db_path=tmp_path / f"book-{len(opened)}.sqlite", api_key="fixture", secret_key="fixture", enable_orders=enabled)
        store = Store(cfg.db_path, "alpaca")
        remote = {"body": {"id": identity}, "status": 200}
        seen = []

        async def handle(request):
            seen.append((request.method, request.url.path))
            if request.method == "GET" and request.url.path == "/v2/account":
                return httpx.Response(remote["status"], json=remote["body"])
            if remote.get("during_write"):
                await remote["during_write"]()
            return httpx.Response(200, json={"accepted": True})

        broker = AlpacaPaper(cfg, store, httpx.MockTransport(handle))
        item = SimpleNamespace(broker=broker, store=store, remote=remote, seen=seen,
                               writes=lambda: [r for r in seen if r[0] != "GET"])
        opened.append(item)
        return item

    yield create
    for item in opened:
        run(item.broker.close())
        item.store.close()


def test_distinct_databases_share_one_account_writer_until_owner_closes(adapters):
    owner, contender = adapters(), adapters()
    run(owner.broker.submit({}))
    for call in (contender.broker.submit({}), contender.broker.cancel("fixture-order"),
                 contender.broker.request("POST", "/v2/orders"), contender.broker.request("DELETE", "/v2/orders/fixture-order")):
        with pytest.raises(BrokerFailure, match="Another local executor") as error:
            run(call)
        assert error.value.sent is False
    assert not contender.writes()
    run(owner.broker.cancel("fixture-order"))
    assert owner.writes() == [("POST", "/v2/orders"), ("DELETE", "/v2/orders/fixture-order")]
    run(owner.broker.close())
    run(contender.broker.submit({}))
    assert contender.writes() == [("POST", "/v2/orders")]


def test_different_accounts_can_write_and_read_only_observers_do_not_contend(adapters):
    first, second, observer = adapters(), adapters("paper-account-b"), adapters(enabled=False)

    async def scenario():
        await asyncio.gather(first.broker.submit({}), second.broker.submit({}))
        assert await observer.broker.request("GET", "/v2/account") == {"id": "paper-account-a"}
        for operation in (observer.broker.submit({}), observer.broker.cancel("fixture-order")):
            with pytest.raises(BrokerFailure, match="Read-only") as error:
                await operation
            assert error.value.sent is False

    run(scenario())
    assert len(first.writes()) == len(second.writes()) == 1
    assert not observer.writes()


@pytest.mark.parametrize("body", [None, [], {}, {"id": ""}, {"id": 42}, {"id": "wrong identity"}],
                         ids=["null", "array", "missing", "empty", "number", "whitespace"])
def test_unverified_identity_denies_write_before_transport(adapters, body):
    adapter = adapters();adapter.remote["body"] = body
    with pytest.raises(BrokerFailure, match="identity is unavailable") as error:
        run(adapter.broker.submit({}))
    assert error.value.sent is False and not adapter.writes()
    assert adapter.store.get("account_binding") is None


def test_failed_identity_read_never_becomes_an_uncertain_submission(adapters):
    adapter = adapters();adapter.remote["status"] = 503
    with pytest.raises(BrokerFailure, match="identity read failed") as error:
        run(adapter.broker.submit({}))
    assert error.value.sent is False and not adapter.writes()


def test_changed_identity_latches_writes_even_if_the_original_identity_returns(adapters):
    adapter = adapters();run(adapter.broker.submit({}))
    adapter.remote["body"] = {"id": "another-account"}
    with pytest.raises(BrokerFailure, match="identity changed") as error:
        run(adapter.broker.cancel("fixture-order"))
    assert error.value.sent is False
    adapter.remote["body"] = {"id": "paper-account-a"}
    with pytest.raises(BrokerFailure, match="authority is unavailable"):
        run(adapter.broker.submit({}))
    assert adapter.writes() == [("POST", "/v2/orders")]
    assert adapter.store.get("account_binding") == "paper-account-a"


def test_existing_account_binding_cannot_be_silently_replaced(adapters):
    adapter = adapters();adapter.store.put("account_binding", "previous-account")
    with pytest.raises(BrokerFailure, match="identity changed") as error:
        run(adapter.broker.submit({}))
    assert error.value.sent is False and not adapter.writes()
    assert adapter.store.get("account_binding") == "previous-account"


@pytest.mark.parametrize("condition", ["directory-symlink", "directory-permissions", "file-symlink", "file-hardlink", "file-permissions"])
def test_unsafe_lock_storage_denies_mutation_without_fallback(adapters, tmp_path, condition):
    owner = adapters();run(owner.broker.submit({}));run(owner.broker.close())
    root = tmp_path / "account-locks";lock = next(root.glob("*.lock"))
    if condition == "directory-symlink":
        root.rename(tmp_path / "moved-locks");root.symlink_to(tmp_path / "moved-locks", target_is_directory=True)
    elif condition == "directory-permissions":root.chmod(0o755)
    elif condition == "file-symlink":
        lock.rename(tmp_path / "moved-lock");lock.symlink_to(tmp_path / "moved-lock")
    elif condition == "file-hardlink":os.link(lock, tmp_path / "extra-link")
    else:lock.chmod(0o644)
    contender = adapters()
    with pytest.raises(BrokerFailure, match="lock storage") as error:
        run(contender.broker.submit({}))
    assert error.value.sent is False and not contender.writes()


def test_replaced_lock_name_revokes_the_existing_writer(adapters, tmp_path):
    adapter = adapters();run(adapter.broker.submit({}))
    lock = next((tmp_path / "account-locks").glob("*.lock"))
    lock.unlink();lock.touch(mode=0o600)
    with pytest.raises(BrokerFailure, match="lock storage") as error:
        run(adapter.broker.cancel("fixture-order"))
    assert error.value.sent is False
    assert adapter.writes() == [("POST", "/v2/orders")]


def test_closed_adapter_cannot_reacquire_authority_and_market_data_cannot_mutate(adapters):
    adapter = adapters()
    with pytest.raises(BrokerFailure, match="GET-only"):
        run(adapter.broker.request("POST", "/v2/orders", data=True))
    run(adapter.broker.close())
    with pytest.raises(BrokerFailure, match="authority is unavailable"):
        run(adapter.broker.submit({}))
    assert not adapter.seen


@pytest.mark.parametrize("override", [
    {"headers": {"APCA-API-KEY-ID": "different-fixture-key"}},
    {"auth": None},
    {"follow_redirects": True},
    {"cookies": {"session": "different-fixture-session"}},
    {"extensions": {"custom_authentication": "fixture"}},
], ids=["credentials", "authentication", "redirects", "cookies", "extensions"])
def test_write_cannot_override_the_verified_authentication_or_redirect_policy(adapters, override):
    adapter = adapters()
    with pytest.raises(BrokerFailure, match="fixed authentication and redirect") as error:
        run(adapter.broker.request("POST", "/v2/orders", **override))
    assert error.value.sent is False and not adapter.seen


def test_close_keeps_ownership_until_the_inflight_write_finishes(adapters):
    owner, contender = adapters(), adapters()

    async def scenario():
        entered, finish, closing_started = asyncio.Event(), asyncio.Event(), asyncio.Event()
        async def pause():
            entered.set();await finish.wait()
        async def close():
            closing_started.set();await owner.broker.close()
        owner.remote["during_write"] = pause
        writing = asyncio.create_task(owner.broker.submit({}))
        closing = None
        try:
            await asyncio.wait_for(entered.wait(), timeout=5)
            closing = asyncio.create_task(close())
            await asyncio.wait_for(closing_started.wait(), timeout=5)
            with pytest.raises(BrokerFailure, match="Another local executor"):
                await contender.broker.submit({})
            assert not contender.writes()
            finish.set();await writing;await closing
            await contender.broker.submit({})
            assert contender.writes() == [("POST", "/v2/orders")]
        finally:
            finish.set()
            await asyncio.gather(writing, *([closing] if closing else []), return_exceptions=True)

    run(scenario())


PROCESS_WORKER = """
import asyncio,os,pwd,sys
sys.modules['readline']=None
from pathlib import Path
from types import SimpleNamespace
# The OS account home stays shared while process HOME profiles differ.
pwd.getpwuid=lambda uid:SimpleNamespace(pw_dir=sys.argv[1])
os.environ['HOME']=str(Path(sys.argv[1])/(sys.argv[2]+'-profile'))
import httpx
from backend import executor_ownership
from backend.broker import AlpacaPaper,BrokerFailure
from backend.config import Settings
from backend.store import Store
cfg=Settings(db_path=Path(sys.argv[1])/(sys.argv[2]+'.sqlite'),api_key='fixture',secret_key='fixture',enable_orders=True)
store=Store(cfg.db_path,'alpaca');writes=[];seen=[]
def handle(req):
    seen.append(req.method)
    if req.method=='GET':return httpx.Response(200,json={'id':'process-paper-account'})
    writes.append(req.method);return httpx.Response(200,json={})
broker=AlpacaPaper(cfg,store,httpx.MockTransport(handle))
async def scenario():
    try:
        await broker.submit({})
    except BrokerFailure as error:
        assert not error.sent and not writes
        print('DENIED',flush=True)
    else:
        assert writes==['POST']
        if sys.argv[2]=='fork-owner':
            child=os.fork()
            if child==0:
                try:
                    await broker.submit({})
                except BrokerFailure as error:
                    assert not error.sent and 'Inherited' in str(error) and seen==['GET','POST']
                    await broker.close()
                    os._exit(0)
                except BaseException:
                    import traceback
                    traceback.print_exc();os._exit(2)
                os._exit(1)
            _,status=os.waitpid(child,0)
            assert os.WIFEXITED(status) and os.WEXITSTATUS(status)==0
        print('OWNED',flush=True)
        if sys.argv[2] in {'owner','fork-owner'}:sys.stdin.readline()
    finally:await broker.close();store.close()
asyncio.run(scenario())
"""


@pytest.mark.parametrize("owner_mode", ["owner", "fork-owner"])
def test_distinct_home_profiles_share_ownership_and_recover_after_sigkill(tmp_path, owner_mode):
    args = [sys.executable, "-c", PROCESS_WORKER, str(tmp_path)]
    owner = subprocess.Popen(args + [owner_mode], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    selector = selectors.DefaultSelector()
    try:
        selector.register(owner.stdout, selectors.EVENT_READ)
        assert selector.select(timeout=15), "Owner did not acquire write authority"
        if owner.stdout.readline().strip() != "OWNED":
            _, error = owner.communicate(timeout=5)
            pytest.fail(error)
        contender = subprocess.run(args + ["contender"], input="", capture_output=True, text=True, timeout=15)
        assert contender.returncode == 0, contender.stderr
        assert contender.stdout.strip() == "DENIED"
        owner.kill();owner.communicate(timeout=10)
        assert owner.returncode == -9
        recovered = subprocess.run(args + ["successor"], input="", capture_output=True, text=True, timeout=15)
        assert recovered.returncode == 0, recovered.stderr
        assert recovered.stdout.strip() == "OWNED"
    finally:
        selector.close()
        if owner.poll() is None:
            owner.kill();owner.communicate(timeout=10)
