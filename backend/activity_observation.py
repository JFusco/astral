"""Bounded observation of existing accounting, independent of trading readiness."""
import asyncio
from collections import Counter
from datetime import datetime, timedelta
import json
import math
import os
import shutil
import sqlite3
import time
import uuid

from .activity_diagnostics import Attempt, DiagnosticStorageError, failure_kind, interval
from .activity_feed import collect_batch, current_accounting, publish_projection
from .activity_rollout import DAY, MAX_GROWTH, MIN_FREE, ledger_bytes
from .store import utcnow


class Latency:
    """Fixed-size histogram retains every observation without per-request rows."""
    bounds = (5, 10, 25, 50, 100, 250, 500, 1000, 2000, 5000)

    def __init__(self):
        self.counts = [0] * (len(self.bounds)+1)

    def add(self, milliseconds):
        self.counts[next((i for i, b in enumerate(self.bounds) if milliseconds <= b), len(self.bounds))] += 1

    def view(self):
        count = sum(self.counts)
        total = 0
        for i, value in enumerate(self.counts):
            total += value
            if count and total >= math.ceil(count*.95):
                return {'samples': count, 'p95_upper_ms': self.bounds[i] if i < len(self.bounds) else None,
                        'over_5000_ms': self.counts[-1]}
        return {'samples': 0, 'p95_upper_ms': None, 'over_5000_ms': 0}


class Observation:
    def __init__(self, prepared, *, clock=None, wall_clock=None):
        self.prepared = prepared
        self.clock, self.wall_clock = clock or time.monotonic, wall_clock or utcnow
        self.started = self.ended = None
        self.status, self.reason = 'prepared', None
        self.cycles = self.complete = self.matched = self.received_bytes = self.request_units = 0
        self.issues, self.availability = Counter(), Counter()
        self.latencies = {k: Latency() for k in ('acquisition', 'publication', 'state', 'lock_wait', 'scheduling_delay', 'event_loop_lag', 'acquisition_execution')}
        self.latest_diagnostics = None
        self.publication_availability = Counter()
        self.last_success = self.last_success_at = None
        self.max_gap, self.started_at = 0, None
        self.run_id, self._lag_handle = uuid.uuid4().hex, None
        self._cycle = self._sleep_lag = None
        self.storage_failed = False
        self.start_clock = self.end_clock = self.last_completion = self.completion_interval = None
        self.max_clock_gap = {'monotonic_seconds': 0, 'wall_seconds': 0}

    def sample(self, monotonic=None):
        now = self.clock() if monotonic is None else monotonic
        return {'monotonic_seconds': round(now-(self.started if self.started is not None else now), 6),
                'wall_at': self.wall_clock()}

    @property
    def remaining(self):
        return max(0, DAY-(self.clock()-self.started)) if self.started is not None else 0

    @property
    def active(self):
        return self.status == 'observing' and self.remaining > 0

    def summary(self):
        end = self.ended if self.ended is not None else self.clock()
        gap = end-(self.last_success if self.last_success is not None else self.started) if self.started is not None else 0
        edge = self.end_clock or (self.sample() if self.start_clock else None)
        previous = self.last_completion or self.start_clock
        tail = interval(previous, edge) if previous and edge else None
        return {'status': 'expired' if self.status == 'observing' and not self.remaining else self.status,
                'reason': self.reason, 'started_at': self.started_at, 'duration_seconds': DAY,
                'elapsed_seconds': round(end-self.started, 3) if self.started is not None else 0,
                'cycles': self.cycles, 'complete_acquisitions': self.complete, 'matched_publications': self.matched,
                'received_bytes': self.received_bytes, 'request_budget_units': self.request_units,
                'max_acquisition_gap_seconds': round(max(self.max_gap, gap), 3), 'last_success_at': self.last_success_at,
                'blocked_reasons': dict(self.issues), 'latency': {k:v.view() for k,v in self.latencies.items()},
                'availability_samples': dict(self.availability),
                'publication_availability_samples': dict(self.publication_availability), 'latest_diagnostics': self.latest_diagnostics,
                'growth_bytes': max(0, ledger_bytes(self.prepared.ledger)-self.prepared.initial_bytes),
                'current_accounting_is_separate': True, 'operational_acceptance': 'owner-review-required',
                'reader_enabled': self.active, 'orders_enabled': False,
                'clock_diagnostics': {'run_id': self.run_id, 'process_id': os.getpid(),
                    'start': self.start_clock, 'end': self.end_clock, 'last_completion': self.last_completion,
                    'last_completion_interval': self.completion_interval, 'tail': tail,
                    'max_completion_interval': dict(self.max_clock_gap),
                    'wall_elapsed_seconds': interval(self.start_clock, edge)['wall_seconds'] if self.start_clock and edge else None},
                'diagnostic_storage_failed': self.storage_failed}

    def storage_stop(self):
        """Disable authority before any attempted persistence of a storage failure."""
        if self.storage_failed:
            return
        self.storage_failed = True
        self.status, self.reason, self.ended = 'stopped', 'diagnostic_storage_failed', self.clock()
        self.end_clock = self.sample(self.ended)
        if self._cycle:
            self._cycle.failure, self._cycle.terminal = 'storage', 'storage'
        self.latest_diagnostics = {**(self.latest_diagnostics or {}), 'failure_kind': 'storage',
                                   'missing_evidence': True}

    def write(self, operation, *args):
        if self.storage_failed:
            raise DiagnosticStorageError('Accounting diagnostic storage unavailable')
        try:
            return operation(*args)
        except (sqlite3.Error, OSError) as exc:
            self.storage_stop()
            raise DiagnosticStorageError('Accounting diagnostic storage unavailable') from exc

    def persist(self, store):
        self.write(store.put, 'activity_rollout_observation', self.summary())

    def stop(self, store, reason):
        if self.status != 'observing':
            return
        self.status, self.reason, self.ended = 'stopped', reason, self.clock()
        self.end_clock = self.sample(self.ended)
        self.persist(store)
        self.write(store.event, 'activity_rollout_stopped', {'run_id': self.run_id, **self.summary()})

    def budget_ok(self):
        return (ledger_bytes(self.prepared.ledger)-self.prepared.initial_bytes < MAX_GROWTH
                and shutil.disk_usage(self.prepared.ledger.parent).free >= MIN_FREE)

    async def acquire(self, engine):
        if not self.active:
            raise ValueError('Accounting observation is inactive')
        cycle = self._cycle or Attempt(self, None, uuid.uuid4().hex)
        started = time.monotonic()
        cycle.mark('lock_wait_start')
        try:
            async with engine.lock:
                cycle.mark('lock_acquired')
                acquired_lock = time.monotonic()
                lock_wait = (acquired_lock-started)*1000
                self.latencies['lock_wait'].add(lock_wait)
                if not self.active:
                    raise ValueError('Accounting observation deadline reached')
                engine.broker._last_activity_acquisition = None
                cycle.mark('collection_start')
                try:
                    batch, receipt = await collect_batch(engine.broker, engine.store, critical=False,
                        refresh_snapshot=True, batch_id=cycle.identity, lifecycle=cycle)
                finally:
                    self.latencies['acquisition'].add((time.monotonic()-started)*1000)
                    retained = engine.broker._last_activity_acquisition or {}
                    execution_ms = (time.monotonic()-acquired_lock)*1000
                    self.latencies['acquisition_execution'].add(execution_ms)
                    self.latest_diagnostics = {**(retained.get('diagnostics') or {}), 'lock_wait_ms': round(lock_wait, 3),
                                               'acquisition_execution_ms': round(execution_ms, 3)}
                    if self.storage_failed:
                        self.latest_diagnostics.update(failure_kind='storage', missing_evidence=True)
                    self.received_bytes += len(retained.get('raw', b''))
                    self.request_units += retained.get('request_attempts', 0)
                    cycle.mark('collection_end')
                if not self.budget_ok():
                    cycle.publication = 'prevented-storage-budget'
                    self.stop(engine.store, 'storage_budget_exceeded')
                    raise ValueError('Storage budget exceeded; acquisition retained without publication')
                if not self.active:
                    cycle.publication = 'prevented-inactive'
                    raise ValueError('Accounting observation deadline reached; acquisition retained without publication')
                if receipt.get('complete'):
                    now = self.clock()
                    self.max_gap = max(self.max_gap, now-(self.last_success if self.last_success is not None else self.started))
                    self.last_success, self.last_success_at = now, receipt['received_at']
                    self.complete += 1
                    cycle.acquisition_counted = True
                    completion = self.sample(now)
                    cycle.marks['completion'] = completion
                    if self.start_clock:
                        self.completion_interval = interval(self.last_completion or self.start_clock, completion)
                        for clock, value in self.completion_interval.items():
                            self.max_clock_gap[clock] = max(self.max_clock_gap[clock], value)
                    self.last_completion = completion
                published = time.monotonic()
                cycle.mark('publication_start')
                cycle.publication = 'failed'
                result = self.write(publish_projection, engine.store, batch, json.loads(self.prepared.mapping_json))
                cycle.publication = 'published'
                cycle.mark('publication_end')
                self.latencies['publication'].add((time.monotonic()-published)*1000)
                self.matched += not result['issues']
                self.issues.update(result['issues'])
                cycle.mark('sample_start')
                self.publication_availability[self.coverage(engine.store, record=False)['activity_coverage']['status']] += 1
                cycle.mark('sample_end')
                return result
        finally:
            if cycle.marks['lock_acquired']:
                cycle.mark('lock_released')

    def start_lag_probe(self, loop):
        def schedule():
            expected, sample = loop.time()+1, self.sample()
            self._lag_handle = loop.call_later(1, tick, expected, sample)

        def tick(expected, scheduled):
            if self.active:
                lag = max(0, loop.time()-expected)*1000
                self.latencies['event_loop_lag'].add(lag)
                summary = self._cycle.lag if self._cycle else self._sleep_lag
                if summary is not None:
                    summary.update(samples=summary['samples']+1, max_ms=max(summary['max_ms'], round(lag, 3)),
                                   scheduled=scheduled, observed=self.sample())
                schedule()
        schedule()

    def recover(self, store):
        """Annotate prior incomplete lifecycles without changing accounting rows."""
        after = 0
        while True:
            rows = store.rows("""SELECT s.seq,s.payload FROM events s
                WHERE s.type='activity_attempt_started' AND s.seq>?
                AND NOT EXISTS (SELECT 1 FROM events e
                    WHERE e.type IN ('activity_attempt_finished','activity_attempt_abandoned')
                    AND e.seq > s.seq
                    AND CASE WHEN json_valid(e.payload) THEN json_extract(e.payload,'$.run_id') END
                        = CASE WHEN json_valid(s.payload) THEN json_extract(s.payload,'$.run_id') END
                    AND CASE WHEN json_valid(e.payload) THEN json_extract(e.payload,'$.sequence') END
                        = CASE WHEN json_valid(s.payload) THEN json_extract(s.payload,'$.sequence') END
                    AND CASE WHEN json_valid(e.payload) THEN json_extract(e.payload,'$.attempt_id') END
                        = CASE WHEN json_valid(s.payload) THEN json_extract(s.payload,'$.attempt_id') END)
                ORDER BY s.seq LIMIT 100""", (after,))
            if not rows:
                return
            for row in rows:
                value = json.loads(row['payload'])
                identity = {key: value[key] for key in ('run_id', 'process_id', 'sequence', 'attempt_id')}
                valid_ids = all(isinstance(identity[key], str) and len(identity[key]) == 32
                                and all(c in '0123456789abcdef' for c in identity[key])
                                for key in ('run_id', 'attempt_id'))
                valid_numbers = all(type(identity[key]) is int and 0 < identity[key] < 2**63
                                    for key in ('sequence', 'process_id'))
                if not valid_ids or not valid_numbers:
                    raise ValueError('Accounting diagnostic identity unavailable')
                self.write(store.event, 'activity_attempt_abandoned', {**identity, 'recovered_by': self.run_id,
                    'reason': 'missing-finish', 'recovered_at': self.wall_clock()})
                after = row['seq']

    async def attempt(self, engine):
        self.cycles += 1
        cycle = self._cycle = Attempt(self, self.cycles, uuid.uuid4().hex)
        self.latest_diagnostics = {'cycle': cycle.view()}
        cancelled = False
        try:
            self.write(engine.store.event, 'activity_attempt_started',
                       {**cycle.identity_view(), 'clock': cycle.marks['attempt_start']})
            async with asyncio.timeout(self.remaining):
                result = await engine.refresh_activity_feed()
            cycle.terminal = 'completed' if cycle.acquisition_counted else 'failed'
            cycle.failure = cycle.trace.view()['failure_kind'] if cycle.trace else None
            engine.worker('fees', 'blocked' if result['issues'] else 'healthy',
                          'Accounting evidence requires review' if result['issues'] else 'Validated accounting acquisition')
        except DiagnosticStorageError:
            cycle.terminal, cycle.failure = 'storage', 'storage'
            raise
        except TimeoutError:
            cycle.terminal, cycle.failure = 'deadline', 'TimeoutError'
            raise
        except asyncio.CancelledError:
            cancelled = True
            cycle.terminal, cycle.failure = 'cancelled', 'CancelledError'
            raise
        except Exception as exc:
            cycle.terminal, cycle.failure = 'failed', failure_kind(exc)
            self.issues['acquisition_or_publication_failed'] += 1
            engine.worker('fees', 'error', 'Accounting acquisition failed; retained evidence blocks readiness')
        finally:
            cycle.mark('attempt_finish')
            self.latest_diagnostics = {**(self.latest_diagnostics or {}), 'cycle': cycle.view()}
            try:
                if not self.storage_failed:
                    try:
                        self.write(engine.store.event, 'activity_attempt_finished', cycle.view())
                    except DiagnosticStorageError:
                        if not cancelled:
                            raise
            finally:
                self._cycle = None

    async def sleep(self, store):
        delay = min(60, self.remaining)
        scheduled = self.sample()
        identity = {'run_id': self.run_id, 'process_id': os.getpid(), 'sequence': self.cycles}
        planned_wake = {'monotonic_seconds': scheduled['monotonic_seconds']+delay,
                        'wall_at': (datetime.fromisoformat(scheduled['wall_at'])+timedelta(seconds=delay)).isoformat()}
        self.write(store.event, 'activity_observation_sleep_started',
                   {**identity, 'clock': scheduled, 'intended_seconds': delay, 'scheduled_wake': planned_wake})
        entered = self.sample()
        wake_at = {'monotonic_seconds': entered['monotonic_seconds']+delay,
                   'wall_at': (datetime.fromisoformat(entered['wall_at'])+timedelta(seconds=delay)).isoformat()}
        due = self.clock()+delay
        self._sleep_lag = {'samples': 0, 'max_ms': 0, 'scheduled': None, 'observed': None}
        result = 'interrupted'
        cancelled = False
        try:
            await asyncio.sleep(delay)
            self.latencies['scheduling_delay'].add(max(0, self.clock()-due)*1000)
            result = 'woke'
        except asyncio.CancelledError:
            cancelled = True
            raise
        finally:
            woke = self.sample()
            if not self.storage_failed:
                try:
                    self.write(store.event, 'activity_observation_sleep_finished',
                        {**identity, 'scheduled': scheduled, 'entered': entered, 'scheduled_wake': wake_at,
                         'wake': woke, 'intended_seconds': delay, 'result': result,
                         'diagnostic_write': interval(scheduled, entered), 'wait': interval(entered, woke),
                         'loop_lag': dict(self._sleep_lag)})
                except DiagnosticStorageError:
                    if not cancelled:
                        raise
            self._sleep_lag = None

    async def run(self, engine):
        try:
            try:
                self.prepared.validate_ledger()
            except Exception:
                self.status, self.reason = 'failed', 'ledger_recheck_failed'
                self.write(engine.store.event, 'activity_rollout_failed', {'run_id': self.run_id, 'reason': self.reason})
                engine.worker('fees', 'disabled', 'Ledger recheck failed; accounting reader disabled')
                return
            try:
                self.recover(engine.store)
            except (sqlite3.Error, OSError):
                self.storage_stop()
                return
            except (ValueError, KeyError, TypeError):
                self.status, self.reason = 'failed', 'diagnostic_evidence_invalid'
                self.write(engine.store.event, 'activity_rollout_failed', {'run_id': self.run_id, 'reason': self.reason})
                return
            previous = engine.store.get('activity_rollout_observation')
            if previous:
                self.write(engine.store.event, 'activity_rollout_previous', previous)
            self.started, self.started_at, self.status = self.clock(), self.wall_clock(), 'observing'
            self.start_clock = {'monotonic_seconds': 0, 'wall_at': self.started_at}
            self.write(engine.store.event, 'activity_rollout_started',
                {'run_id': self.run_id, 'mapping_sha256': self.prepared.mapping_sha256,
                 'duration_seconds': DAY, 'process_id': os.getpid(), 'clock': self.start_clock})
            self.persist(engine.store)
            self.start_lag_probe(asyncio.get_running_loop())
            while self.active:
                if not self.budget_ok():
                    self.stop(engine.store, 'storage_budget_exceeded')
                    break
                try:
                    await self.attempt(engine)
                except TimeoutError:
                    self.stop(engine.store, 'observation_deadline')
                    break
                self.persist(engine.store)
                if not self.active:
                    break
                await self.sleep(engine.store)
                if not self.active:
                    break
                self.coverage(engine.store)
                self.persist(engine.store)
        except DiagnosticStorageError:
            pass
        finally:
            if self._lag_handle is not None:
                self._lag_handle.cancel()
            try:
                if not self.storage_failed:
                    self.stop(engine.store, 'observation_deadline' if not self.remaining else 'observation_interrupted')
            except DiagnosticStorageError:
                pass
            engine.worker('fees', 'disabled', 'Observation stopped; accounting reader disabled')

    def coverage(self, store, *, record=True):
        """Sample current availability without treating it as collection success."""
        value = current_accounting(store, enabled=self.active)
        if record:
            self.availability[value['activity_coverage']['status']] += 1
        return {'accounting_evidence': value['accounting_evidence'],
                'activity_coverage': value['activity_coverage'],
                'accounting_by_symbol': value['accounting_by_symbol']}
