"""Protect in-cloud parity, aggregate-only diagnostics and the zero-order boundary."""
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal, localcontext
import json
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


def run_bars(algorithm, rows=None, *, fill_forward=False, unfinished=False, bar_zone=None, clock_zone=None):
    for day, values in rows or daily_bars():
        opening, high, low, close, volume = values
        start = datetime.combine(day, time())
        end = start + timedelta(days=1)
        algorithm.utc_time = start if unfinished else end
        if clock_zone:
            algorithm.utc_time = algorithm.utc_time.replace(tzinfo=timezone.utc).astimezone(clock_zone)
        if bar_zone:
            start = start.replace(tzinfo=timezone.utc).astimezone(bar_zone)
            end = end.replace(tzinfo=timezone.utc).astimezone(bar_zone)
        bar = SimpleNamespace(time=start, end_time=end, open=opening, high=high, low=low,
                              close=close, volume=volume, is_fill_forward=fill_forward)
        algorithm.on_data(SimpleNamespace(bars={"BTCUSD": bar}))


@pytest.mark.parametrize("boundary", ["prior-high", "slow-mean"], ids=["equal-breakout-holds", "equal-slow-mean-holds"])
def test_exact_threshold_equality_does_not_create_entry_or_exit(boundary):
    window = [(Decimal(i + 102), Decimal(i + 98), Decimal(i + 100)) for i in range(60)]
    if boundary == "prior-high":
        high, low, close = window[-2]
        window[-2] = (window[-1][2], low, close)
    else:
        window = [(Decimal(102), Decimal(98), Decimal(100))] * 60
    assert evaluate(window)["signal"] == "hold"


def complete_log(monkeypatch, mutate=None):
    algorithm = cloud_algorithm(monkeypatch)
    algorithm.initialize()
    run_bars(algorithm)
    algorithm.on_end_of_algorithm()
    records = list(algorithm.logs)
    if mutate:
        summary = json.loads(records[-1].split("|R|", 1)[1])
        mutate(summary)
        records[-1] = "ASTRAL_QC|R|" + json.dumps(summary)
    return "\n".join(records)


def test_packaged_comparison_agrees_on_all_states_without_exporting_market_data(monkeypatch):
    text = complete_log(monkeypatch)
    result = comparison.compare(text, origin="local-fixture")
    assert result["status"] == "pass" and result["bars"] == 181 and result["signals"] == 131
    assert all(result["signal_counts"].values())
    assert result["orders"] == 0 and not result["profitability_evaluated"]
    assert result["evidence_origin"] == "local-fixture"
    assert len(text.splitlines()) == 2
    summary = json.loads(text.split("|R|", 1)[1])
    assert set(summary) == {"bars", "signals", "orders", "mismatched_signals", "signal_counts", "max_absolute_errors"}
    assert not any("ASTRAL_QC|" + tag + "|" in text for tag in ("B", "S", "E"))


@pytest.mark.parametrize('bar_zone,clock_zone', [
    pytest.param(None, timezone.utc, id='lean-naive-bars-aware-clock'),
    pytest.param(timezone.utc, None, id='aware-bars-naive-clock'),
    pytest.param(timezone(timedelta(hours=2)), timezone.utc, id='equivalent-offset-bars'),
])
def test_cloud_timestamp_representations_preserve_completed_utc_coverage(monkeypatch, bar_zone, clock_zone):
    algorithm = cloud_algorithm(monkeypatch)
    algorithm.initialize()
    run_bars(algorithm, bar_zone=bar_zone, clock_zone=clock_zone)
    algorithm.on_end_of_algorithm()
    result = comparison.compare('\n'.join(algorithm.logs), origin='local-fixture')
    assert result['status'] == 'pass' and result['bars'] == 181 and result['signals'] == 131
    assert result['orders'] == 0


def test_timezone_normalization_cannot_admit_non_midnight_utc_bars(monkeypatch):
    algorithm = cloud_algorithm(monkeypatch)
    algorithm.initialize()
    start = datetime.combine(START, time(), tzinfo=timezone(timedelta(hours=-4)))
    end = start + timedelta(days=1)
    algorithm.utc_time = end.astimezone(timezone.utc)
    bar = SimpleNamespace(time=start, end_time=end, open=1, high=2, low=1, close=2,
                          volume=100, is_fill_forward=False)
    with pytest.raises(ValueError, match='daily UTC'):
        algorithm.on_data(SimpleNamespace(bars={'BTCUSD':bar}))


def test_delivery_boundary_bars_are_excluded_without_replacing_missing_coverage(monkeypatch):
    algorithm = cloud_algorithm(monkeypatch)
    algorithm.initialize()
    rows = daily_bars()
    run_bars(algorithm, [(START - timedelta(days=1), rows[0][1]), *rows, (END, rows[-1][1])],
             clock_zone=timezone.utc)
    algorithm.on_end_of_algorithm()
    result = comparison.compare('\n'.join(algorithm.logs), origin='local-fixture')
    assert result['status'] == 'pass' and result['bars'] == 181 and result['signals'] == 131
    missing = cloud_algorithm(monkeypatch)
    missing.initialize()
    with pytest.raises(ValueError, match='Missing first historical day'):
        run_bars(missing, rows[1:], clock_zone=timezone.utc)


def test_rolling_window_matches_frozen_oracle_and_future_data_cannot_change_prior_signals():
    rows = daily_bars()
    rows[0][1][1] += 10000
    windows = [[(v[1], v[2], v[3]) for _, v in rows[max(0, end-90):end]] for end in range(51, 182)]
    before = [evaluate(window) for window in windows]
    assert before == [price_signal(window) for window in windows]
    rows[-1][1][1] += 1000
    after = [evaluate([(v[1], v[2], v[3]) for _, v in rows[max(0, end-90):end]]) for end in range(51, 182)]
    assert before[:-1] == after[:-1]
    assert before[-1] != after[-1]


@pytest.mark.parametrize("field", ["atr", "signal"])
def test_cloud_summary_retains_detected_implementation_drift(monkeypatch, field):
    algorithm = cloud_algorithm(monkeypatch)
    original = algorithm.on_data.__globals__["evaluate"]
    def changed(window):
        result = original(window)
        with localcontext() as context:
            context.prec = 50
            result[field] = result[field] + 1 if field == "atr" else "hold"
        return result
    algorithm.on_data.__globals__["evaluate"] = changed
    algorithm.initialize()
    run_bars(algorithm)
    algorithm.on_end_of_algorithm()
    result = comparison.compare("\n".join(algorithm.logs))
    assert result["status"] == "mismatch" and result["mismatched_signals"] > 0
    if field == "atr": assert Decimal(result["max_absolute_errors"][field]) == 1


@pytest.mark.parametrize("condition", ["missing-header", "wrong-bundle", "wrong-venue", "missing-result", "duplicate-result", "raw-record", "bars", "signals", "orders", "boolean", "negative", "counts", "nan", "inconsistent", "extra-market-data"])
def test_incomplete_raw_or_invalid_aggregate_evidence_cannot_pass(monkeypatch, condition):
    lines = complete_log(monkeypatch).splitlines()
    summary = json.loads(lines[-1].split("|R|", 1)[1])
    if condition == "missing-header": lines.pop(0)
    elif condition == "wrong-bundle": lines[0] += "altered"
    elif condition == "wrong-venue": lines[0] = lines[0].replace("coinbase", "alpaca")
    elif condition == "missing-result": lines.pop()
    elif condition == "duplicate-result": lines.append(lines[-1])
    elif condition == "raw-record": lines.insert(1, "ASTRAL_QC|B|2025-01-01|1|2|1|2|100")
    else:
        if condition in {"bars", "signals", "orders"}: summary[condition] += 1
        elif condition == "boolean": summary["orders"] = False
        elif condition == "negative": summary["mismatched_signals"] = -1
        elif condition == "counts": summary["signal_counts"]["hold"] += 1
        elif condition == "nan": summary["max_absolute_errors"]["atr"] = "NaN"
        elif condition == "inconsistent": summary["max_absolute_errors"]["atr"] = "1"
        elif condition == "extra-market-data": summary["prices"] = [1, 2]
        lines[-1] = "ASTRAL_QC|R|" + json.dumps(summary)
    with pytest.raises((ValueError, ArithmeticError)):
        comparison.compare("\n".join(lines))


def test_live_mode_is_refused_before_any_data_subscription(monkeypatch):
    algorithm = cloud_algorithm(monkeypatch, live=True)
    with pytest.raises(RuntimeError, match="refuses every live"):
        algorithm.initialize()
    assert algorithm.subscriptions == [] and algorithm.logs == []


@pytest.mark.parametrize("failure", ["filled", "unfinished", "unfinished-aware-clock", "gap", "orders", "nan", "duplicate", "range", "out-of-period"])
def test_cloud_host_cannot_complete_invalid_coverage_or_nonzero_orders(monkeypatch, failure):
    algorithm = cloud_algorithm(monkeypatch, orders=[object()] if failure == "orders" else [])
    algorithm.initialize()
    rows = daily_bars()
    if failure == "gap": rows.pop(12)
    elif failure == "nan": rows[0][1][0] = Decimal("NaN")
    elif failure == "duplicate": rows.insert(1, rows[0])
    elif failure == "range": rows[0][1][0] = Decimal(1)
    elif failure == "out-of-period": rows[0] = (START - timedelta(days=1), rows[0][1])
    with pytest.raises((ValueError, RuntimeError)):
        run_bars(algorithm, rows, fill_forward=failure == "filled", unfinished=failure.startswith("unfinished"),
                 clock_zone=timezone.utc if failure == "unfinished-aware-clock" else None)
        algorithm.on_end_of_algorithm()
    assert not any(line.startswith("ASTRAL_QC|R|") for line in algorithm.logs)
