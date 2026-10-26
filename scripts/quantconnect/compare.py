"""Package the cloud algorithm or compare its downloaded log with frozen ASTRAL."""
import argparse
from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import tempfile

from .model import CONTRACT, START, END, FROZEN_MANIFEST, FIELDS, validate_bar

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
    model = (HERE / "model.py").read_text()
    algorithm = (HERE / "algorithm.py").read_text()
    module_import = "from scripts.quantconnect.model import (\n    CONTRACT, START, END, FROZEN_MANIFEST, FIELDS, validate_bar, evaluate,\n)\n"
    if algorithm.count(module_import) != 1:
        raise ValueError("Cloud packaging import changed")
    source = model + "\n" + algorithm.replace(module_import, "")
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
    # Verify frozen code before importing even the pure oracle module.
    from backend.risk import price_signal

    _, identity = bundle()
    records = [line.split("ASTRAL_QC|", 1)[1].strip() for line in text.splitlines() if "ASTRAL_QC|" in line]
    metadata = "|".join(("M", CONTRACT, "coinbase", "BTCUSD", str(START), str(END), FROZEN_MANIFEST, identity))
    if not records or records[0] != metadata or not records[-1].startswith("E|"):
        raise ValueError("Missing or mismatched comparison header/completion record")
    previous = None
    window = []
    counts = Counter()
    mismatches = []
    bars = signals = 0
    pending = None
    digest = hashlib.sha256()
    for record in records[1:-1]:
        digest.update((record + "\n").encode())
        parts = record.split("|")
        if parts[0] == "B" and len(parts) == 7:
            if pending is not None:
                raise ValueError("Missing signal for an evaluated bar")
            day = date.fromisoformat(parts[1])
            if previous is None and day != START:
                raise ValueError("Missing first historical day")
            _, high, low, close, _ = validate_bar(day, parts[2:], previous)
            previous = day
            bars += 1
            window = (window + [(high, low, close)])[-90:]
            if len(window) >= 51:
                pending = (str(day), price_signal(window))
        elif parts[0] == "S" and len(parts) == 7:
            if pending is None or parts[1] != pending[0]:
                raise ValueError("Unexpected, duplicated or misaligned signal")
            expected = pending[1]
            for key, observed in zip(FIELDS, parts[2:]):
                if key == "signal":
                    different = observed != expected[key]
                else:
                    value = Decimal(observed)
                    if not value.is_finite():
                        raise ValueError("Non-finite comparison indicator")
                    different = abs(value - expected[key]) > TOLERANCE
                if different:
                    mismatches.append({"day": parts[1], "field": key, "astral": str(expected[key]), "lean": observed})
            counts[expected["signal"]] += 1
            signals += 1
            pending = None
        else:
            raise ValueError("Unexpected comparison record")
    expected_end = f"E|{bars}|{signals}|0|{digest.hexdigest()}"
    if (pending is not None or bars != (END - START).days or signals != bars - 50
            or records[-1] != expected_end):
        raise ValueError("Incomplete, altered or nonzero-order comparison export")
    return {
        "contract": CONTRACT, "status": "pass" if not mismatches else "mismatch",
        "evidence_origin": origin,
        "declared_venue": "Coinbase; not Alpaca", "symbol": "BTCUSD",
        "start": str(START), "end_exclusive": str(END), "bars": bars, "signals": signals,
        "signal_counts": dict(counts), "mismatches": mismatches,
        "absolute_indicator_tolerance": str(TOLERANCE), "signal_tolerance": "exact",
        "frozen_manifest_sha256": FROZEN_MANIFEST, "frozen_sources": sources,
        "bundle_sha256": identity, "log_sha256": sha(text.encode()),
        "comparator_sha256": sha(Path(__file__).read_bytes()),
        "execution_enabled": False, "orders": 0, "profitability_evaluated": False,
        "limitations": ["Historical development data; not an untouched holdout",
                        "Price hypothesis only; no calendar, liquidity, sizing, exits, costs or fill validation",
                        "Cloud provenance and zero orders must also be checked in the saved QuantConnect backtest"],
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
            print(f"Prepared signal-only main.py in {destination}; bundle {identity}")
            return 0
        result = compare(Path(args.log).read_text(), origin=args.origin)
        destination = new_output(args.output)
        (destination / "report.json").write_text(json.dumps(result, indent=2) + "\n")
        (destination / "report.md").write_text(
            f"# BTC signal comparison\n\nStatus: {result['status']}. "
            f"Evidence origin (operator supplied): {result['evidence_origin']}. "
            f"Compared {result['signals']} signals from {result['bars']} daily bars "
            "under the Coinbase input contract. "
            f"Mismatched fields: {len(result['mismatches'])}. Orders: 0.\n\n"
            "Signal implementation agreement only. No profitability or Alpaca execution claim.\n"
        )
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "pass" else 1
    except (ValueError, InvalidOperation, OSError) as error:
        parser.exit(2, f"Comparison refused: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
