"""Read-only main-ledger input; append-only, separately registered experiment output.

No broker, Engine, credentials, model, networking or order API imports.
"""
from dataclasses import asdict
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import json
from pathlib import Path
import sqlite3

from .config import ROOT
from .experiment import contract, digest
from .liquidity import Policy, SCENARIOS, evaluate
from .risk import timestamp
from .evidence_codec import unpack_text

MANIFEST=ROOT/"experiments/btc-liquidity-depth-v1.json"
OUTPUT=ROOT/"runtime/btc-liquidity-depth-v1.sqlite"
CODE=("backend/liquidity.py","backend/liquidity_runner.py","backend/market_depth.py","backend/trade_history.py","backend/risk.py","backend/evidence_codec.py")


def now():return datetime.now(timezone.utc).isoformat()


@contextmanager
def readonly(path):
    db=sqlite3.connect(Path(path).resolve().as_uri()+"?mode=ro",uri=True)
    db.row_factory=sqlite3.Row;db.execute("PRAGMA query_only=ON");db.execute("BEGIN")
    try:yield db
    finally:db.close()


def get(db,key,default=None):
    row=db.execute("SELECT value FROM state WHERE key=?",(key,)).fetchone()
    return json.loads(row[0]) if row else default


def hashes():return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in CODE}


def binding(db):
    frozen=get(db,"frozen_experiment",{})
    if get(db,"mode")!="alpaca" or not frozen or not get(db,"account_binding"):
        raise ValueError("Bound frozen Alpaca paper ledger required")
    return digest({"mode":"alpaca","frozen":frozen,"account":get(db,"account_binding")})


def register(db_path, manifest_path=MANIFEST):
    if manifest_path.exists():
        value=load(manifest_path)
        with readonly(db_path) as db:
            if binding(db)!=value["ledger_binding_sha256"]:raise ValueError("Wrong paper ledger for experiment")
        return value
    frozen=contract()
    if not frozen or not frozen["code_matches"]:raise ValueError("Matching original frozen strategy required")
    with readonly(db_path) as db:
        if get(db,"frozen_experiment",{}).get("manifest_sha256")!=frozen["manifest_sha256"]:
            raise ValueError("Ledger original strategy registration mismatch")
        identity=binding(db);seq=db.execute("SELECT COALESCE(MAX(seq),0) FROM events").fetchone()[0]
    stamp=datetime.now(timezone.utc)
    value={"id":Policy().version,"symbol":"BTC","registered_at":stamp.isoformat(),"starts_at":stamp.isoformat(),
           "ends_at":(stamp+timedelta(days=14)).isoformat(),"baseline_event_seq":seq,"ledger_binding_sha256":identity,
           "source_sha256":hashes(),"baseline_strategy_manifest":frozen["manifest_sha256"],
           "policy":asdict(Policy()),"scenarios":SCENARIOS,"sample_interval_seconds":15,"max_sample_gap_seconds":45,
           "comparison":"Frozen $1m ADV / 1% top-level rule versus 2bps ADV / 1% two-sided displayed depth with half-depth haircut",
           "non_liquidity_gates":"Unchanged in original strategy. Feasible quote models never clear fee, event, signal, portfolio or execution-supervision gates",
           "acceptance":{"automatic_promotion":False,"profitability_pass":False,"review":"Retain rejected, stale and missing samples; 14 days is a collection window, not proof of an edge"},
           "execution_enabled":False,"fill_assumed":False,"development_data":"Previously inspected volume and depth informed hypothesis; excluded from prospective acceptance"}
    value["sha256"]=digest(value)
    manifest_path.parent.mkdir(exist_ok=True)
    with manifest_path.open("x") as out:json.dump(value,out,indent=2);out.write("\n")
    return load(manifest_path)


def load(path=MANIFEST):
    value=json.loads(path.read_text());sha=value.pop("sha256")
    if digest(value)!=sha:raise ValueError("Liquidity experiment contract changed")
    if (value["policy"]!=asdict(Policy()) or value["scenarios"]!=json.loads(json.dumps(SCENARIOS))
        or value["id"]!=Policy().version or value["execution_enabled"] is not False
        or timestamp(value["ends_at"])-timestamp(value["starts_at"])!=timedelta(days=14)):
        raise ValueError("Liquidity contract does not match implemented experiment")
    return {**value,"sha256":sha,"code_matches":value["source_sha256"]==hashes()}


def snapshot(db):
    row=db.execute("SELECT seq,at,payload FROM events WHERE type='quotes' ORDER BY seq DESC LIMIT 1").fetchone()
    if not row:raise ValueError("No recorded quote event")
    quote=json.loads(unpack_text(row["payload"])).get("BTC",{})
    sha=quote.get("depth",{}).get("raw_sha256")
    raw=db.execute("SELECT payload FROM depth_snapshots WHERE id=?",(sha,)).fetchone() if sha else None
    if not raw:raise ValueError("Recorded raw matching BTC depth unavailable")
    book=json.loads(unpack_text(raw[0]))
    if digest(book)!=sha:raise ValueError("Retained depth hash mismatch")
    history=get(db,"trade_history:BTC",{})
    return {"source_event_seq":row["seq"],"source_recorded_at":row["at"],"quote":quote,"raw_book":book,
            "history":{**{k:v for k,v in history.items() if k!="rows"},"rows":history.get("rows",[])[-21:]},
            "asset":get(db,"assets",{}).get("BTC",{}),
            "other_gates":{"inventory_status":get_inventory_status(db),"packet":next(({
                "as_of":p.get("as_of"),"input_hash":p.get("input_hash"),"eligible":p.get("eligible"),
                "signal":p.get("facts",{}).get("signal"),"vetoes":p.get("vetoes",[])} for p in get(db,"research_packets",[]) if p.get("symbol")=="BTC"),None)}}


def get_inventory_status(db):
    # Only recorded evidence, no reclassification or fee assumptions in the main ledger.
    return "fee-conflict" if get(db,"fee_reconciliation_required") else "see original inventory reconciliation; experiment does not certify custody"


def observe(db_path, manifest_path=MANIFEST, output_path=OUTPUT):
    if not manifest_path.exists():return {"status":"not-registered","execution_enabled":False}
    registered=load(manifest_path)
    if not registered["code_matches"]:raise ValueError("Liquidity experiment code drift; original contract retained")
    at=now();moment=timestamp(at)
    if moment<timestamp(registered["starts_at"]):raise ValueError("Before registered window")
    if moment>=timestamp(registered["ends_at"]):return {"status":"window-ended","ends_at":registered["ends_at"],"execution_enabled":False}
    with readonly(db_path) as db:
        if binding(db)!=registered["ledger_binding_sha256"]:raise ValueError("Wrong paper ledger for experiment")
        try:
            inputs=snapshot(db)
            if inputs["source_event_seq"]<=registered["baseline_event_seq"] or timestamp(inputs["quote"]["at"])<timestamp(registered["starts_at"]):
                raise ValueError("Pre-registration quote excluded from prospective comparison")
            result=evaluate(inputs,as_of=at)
            raw_hash=inputs["quote"]["depth"]["raw_sha256"]
            # Original raw depth remains in main ledger, referenced by content hash.
            retained={k:v for k,v in inputs.items() if k!="raw_book"};retained["raw_book_reference"]={"table":"depth_snapshots","id":raw_hash}
        except (ValueError,KeyError,TypeError,sqlite3.OperationalError) as exc:
            seq=db.execute("SELECT COALESCE(MAX(seq),0) FROM events WHERE type='quotes'").fetchone()[0]
            retained={"source_event_seq":seq,"evidence_error":str(exc)[:200]}
            result={"status":"invalid-evidence","as_of":at,"reasons":[str(exc)[:200]],"execution_enabled":False,"fill_assumed":False}
    output_path.parent.mkdir(parents=True,exist_ok=True);output_path.parent.chmod(0o700)
    with open(str(output_path)+".lock","a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        db=sqlite3.connect(output_path);output_path.chmod(0o600)
        try:
            db.executescript("""CREATE TABLE IF NOT EXISTS inputs(id TEXT PRIMARY KEY,payload TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS samples(id TEXT PRIMARY KEY,at TEXT NOT NULL,event_seq INTEGER NOT NULL,input_id TEXT NOT NULL,payload TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS registration(sha256 TEXT PRIMARY KEY,payload TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS statistics(id INTEGER PRIMARY KEY CHECK(id=1),payload TEXT NOT NULL);""")
            existing=db.execute("SELECT sha256 FROM registration").fetchall()
            if existing and existing!=[(registered["sha256"],)]:raise ValueError("Output belongs to another registered experiment")
            db.execute("INSERT OR IGNORE INTO registration VALUES(?,?)",(registered["sha256"],json.dumps(registered,sort_keys=True)))
            input_hash=digest(retained);key=digest({"contract":registered["sha256"],"input":input_hash})
            db.execute("INSERT OR IGNORE INTO inputs VALUES(?,?)",(input_hash,json.dumps(retained,sort_keys=True)))
            inserted=db.execute("INSERT OR IGNORE INTO samples VALUES(?,?,?,?,?)",(key,at,retained["source_event_seq"],input_hash,json.dumps(result,sort_keys=True)))
            if inserted.rowcount:
                prior=db.execute("SELECT payload FROM statistics WHERE id=1").fetchone()
                stats=json.loads(prior[0]) if prior else {"samples":0,"sample_gaps_over_45s":0,"largest_sample_gap_seconds":0,"invalid_samples":0,"baseline_liquidity_passes":0,"challenger_base_feasible":0}
                gap=(moment-timestamp(stats["last_observed_at"])).total_seconds() if stats.get("last_observed_at") else (moment-timestamp(registered["starts_at"])).total_seconds()
                stats.update(samples=stats["samples"]+1,last_observed_at=at,largest_sample_gap_seconds=max(stats["largest_sample_gap_seconds"],gap),
                             sample_gaps_over_45s=stats["sample_gaps_over_45s"]+(gap>45),
                             invalid_samples=stats["invalid_samples"]+(result["status"]!="evaluated"),
                             baseline_liquidity_passes=stats["baseline_liquidity_passes"]+bool(result.get("baseline",{}).get("liquidity_passed")),
                             challenger_base_feasible=stats["challenger_base_feasible"]+bool(result.get("scenarios",[{}])[0].get("feasible_quote_model")))
                db.execute("INSERT INTO statistics VALUES(1,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload",(json.dumps(stats),))
            db.commit()
        finally:db.close()
    return state(db_path,manifest_path,output_path)


def state(db_path,manifest_path=MANIFEST,output_path=OUTPUT):
    if not manifest_path.exists():return None
    value=load(manifest_path)
    with readonly(db_path) as db:
        if binding(db)!=value["ledger_binding_sha256"]:return None
    result={k:value[k] for k in ("id","sha256","code_matches","registered_at","starts_at","ends_at","sample_interval_seconds")}
    result.update(execution_enabled=False,fill_assumed=False,automatic_promotion=False,profitability_validated=False,samples=0)
    if not output_path.exists():return {**result,"status":"waiting"}
    with readonly(output_path) as db:
        registration=db.execute("SELECT sha256 FROM registration").fetchall()
        if [r[0] for r in registration]!=[value["sha256"]]:raise ValueError("Output contract mismatch")
        stats=db.execute("SELECT payload FROM statistics WHERE id=1").fetchone()
        if stats:result.update(json.loads(stats[0]))
        last=db.execute("SELECT at,payload FROM samples ORDER BY rowid DESC LIMIT 1").fetchone()
        if last:result.update(last_observed_at=last["at"],latest=json.loads(last["payload"]))
    moment=timestamp(now());age=(moment-timestamp(result["last_observed_at"])).total_seconds() if last else None
    result["status"]="code-drift" if not value["code_matches"] else "window-ended" if moment>=timestamp(value["ends_at"]) else "stale" if age is None or not 0<=age<=45 else "collecting"
    result["interpretation"]="Liquidity/cost diagnostics only. Original fee, calendar, signal, risk and execution gates still apply. No modeled fills or profit."
    return result
