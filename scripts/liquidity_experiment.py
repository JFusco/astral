"""Register or sample a separately stored liquidity experiment. Never reads .env."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.config import ROOT
from backend.liquidity_runner import register,observe,state

parser=argparse.ArgumentParser()
parser.add_argument("action",choices=("register","sample","status"))
parser.add_argument("--db",type=Path,default=ROOT/"runtime/astral-stage2.sqlite")
args=parser.parse_args()
fn={"register":register,"sample":observe,"status":state}[args.action]
result=fn(args.db)
if args.action=="register":result={k:result[k] for k in ("id","sha256","code_matches","starts_at","ends_at","execution_enabled")}
print(json.dumps(result,indent=2))
