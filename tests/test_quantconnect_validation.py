"""Protect parity evidence, frozen-window isolation and the zero-order boundary."""
from datetime import datetime, time, timedelta
from decimal import Decimal
import hashlib
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from backend.risk import price_signal
from scripts.quantconnect import compare as comparison
from scripts.quantconnect.model import START, END, FIELDS, evaluate


def daily_bars():
    rows = []
    for index in range((END - START).days):
        close = Decimal(10000 + (index * 9 if index < 70 else 630 - (index - 70) * 17))
        if index > 125:
            close = Decimal(9500 + (index - 125) * 23)
        day = START + timedelta(days=index)
        rows.append((day, [close - 1, close + 2, close - 3, close, Decimal(100)]))
    return rows


def trace(rows=None, mutate=None):
    _, identity = comparison.bundle()
    records = ["M|" + "|".join((comparison.CONTRACT, "coinbase", "BTCUSD", str(START), str(END), comparison.FROZEN_MANIFEST, identity))]
    window = []
    signals = 0
    for day, values in rows or daily_bars():
        records.append("B|" + "|".join((str(day), *(str(value) for value in values))))
        window = (window + [(values[1], values[2], values[3])])[-90:]
        if len(window) >= 51:
            result = evaluate(window)
            records.append("S|" + "|".join((str(day), *(str(result[key]) for key in FIELDS))))
            signals += 1
    if mutate:
        mutate(records)
    digest = hashlib.sha256("".join(record + "\n" for record in records[1:]).encode()).hexdigest()
    records.append(f"E|{len(rows or daily_bars())}|{signals}|0|{digest}")
    return "\n".join("2025-01-01 00:00:00 : ASTRAL_QC|" + record for record in records)


def test_identical_bars_agree_across_all_signal_states_and_capped_windows():
    result = comparison.compare(trace())
    assert result["status"] == "pass"
    assert result["signals"] == 131 and result["bars"] == 181
    assert set(result["signal_counts"]) == {"hold", "entry_candidate", "exit_review"}
    assert result["evidence_origin"] == "unverified-export"
    assert not result["profitability_evaluated"] and result["orders"] == 0


@pytest.mark.parametrize("field,value", [("atr", "12345"), ("signal", "hold")], ids=["indicator-drift", "decision-drift"])
def test_changed_cloud_result_reports_the_actual_mismatch(field, value):
    def mutate(records):
        index = next(i for i, row in enumerate(records) if row.startswith("S|") and row.endswith("entry_candidate"))
        parts = records[index].split("|")
        parts[2 + FIELDS.index(field)] = value
        records[index] = "|".join(parts)
    result = comparison.compare(trace(mutate=mutate))
    assert result["status"] == "mismatch"
    assert result["mismatches"][0]["field"] == field


def test_rolling_atr_restarts_after_old_bar_leaves_and_future_prices_cannot_change_past():
    rows = daily_bars()
    rows[0][1][1] += 10000
    text = trace(rows)
    assert comparison.compare(text)["status"] == "pass"
    final = [(v[1], v[2], v[3]) for _, v in rows[-90:]]
    assert evaluate(final) == price_signal(final)
    rows[-1][1][1] += 1000
    assert text.split("ASTRAL_QC|B|2025-06-30")[0] == trace(rows).split("ASTRAL_QC|B|2025-06-30")[0]


@pytest.mark.parametrize("boundary", ["prior-high", "slow-mean"], ids=["equal-breakout-holds", "equal-slow-mean-holds"])
def test_exact_threshold_equality_does_not_create_entry_or_exit(boundary):
    window = [(Decimal(i + 102), Decimal(i + 98), Decimal(i + 100)) for i in range(60)]
    if boundary == "prior-high":
        high, low, close = window[-2]
        window[-2] = (window[-1][2], low, close)
    else:
        window = [(Decimal(102), Decimal(98), Decimal(100))] * 60
    assert evaluate(window)["signal"] == "hold"


@pytest.mark.parametrize("condition", ["missing-day", "duplicate-day", "future-period", "nan", "range", "missing-signal", "duplicate-signal", "wrong-venue", "wrong-bundle", "missing-end", "altered-end", "orders" ])
def test_invalid_or_incomplete_cloud_evidence_cannot_pass(condition):
    text = trace()
    lines = text.splitlines()
    if condition == "missing-day":
        lines.pop(12)
    elif condition == "duplicate-day":
        lines.insert(12, lines[11])
    elif condition == "future-period":
        lines[1] = lines[1].replace("B|2025-01-01", "B|2026-10-25")
    elif condition in {"nan", "range"}:
        parts = lines[1].split("|")
        parts[3] = "NaN" if condition == "nan" else "1"
        lines[1] = "|".join(parts)
    elif condition in {"missing-signal", "duplicate-signal"}:
        index = next(i for i, row in enumerate(lines) if "ASTRAL_QC|S|" in row)
        if condition == "missing-signal":
            lines.pop(index)
        else:
            lines.insert(index, lines[index])
    elif condition == "wrong-venue":
        lines[0] = lines[0].replace("coinbase", "alpaca")
    elif condition == "wrong-bundle":
        lines[0] += "altered"
    elif condition == "missing-end":
        lines.pop()
    elif condition == "altered-end":
        lines[-1] += "altered"
    else:
        lines[-1] = lines[-1].replace("|131|0|", "|131|1|")
    with pytest.raises((ValueError, ArithmeticError)):
        comparison.compare("\n".join(lines))


def test_manifest_and_source_drift_refuse_comparison(tmp_path):
    source_root = comparison.ROOT
    manifest = Path("experiments/btc-daily-swing-v1.json")
    (tmp_path / manifest).parent.mkdir()
    (tmp_path / manifest).write_bytes((source_root / manifest).read_bytes())
    for filename in comparison.pinned_sources():
        target = tmp_path / filename
        target.parent.mkdir(exist_ok=True)
        target.write_bytes((source_root / filename).read_bytes())
    (tmp_path / "backend/risk.py").write_text("drift")
    with pytest.raises(ValueError, match="source drift"):
        comparison.pinned_sources(tmp_path)
    (tmp_path / manifest).write_text((tmp_path / manifest).read_text().replace('"25"', '"26"'))
    with pytest.raises(ValueError, match="manifest"):
        comparison.pinned_sources(tmp_path)


def test_outputs_cannot_overwrite_existing_artifacts_or_follow_symlinks_into_runtime(tmp_path, monkeypatch):
    monkeypatch.setattr(comparison, "ROOT", tmp_path)
    for directory in ("runtime", "experiments", "evidence"):
        with pytest.raises(ValueError):
            comparison.new_output(tmp_path / directory / "result")
    output = comparison.new_output(tmp_path / "outputs/quantconnect/run")
    with pytest.raises(FileExistsError):
        comparison.new_output(output)
    (tmp_path / "runtime").mkdir()
    (tmp_path / "outputs/quantconnect/link").symlink_to(tmp_path / "runtime", target_is_directory=True)
    with pytest.raises(ValueError):
        comparison.new_output(tmp_path / "outputs/quantconnect/link/result")


def cloud_algorithm(monkeypatch, *, live=False, orders=None):
    class Host:
        live_mode = live

        def __init__(self):
            self.logs = []
            self.subscriptions = []
            self.transactions = SimpleNamespace(get_orders=lambda: orders or [])
            self.portfolio = SimpleNamespace(invested=False)

        def set_time_zone(self, zone): pass
        def set_start_date(self, *args): pass
        def set_end_date(self, *args): pass
        def set_cash(self, amount): pass

        def add_crypto(self, ticker, resolution, **kwargs):
            self.subscriptions.append((ticker, resolution, kwargs))
            return SimpleNamespace(symbol="BTCUSD")

        def log(self, message): self.logs.append(message)

    imports = ModuleType("AlgorithmImports")
    imports.QCAlgorithm = Host
    imports.Resolution = SimpleNamespace(DAILY="daily")
    imports.Market = SimpleNamespace(COINBASE="coinbase")
    imports.TimeZones = SimpleNamespace(UTC="UTC")
    monkeypatch.setitem(__import__("sys").modules, "AlgorithmImports", imports)
    namespace = {}
    exec(compile(comparison.bundle()[0], "packaged-main.py", "exec"), namespace)
    return namespace["AstralBtcSignalParity"]()


def run_bars(algorithm, rows=None, *, fill_forward=False, unfinished=False):
    for day, values in rows or daily_bars():
        opening, high, low, close, volume = values
        start = datetime.combine(day, time())
        end = start + timedelta(days=1)
        algorithm.utc_time = start if unfinished else end
        bar = SimpleNamespace(time=start, end_time=end, open=opening, high=high, low=low,
                              close=close, volume=volume, is_fill_forward=fill_forward)
        algorithm.on_data(SimpleNamespace(bars={"BTCUSD": bar}))


def test_packaged_algorithm_exports_comparable_cloud_records_without_order_interface(monkeypatch):
    algorithm = cloud_algorithm(monkeypatch)
    algorithm.initialize()
    run_bars(algorithm)
    algorithm.on_end_of_algorithm()
    assert comparison.compare("\n".join(algorithm.logs))["status"] == "pass"
    assert algorithm.subscriptions == [("BTCUSD", "daily", {"market": "coinbase", "fill_forward": False})]


def test_live_mode_is_refused_before_any_data_subscription(monkeypatch):
    algorithm = cloud_algorithm(monkeypatch, live=True)
    with pytest.raises(RuntimeError, match="refuses every live"):
        algorithm.initialize()
    assert algorithm.subscriptions == [] and algorithm.logs == []


@pytest.mark.parametrize("failure", ["filled", "unfinished", "gap", "orders"])
def test_cloud_host_cannot_certify_fabricated_data_incomplete_coverage_or_orders(monkeypatch, failure):
    algorithm = cloud_algorithm(monkeypatch, orders=[object()] if failure == "orders" else [])
    algorithm.initialize()
    with pytest.raises((ValueError, RuntimeError)):
        if failure == "gap":
            run_bars(algorithm, daily_bars()[:-1])
        else:
            run_bars(algorithm, fill_forward=failure == "filled", unfinished=failure == "unfinished")
        algorithm.on_end_of_algorithm()
    assert not any(line.startswith("ASTRAL_QC|E|") for line in algorithm.logs)
