"""Register once; run offline diagnostic from an existing read-only history DB.

Never loads .env, imports Engine, starts workers or calls a broker endpoint.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.config import ROOT
from backend import experiment


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--history-db",type=Path,required=True)
    args=parser.parse_args()
    if experiment.MANIFEST.exists():raise SystemExit("Experiment already frozen; use a separately reviewed version for changes")
    manifest={"id":"btc-daily-swing-v1","symbol":"BTC","venue":"Alpaca US PAPER","horizon":"daily swing",
        "frozen_at":datetime.now(timezone.utc).isoformat(),"source_sha256":experiment.source_hashes(),
        "notional_cap_usd":"25","risk_budget_equity_fraction":"0.0025","model_arm":"deterministic no-model baseline",
        "data":"Same-venue executed-trade daily UTC bars, at most 90 completed bars; no invented missing days",
        "indicators":{"atr":"Wilder14","trend":[20,50],"breakout":"close strictly above prior 20 highs"},
        "entry":"Closed-bar candidate, cost hurdle, subsequent fresh quote and all news/calendar/portfolio/depth/liquidity gates",
        "exit":{"stop_atr_multiple":"2","reward_stop_multiple":"2","max_holding_days":10,"trend":"close below SMA50","cooldown_minutes":5},
        "cost_assumptions":{"fee_bps_per_side":"25","slippage_bps_round_trip":"10","crypto_gap_stress_bps":"200","fees_confirmed":False},
        "forward":{"minimum_observation_days":14,"poll_seconds":900,"scope":"Evidence and veto observations only; no simulated or broker fills",
                   "restart_gaps":"Retain and report; never backfill prospective observations"},
        "acceptance":{"infrastructure":"Every observation retains source times, revision hashes, code match, sizing and final veto; zero broker writes",
                      "strategy":"No promotion until realistic portfolio/cost replay, chronological holdout and adequate prospective/regime coverage are separately reviewed"},
        "known_limitations":["Historical price dataset was inspected before registration; it is development data, not an untouched holdout",
            "Complete financial/protocol/macro calendars, quote depth units and fee attribution remain unresolved",
            "Realistic portfolio replay and protective execution validation remain outstanding"],
        "execution_enabled":False,"automatic_promotion":False,"learning_enabled":False}
    manifest["manifest_sha256"]=experiment.digest(manifest)
    experiment.MANIFEST.parent.mkdir(exist_ok=True)
    with experiment.MANIFEST.open("x") as f:json.dump(manifest,f,indent=2);f.write("\n")
    db=sqlite3.connect(args.history_db.resolve().as_uri()+"?mode=ro",uri=True)
    history=json.loads(db.execute("SELECT value FROM state WHERE key='trade_history:BTC'").fetchone()[0]);db.close()
    result=experiment.diagnose(history);result["manifest_sha256"]=manifest["manifest_sha256"]
    out=ROOT/"runtime/btc-daily-swing-v1-history-diagnostic.json"
    out.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"experiment":manifest["id"],"manifest_sha256":manifest["manifest_sha256"],"prefixes":result["evaluated_prefixes"],"signals":result["signal_counts"],"fills_assumed":False}))


if __name__=="__main__":main()
