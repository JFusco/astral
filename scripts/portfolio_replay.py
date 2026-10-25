"""Offline model runner. Reads SQLite mode=ro; never loads credentials or orders."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.config import ROOT
from backend.replay_runner import build_report


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--db',type=Path,default=ROOT/'runtime/astral-stage2.sqlite')
    parser.add_argument('--register-holdout',action='store_true')
    args=parser.parse_args();result=build_report(args.db,register=args.register_holdout)
    print(json.dumps({'at':result['at'],'observed_quotes':result['observed_coverage']['quotes'],
                      'observed_packets':result['observed_coverage']['research_packets'],
                      'observed_hypothetical_fills':result['observed']['fill_count'],
                      'synthetic_scenarios':result['synthetic_scenarios'],
                      'forward':{k:v for k,v in result['forward'].items() if k not in {'coverage','replay'}},
                      'broker_orders_created':0,'profitability_validated':False,'receipt':result['receipt']}))


if __name__=='__main__':main()
