"""Bounded diagnostics; no credentials, response data or exception messages."""
from contextlib import contextmanager
from contextvars import ContextVar
import os
import sqlite3
import time

from .store import utcnow

ACTIVE = ContextVar('activity_diagnostics', default=None)
PATHS = {'/v2/account', '/v2/positions', '/v2/clock', '/v2beta1/events/activities'}
REQUEST_PATHS = PATHS | {'/v2/orders', '/v2/orders:by_client_order_id', '/v1beta1/news',
                        '/v2/stocks/quotes/latest', '/v1beta3/crypto/us/latest/quotes',
                        '/v1beta3/crypto/us/latest/orderbooks'}
ERRORS = {'ConnectTimeout', 'ReadTimeout', 'WriteTimeout', 'PoolTimeout', 'ConnectError',
          'ReadError', 'WriteError', 'RemoteProtocolError', 'LocalProtocolError', 'DecodingError',
          'HTTPStatusError', 'TimeoutError', 'CancelledError', 'JSONDecodeError', 'ValueError',
          'BrokerFailure', 'OwnershipError', 'FeedError', 'SnapshotCommitError'}
PHASES = ('connection.connect_tcp', 'connection.start_tls', 'http11.send_request_headers',
          'http11.send_request_body', 'http11.receive_response_headers',
          'http11.receive_response_body', 'http11.response_closed')
MARKS = ('attempt_start', 'lock_wait_start', 'lock_acquired', 'collection_start',
         'retention_start', 'retention_end', 'collection_end', 'completion',
         'publication_start', 'publication_end', 'sample_start', 'sample_end',
         'lock_released', 'attempt_finish')


class DiagnosticStorageError(RuntimeError):
    """A tagged ledger failure, distinct from network OSError and invalid evidence."""


def failure_kind(exc):
    """Prefer the outer failure over its cause, skipping generic wrappers."""
    chain, seen = [], set()
    while exc is not None and id(exc) not in seen and len(chain) < 8:
        seen.add(id(exc))
        name = type(exc).__name__
        chain.append('storage' if isinstance(exc, (DiagnosticStorageError, sqlite3.Error))
                     else name if name in ERRORS else 'unclassified')
        exc = exc.__cause__
    for name in chain:
        if name not in {'BrokerFailure', 'FeedError', 'ValueError', 'OwnershipError', 'unclassified'}:
            return name
    return next((name for name in chain if name != 'unclassified'), 'unclassified')


def ledger_write(operation, *args, lifecycle=None):
    """Stop an observer at the failing write; never retry or salvage after a latch."""
    trace = ACTIVE.get()
    lifecycle = lifecycle or (trace.lifecycle if trace else None)
    if lifecycle and lifecycle.observation.storage_failed:
        raise DiagnosticStorageError('Accounting diagnostic storage unavailable')
    try:
        return operation(*args)
    except (sqlite3.Error, OSError) as exc:
        if lifecycle:
            lifecycle.observation.storage_stop()
            raise DiagnosticStorageError('Accounting diagnostic storage unavailable') from exc
        raise


def interval(before, after):
    from datetime import datetime
    return {'monotonic_seconds': round(after['monotonic_seconds']-before['monotonic_seconds'], 6),
            'wall_seconds': round((datetime.fromisoformat(after['wall_at'])-
                                   datetime.fromisoformat(before['wall_at'])).total_seconds(), 6)}


class Attempt:
    def __init__(self, observation, sequence, identity):
        self.observation, self.sequence, self.identity = observation, sequence, identity
        self.marks = dict.fromkeys(MARKS)
        self.batch_started = self.outcome_retained = self.acquisition_counted = False
        self.publication = 'not-started'
        self.terminal, self.failure = 'running', None
        self.trace = None
        self.lag = {'samples': 0, 'max_ms': 0, 'scheduled': None, 'observed': None}
        self.mark('attempt_start')

    def mark(self, name):
        if name not in MARKS:
            raise ValueError('Unknown accounting diagnostic boundary')
        self.marks[name] = self.observation.sample()

    def identity_view(self):
        return {'run_id': self.observation.run_id, 'process_id': os.getpid(),
                'sequence': self.sequence, 'attempt_id': self.identity}

    def view(self):
        return {**self.identity_view(), 'boundaries': dict(self.marks),
                'batch_started': self.batch_started, 'outcome_retained': self.outcome_retained,
                'acquisition_counted': self.acquisition_counted, 'publication': self.publication,
                'terminal': self.terminal, 'failure_kind': self.failure,
                'not_started_reason': None if self.batch_started else self.terminal,
                'not_published_reason': None if self.publication == 'published' else self.terminal,
                'loop_lag': dict(self.lag), 'acquisition': self.trace.view() if self.trace else None}


class AcquisitionTrace:
    def __init__(self, batch, lifecycle=None):
        self.batch, self.stage, self.requests = batch, 'initializing', []
        self.failure, self.lifecycle = None, lifecycle
        self.origin = time.monotonic()
        if lifecycle:
            lifecycle.trace = self

    def sample(self):
        return self.lifecycle.observation.sample() if self.lifecycle else {
            'monotonic_seconds': round(time.monotonic()-self.origin, 6), 'wall_at': utcnow()}

    def view(self):
        failed = next((r for r in self.requests if r['failure_kind']), None)
        return {'batch': self.batch, 'process_id': os.getpid(),
                'run_id': self.lifecycle.observation.run_id if self.lifecycle else self.batch,
                'stage': self.stage,
                'failure_stage': failed['stage'] if failed else self.stage if self.failure else None,
                'failure_kind': self.failure or (failed['failure_kind'] if failed else None),
                'requests': [span_view(r) for r in self.requests]}


def classify(receipt, exc):
    receipt['failure_kind'] = failure_kind(exc)
    if receipt['failure_kind'] == 'storage':
        locus = 'storage'
    elif receipt.get('denial'):
        locus = receipt['denial']
    elif receipt['failure_kind'] in {'TimeoutError', 'CancelledError'}:
        locus = 'deadline/cancellation'
    elif receipt.get('http_status') is not None and receipt['http_status'] >= 300:
        locus = 'observed-provider-status'
    elif receipt['failure_kind'] in {'ConnectTimeout', 'ReadTimeout', 'WriteTimeout', 'PoolTimeout',
                                    'ConnectError', 'ReadError', 'WriteError', 'RemoteProtocolError',
                                    'LocalProtocolError', 'DecodingError'}:
        locus = 'transport-after-headers' if receipt.get('http_status') is not None else 'transport-before-observed-headers'
    else:
        locus = 'unclassified'
    receipt['failure_locus'] = locus


def span_view(receipt):
    return {key: value for key, value in receipt.items() if not key.startswith('_')}


def trace_extensions(receipt, extensions=None):
    """HTTPCore requires a coroutine callback, including when it does no awaits."""
    if '_sample' not in receipt:
        return extensions or {}

    async def trace(name, info):
        # Never inspect info: headers, request objects and exceptions can be private.
        try:
            phase, state = name.rsplit('.', 1)
            if phase not in PHASES or state not in {'started', 'complete', 'failed'}:
                return
            sample = receipt['_sample']()
            summary = receipt['phases'][phase]
            if receipt['pre_trace_ms'] is None:
                receipt['pre_trace_ms'] = round((sample['monotonic_seconds']-
                                                receipt['started_clock']['monotonic_seconds'])*1000, 3)
            if state == 'started':
                summary['started'] = summary['started'] or sample
                summary['count'] += 1
            else:
                summary['ended'] = sample
            summary['state'] = state
        except Exception:
            receipt['tracing_unavailable'] = True

    return {**(extensions or {}), 'trace': trace}


@contextmanager
def request_span(method, path):
    trace = ACTIVE.get()
    started = time.monotonic()
    receipt = {'dispatch': 'not-started', 'http_status': None, 'failure_kind': None,
               'failure_locus': None, 'denial': None,
               'method': method if method in {'GET', 'POST', 'DELETE'} else 'unknown',
               'path': path if path in REQUEST_PATHS else 'unknown'}
    if trace:
        if method != 'GET' or path not in PATHS or len(trace.requests) >= 7:
            raise ValueError('Acquisition diagnostic request boundary differs')
        receipt.update(stage=trace.stage, started_clock=trace.sample(), ended_clock=None,
                       phases={phase: {'state': 'not-observed', 'count': 0, 'started': None, 'ended': None}
                               for phase in PHASES}, pre_trace_ms=None, tracing_unavailable=False,
                       _sample=trace.sample)
        receipt['started_at'] = receipt['started_clock']['wall_at']
        trace.requests.append(receipt)
    try:
        yield receipt
    except BaseException as exc:
        classify(receipt, exc)
        raise
    finally:
        receipt['elapsed_ms'] = round((time.monotonic()-started)*1000, 3)
        if trace:
            receipt['ended_clock'] = trace.sample()
            receipt['ended_at'] = receipt['ended_clock']['wall_at']
