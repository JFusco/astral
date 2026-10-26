"""Package an in-cloud comparison or validate its aggregate-only diagnostic log."""
import argparse
import ast
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import tempfile

from .model import CONTRACT, START, END, FROZEN_MANIFEST, FIELDS

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
TOLERANCE = Decimal("1e-20")


def sha(content):
    return hashlib.sha256(content).hexdigest()


def pinned_sources(root=ROOT):
    manifest = json.loads((root / "experiments/btc-daily-swing-v1.json").read_text())
    registered = manifest.pop("manifest_sha256")
    actual = sha(json.dumps(manifest, sort_keys=True, separators=(",", ":"), allow_nan=False).encode())
    if registered != FROZEN_MANIFEST or actual != registered:
        raise ValueError("Frozen manifest differs from the pinned comparison")
    for filename, expected in manifest["source_sha256"].items():
        if sha((root / filename).read_bytes()) != expected:
            raise ValueError(f"Frozen source drift: {filename}")
    return manifest["source_sha256"]


def bundle():
    pinned_sources()
    frozen = (ROOT / "backend/risk.py").read_text()
    functions = [node for node in ast.parse(frozen).body
                 if isinstance(node, ast.FunctionDef) and node.name == "price_signal"]
    if len(functions) != 1:
        raise ValueError("Frozen signal function is ambiguous")
    oracle = ast.get_source_segment(frozen, functions[0])
    model = (HERE / "model.py").read_text()
    algorithm = (HERE / "algorithm.py").read_text()
    imports = ("from scripts.quantconnect.model import (\n    CONTRACT, START, END, FROZEN_MANIFEST, FIELDS, validate_bar, evaluate,\n)\n",
               "from backend.risk import price_signal\n")
    for statement in imports:
        if algorithm.count(statement) != 1:
            raise ValueError("Cloud packaging import changed")
        algorithm = algorithm.replace(statement, "")
    source = model + "\n" + oracle + "\n\n" + algorithm
    identity = sha(source.encode())
    return source.replace('BUNDLE_ID = "unprepared"', f'BUNDLE_ID = "{identity}"'), identity


def new_output(path):
    destination = Path(path).resolve()
    allowed = ROOT / "outputs/quantconnect"
    temporary = Path(tempfile.gettempdir()).resolve()
    if destination.is_relative_to(ROOT) and not destination.is_relative_to(allowed):
        raise ValueError("Repository output is restricted to outputs/quantconnect")
    if not (destination.is_relative_to(allowed) or destination.is_relative_to(temporary)):
        raise ValueError("Use a new directory under outputs/quantconnect or the system temporary directory")
    destination.mkdir(parents=True, exist_ok=False)
    return destination


def compare(text, *, origin="unverified-export"):
    if origin not in {"unverified-export", "local-fixture", "quantconnect-cloud-export"}:
        raise ValueError("Unknown evidence origin")
    sources = pinned_sources()
    _, identity = bundle()
    records = [line.split("ASTRAL_QC|", 1)[1].strip() for line in text.splitlines() if "ASTRAL_QC|" in line]
    metadata = "|".join(("M", CONTRACT, "coinbase", "BTCUSD", str(START), str(END), FROZEN_MANIFEST, identity))
    if len(records) != 2 or records[0] != metadata or not records[1].startswith("R|"):
        raise ValueError("Expected the pinned header and one aggregate completion record; raw-data exports are refused")
    summary = json.loads(records[1][2:])
    fields = {"bars", "signals", "orders", "mismatched_signals", "signal_counts", "max_absolute_errors"}
    if not isinstance(summary, dict) or set(summary) != fields:
        raise ValueError("Unexpected aggregate comparison fields")
    def count(value):
        if type(value) is not int or value < 0:
            raise ValueError("Comparison counts must be nonnegative integers")
        return value
    bars, signals, orders, mismatches = (count(summary[key]) for key in ("bars", "signals", "orders", "mismatched_signals"))
    if bars != (END - START).days or signals != bars - 50 or orders or mismatches > signals:
        raise ValueError("Incomplete or nonzero-order comparison")
    counts, errors = summary["signal_counts"], summary["max_absolute_errors"]
    if (not isinstance(counts, dict) or set(counts) != {"hold", "entry_candidate", "exit_review"}
            or sum(count(value) for value in counts.values()) != signals
            or not isinstance(errors, dict) or set(errors) != set(FIELDS) - {"signal"}):
        raise ValueError("Invalid signal counts or comparison errors")
    numeric = {key: Decimal(value) if isinstance(value, str) else Decimal("NaN") for key, value in errors.items()}
    if any(not value.is_finite() or value < 0 for value in numeric.values()):
        raise ValueError("Comparison errors must be finite and nonnegative")
    if not mismatches and any(value > TOLERANCE for value in numeric.values()):
        raise ValueError("Mismatch count contradicts indicator errors")
    return {
        "contract": CONTRACT, "status": "pass" if not mismatches else "mismatch",
        "evidence_origin": origin, "comparison_location": "Both implementations in the same cloud process",
        "declared_venue": "Coinbase; not Alpaca", "symbol": "BTCUSD",
        "start": str(START), "end_exclusive": str(END), **summary,
        "absolute_indicator_tolerance": str(TOLERANCE), "signal_tolerance": "exact",
        "frozen_manifest_sha256": FROZEN_MANIFEST, "frozen_sources": sources,
        "bundle_sha256": identity, "log_sha256": sha(text.encode()),
        "comparator_sha256": sha(Path(__file__).read_bytes()),
        "execution_enabled": False, "profitability_evaluated": False,
        "limitations": ["Aggregate diagnostics only; no raw bars, indicator series or raw-data digests exported",
                        "Historical development data; no untouched holdout or Alpaca execution validation",
                        "No calendar, liquidity, sizing, exits, costs, fill or profitability validation",
                        "Local validation checks the summary contract, not a recomputation of cloud market data",
                        "Verify source, completion and zero orders in the saved QuantConnect backtest separately"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--output", required=True)
    check = sub.add_parser("compare")
    check.add_argument("--log", required=True)
    check.add_argument("--origin", required=True, choices=("local-fixture", "quantconnect-cloud-export"))
    check.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        pinned_sources()
        if args.command == "prepare":
            source, identity = bundle()
            destination = new_output(args.output)
            (destination / "main.py").write_text(source)
            print(f"Prepared aggregate-only main.py in {destination}; bundle {identity}")
            return 0
        result = compare(Path(args.log).read_text(), origin=args.origin)
        destination = new_output(args.output)
        (destination / "report.json").write_text(json.dumps(result, indent=2) + "\n")
        (destination / "report.md").write_text(
            f"# BTC signal comparison\n\nStatus: {result['status']}. "
            f"Evidence origin (operator supplied): {result['evidence_origin']}. "
            f"In-cloud summary: {result['signals']} signals, {result['bars']} bars, "
            f"{result['mismatched_signals']} mismatches and zero orders.\n\n"
            "Aggregate contract validation only; no local raw-data recomputation, profitability or Alpaca execution claim.\n")
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "pass" else 1
    except (ValueError, InvalidOperation, OSError) as error:
        parser.exit(2, f"Comparison refused: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
