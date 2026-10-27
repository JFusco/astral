"""Bounded observation of existing accounting, independent of trading readiness."""
import asyncio
from collections import Counter
import json
import math
import shutil
import time
import uuid

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
    def __init__(self, prepared, *, clock=None):
        self.prepared = prepared
        self.clock = clock or time.monotonic
        self.started = None
        self.ended = None
        self.status = 'prepared'
        self.reason = None
        self.cycles = self.complete = self.matched = self.received_bytes = self.request_units = 0
        self.issues = Counter()
        self.availability = Counter()
        self.latencies = {k: Latency() for k in ('acquisition', 'publication', 'state')}
        self.last_success = self.last_success_at = None
        self.max_gap = 0
        self.started_at = None
        self.run_id = uuid.uuid4().hex

    @property
    def remaining(self):
        return max(0, DAY-(self.clock()-self.started)) if self.started is not None else 0

    @property
    def active(self):
        return self.status == 'observing' and self.remaining > 0

    def summary(self):
        end = self.ended if self.ended is not None else self.clock()
        gap = end-(self.last_success if self.last_success is not None else self.started) if self.started is not None else 0
        return {'status': 'expired' if self.status == 'observing' and not self.remaining else self.status,
                'reason': self.reason, 'started_at': self.started_at, 'duration_seconds': DAY,
                'elapsed_seconds': round(end-self.started, 3) if self.started is not None else 0,
                'cycles': self.cycles, 'complete_acquisitions': self.complete, 'matched_publications': self.matched,
                'received_bytes': self.received_bytes, 'request_budget_units': self.request_units,
                'max_acquisition_gap_seconds': round(max(self.max_gap, gap), 3), 'last_success_at': self.last_success_at,
                'blocked_reasons': dict(self.issues), 'latency': {k:v.view() for k,v in self.latencies.items()},
                'availability_samples': dict(self.availability),
                'growth_bytes': max(0, ledger_bytes(self.prepared.ledger)-self.prepared.initial_bytes),
                'current_accounting_is_separate': True, 'operational_acceptance': 'owner-review-required',
                'reader_enabled': self.active, 'orders_enabled': False}

    def persist(self, store):
        store.put('activity_rollout_observation', self.summary())

    def stop(self, store, reason):
        if self.status != 'observing':
            return
        self.status, self.reason = 'stopped', reason
        self.ended = self.clock()
        self.persist(store)
        store.event('activity_rollout_stopped', {'run_id': self.run_id, **self.summary()})

    def budget_ok(self):
        return (ledger_bytes(self.prepared.ledger)-self.prepared.initial_bytes < MAX_GROWTH
                and shutil.disk_usage(self.prepared.ledger.parent).free >= MIN_FREE)

    async def acquire(self, engine):
        if not self.active:
            raise ValueError('Accounting observation is inactive')
        started = time.monotonic()
        # Snapshot and publication share the existing reconciliation lock. This
        # never extends the actual stream cutoff to cover a later snapshot.
        async with engine.lock:
            if not self.active:
                raise ValueError('Accounting observation deadline reached')
            engine.broker._last_activity_acquisition = None
            try:
                batch, receipt = await collect_batch(engine.broker, engine.store, critical=False, refresh_snapshot=True)
            finally:
                self.latencies['acquisition'].add((time.monotonic()-started)*1000)
                retained = engine.broker._last_activity_acquisition or {}
                self.received_bytes += len(retained.get('raw', b''))
                self.request_units += retained.get('request_attempts', 0)
            if not self.budget_ok():
                self.stop(engine.store, 'storage_budget_exceeded')
                raise ValueError('Storage budget exceeded; acquisition retained without publication')
            if not self.active:
                raise ValueError('Accounting observation deadline reached; acquisition retained without publication')
            if receipt.get('complete'):
                now = self.clock()
                self.max_gap = max(self.max_gap, now-(self.last_success if self.last_success is not None else self.started))
                self.last_success, self.last_success_at = now, receipt['received_at']
                self.complete += 1
            published = time.monotonic()
            result = publish_projection(engine.store, batch, json.loads(self.prepared.mapping_json))
            self.latencies['publication'].add((time.monotonic()-published)*1000)
            self.matched += not result['issues']
            self.issues.update(result['issues'])
            return result

    async def run(self, engine):
        self.prepared.validate_ledger()
        previous = engine.store.get('activity_rollout_observation')
        if previous:
            engine.store.event('activity_rollout_previous', previous)
        self.started, self.started_at, self.status = self.clock(), utcnow(), 'observing'
        engine.store.event('activity_rollout_started', {'run_id': self.run_id, 'mapping_sha256': self.prepared.mapping_sha256,
                                                     'duration_seconds': DAY})
        self.persist(engine.store)
        try:
            while self.active:
                if not self.budget_ok():
                    self.stop(engine.store, 'storage_budget_exceeded')
                    break
                self.cycles += 1
                try:
                    async with asyncio.timeout(self.remaining):
                        result = await engine.refresh_activity_feed()
                    engine.worker('fees', 'blocked' if result['issues'] else 'healthy',
                                  'Accounting evidence requires review' if result['issues'] else 'Validated accounting acquisition')
                except TimeoutError:
                    self.stop(engine.store, 'observation_deadline')
                    break
                except Exception:
                    self.issues['acquisition_or_publication_failed'] += 1
                    engine.worker('fees', 'error', 'Accounting acquisition failed; retained evidence blocks readiness')
                self.coverage(engine.store)
                self.persist(engine.store)
                await asyncio.sleep(min(60, self.remaining))
        finally:
            self.stop(engine.store, 'observation_deadline' if not self.remaining else 'observation_interrupted')
            engine.worker('fees', 'disabled', 'Observation stopped; accounting reader disabled')

    def coverage(self, store):
        """Sample current availability without treating it as collection success."""
        value = current_accounting(store, enabled=self.active)
        self.availability[value['activity_coverage']['status']] += 1
        return {'activity_coverage': value['activity_coverage'],
                'accounting_by_symbol': value['accounting_by_symbol']}
