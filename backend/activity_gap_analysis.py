"""Pure, conservative interpretation of the reviewed observation record contract."""
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import (Decimal, DecimalException, Inexact, InvalidOperation, Overflow,
                     localcontext)
import re

MARKS = ('attempt_start', 'lock_wait_start', 'lock_acquired', 'collection_start',
         'retention_start', 'retention_end', 'collection_end', 'completion',
         'publication_start', 'publication_end', 'sample_start', 'sample_end',
         'lock_released', 'attempt_finish')
TRANSPORT = {'ConnectTimeout', 'ReadTimeout', 'WriteTimeout', 'PoolTimeout', 'ConnectError',
             'ReadError', 'WriteError', 'RemoteProtocolError', 'LocalProtocolError', 'DecodingError'}
ERRORS = TRANSPORT | {'HTTPStatusError', 'TimeoutError', 'CancelledError', 'JSONDecodeError',
    'ValueError', 'BrokerFailure', 'OwnershipError', 'FeedError', 'SnapshotCommitError', 'storage', 'unclassified'}
PHASES = ('connection.connect_tcp', 'connection.start_tls', 'http11.send_request_headers',
          'http11.send_request_body', 'http11.receive_response_headers',
          'http11.receive_response_body', 'http11.response_closed')
DEFECTS = (ValueError, TypeError, KeyError, RecursionError, DecimalException)
SAT, FAIL, UNKNOWN, NA = 'satisfied', 'not-satisfied', 'unknown', 'not-evaluated'
ZERO = Decimal(0)


@contextmanager
def exact():
    with localcontext() as context:
        context.prec = 64
        context.traps[Inexact] = context.traps[Overflow] = context.traps[InvalidOperation] = True
        yield


def number(value):
    if type(value) not in (int, Decimal) or not Decimal(value).is_finite():
        raise ValueError('invalid-number')
    value = Decimal(value)
    if len(value.as_tuple().digits) > 64 or abs(value.as_tuple().exponent) > 64:
        raise ValueError('unsupported-precision')
    return +value


def integer(value):
    if type(value) is not int or not 0 <= value < 2**63:
        raise ValueError('invalid-counter')
    return value


def identity(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{32}', value) is not None


def legacy_summary(value):
    """Recognize the a6bf6ca summary shape, without attesting provenance or a run."""
    keys = {'status', 'reason', 'started_at', 'duration_seconds', 'elapsed_seconds',
            'cycles', 'complete_acquisitions', 'matched_publications', 'received_bytes',
            'request_budget_units', 'max_acquisition_gap_seconds', 'last_success_at',
            'blocked_reasons', 'latency', 'availability_samples', 'growth_bytes',
            'current_accounting_is_separate', 'operational_acceptance', 'reader_enabled',
            'orders_enabled'}
    if not isinstance(value, dict) or set(value) != keys:
        return False
    if (not isinstance(value['status'], str)
            or value['status'] not in {'prepared', 'observing', 'expired', 'stopped', 'failed'}
            or (value['reason'] is not None and not isinstance(value['reason'], str))
            or type(value['duration_seconds']) is not int or value['duration_seconds'] != 86400
            or value['current_accounting_is_separate'] is not True
            or value['operational_acceptance'] != 'owner-review-required'
            or type(value['reader_enabled']) is not bool or value['orders_enabled'] is not False):
        return False
    for name in ('started_at', 'last_success_at'):
        stamp = value[name]
        if stamp is None:
            continue
        if not isinstance(stamp, str) or not re.fullmatch(
                r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?\+00:00', stamp):
            return False
        try:
            datetime.fromisoformat(stamp)
        except ValueError:
            return False
    for name in ('elapsed_seconds', 'max_acquisition_gap_seconds'):
        amount = value[name]
        # The preflight decoder uses float; the offline report uses Decimal.
        if type(amount) not in (int, float, Decimal) or not Decimal(str(amount)).is_finite() or amount < 0:
            return False
    def counter(amount):
        return type(amount) is int and amount >= 0
    if not all(counter(value[name]) for name in ('cycles', 'complete_acquisitions',
            'matched_publications', 'received_bytes', 'request_budget_units', 'growth_bytes')):
        return False
    for name in ('blocked_reasons', 'availability_samples'):
        counts = value[name]
        # Exact containers and integer leaves exclude identities at every depth.
        if not isinstance(counts, dict) or any(
                not isinstance(key, str) or key in {'run_id', 'recovered_by'} or not counter(amount)
                for key, amount in counts.items()):
            return False
    if not set(value['availability_samples']) <= {'current', 'incomplete'}:
        return False
    latencies = value['latency']
    if not isinstance(latencies, dict) or set(latencies) != {'acquisition', 'publication', 'state'}:
        return False
    for histogram in latencies.values():
        if (not isinstance(histogram, dict)
                or set(histogram) != {'samples', 'p95_upper_ms', 'over_5000_ms'}
                or not counter(histogram['samples']) or not counter(histogram['over_5000_ms'])):
            return False
        upper = histogram['p95_upper_ms']
        if upper is not None and (type(upper) is not int or upper not in (5, 10, 25, 50, 100, 250, 500, 1000, 2000, 5000)):
            return False
    return True


def clock(value):
    if not isinstance(value, dict):
        raise ValueError('missing-clock')
    mono = number(value['monotonic_seconds'])
    wall = value['wall_at']
    if mono < 0 or not isinstance(wall, str) or len(wall) > 40:
        raise ValueError('invalid-clock')
    if not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?(?:Z|[+]00:00)', wall):
        raise ValueError('invalid-clock')
    date = datetime.fromisoformat(wall.replace('Z', '+00:00'))
    delta = date - datetime(1970, 1, 1, tzinfo=timezone.utc)
    micros = (delta.days*86400 + delta.seconds)*1000000 + delta.microseconds
    return mono, Decimal(micros)/1000000


def seconds(value):
    return format(value, 'f')


def point(value):
    return {'monotonic_seconds': seconds(value[0]), 'wall_epoch_seconds': seconds(value[1])}


def duration(before, after):
    mono, wall = after[0]-before[0], after[1]-before[1]
    return {'monotonic_seconds': seconds(mono), 'wall_seconds': seconds(wall),
            'clock_discrepancy_seconds': seconds(wall-mono)}


def verdict(values):
    if FAIL in values:
        return FAIL
    if UNKNOWN in values:
        return UNKNOWN
    return SAT if SAT in values else NA


def request_locus(request):
    if not isinstance(request, dict):
        raise ValueError('invalid-request')
    kind, status = request.get('failure_kind'), request.get('http_status')
    dispatch, denial = request.get('dispatch'), request.get('denial')
    if kind is not None and kind not in ERRORS:
        raise ValueError('unsupported-failure-kind')
    if request.get('method') != 'GET' or request.get('path') not in {
            '/v2/account', '/v2/positions', '/v2/clock', '/v2beta1/events/activities'}:
        raise ValueError('unsupported-request')
    if (dispatch not in {'not-started', 'started-outcome-unknown', 'response-received'}
            or denial not in {None, 'configuration', 'local-budget', 'local-cooldown'}
            or request.get('failure_locus') not in {None, 'storage', 'configuration', 'local-budget', 'local-cooldown', 'deadline/cancellation', 'observed-provider-status', 'transport-after-headers', 'transport-before-observed-headers', 'unclassified'}):
        raise ValueError('unsupported-request-fields')
    if number(request['elapsed_ms']) < 0:
        raise ValueError('invalid-duration')
    if status is not None and (type(status) is not int or not 100 <= status <= 599):
        raise ValueError('invalid-status')
    if kind == 'storage':
        expected, locus = 'storage', 'storage'
    elif denial in {'local-budget', 'local-cooldown'} and dispatch == 'not-started' and status is None:
        expected, locus = denial, 'local-budget/cooldown'
    elif kind in {'TimeoutError', 'CancelledError'}:
        expected, locus = 'deadline/cancellation', 'deadline/cancellation'
    elif status is not None and status >= 300 and dispatch == 'response-received' and kind:
        expected, locus = 'observed-provider-status', 'observed-provider-status'
    elif kind in TRANSPORT and dispatch in {'started-outcome-unknown', 'response-received'}:
        expected = 'transport-after-headers' if status is not None else 'transport-before-observed-headers'
        locus = expected
    elif kind is None and denial is None and status is not None and 200 <= status < 300 and dispatch == 'response-received':
        expected, locus = None, 'slow-success'
    else:
        expected, locus = request.get('failure_locus'), 'unknown'
    if request.get('failure_locus') != expected:
        raise ValueError('conflicting-locus')
    start, end = clock(request['started_clock']), clock(request['ended_clock'])
    if (clock({'monotonic_seconds': start[0], 'wall_at': request['started_at']}) != start
            or clock({'monotonic_seconds': end[0], 'wall_at': request['ended_at']}) != end):
        raise ValueError('conflicting-request-clocks')
    if request.get('stage') not in {'initial-snapshot', 'identity-before', 'activity-stream', 'identity-after', 'positions-after'}:
        raise ValueError('unsupported-request-stage')
    if end[0] < start[0]:
        raise ValueError('backward-monotonic')
    # Phase summaries can be absent on reused connections. Never manufacture DNS/pool durations.
    phases = request.get('phases')
    if not isinstance(phases, dict) or set(phases) != set(PHASES):
        raise ValueError('missing-phases')
    details = []
    for name in PHASES:
        phase = phases[name]
        count = integer(phase['count'])
        if phase['state'] not in {'not-observed', 'started', 'complete', 'failed'}:
            raise ValueError('unsupported-phase')
        item = {'phase': name, 'count': count, 'attribution': 'unknown'}
        if count == 1 and phase.get('started') is not None and phase.get('ended') is not None:
            lo, hi = clock(phase['started']), clock(phase['ended'])
            if not start[0] <= lo[0] <= hi[0] <= end[0]:
                raise ValueError('conflicting-phase-range')
            item.update(duration(lo, hi));item['attribution'] = 'observed'
        details.append(item)
    phase_state = 'observed' if not request.get('tracing_unavailable') and all(p['attribution'] == 'observed' for p in details) else 'unknown'
    pre_trace = request.get('pre_trace_ms')
    if pre_trace is not None and number(pre_trace) < 0:
        raise ValueError('invalid-pre-trace')
    return {'locus': locus, 'stage': request['stage'], 'path': request['path'], 'http_status': status,
            'dispatch': dispatch, 'denial': denial, 'failure_kind': kind, **duration(start, end), 'phase_attribution': phase_state,
            'start_monotonic_seconds': seconds(start[0]), 'end_monotonic_seconds': seconds(end[0]),
            'phase_measurements': details, 'pre_trace_ms': seconds(number(pre_trace)) if pre_trace is not None else None,
            'pre_trace_attribution': 'unknown'}


class Analysis:
    def __init__(self, run, rows, policy, synthetic):
        self.run, self.rows, self.policy = run, rows, policy
        self.eligible = synthetic and policy is not None and policy['synthetic']
        self.issues, self.segments, self.samples, self.lag = [], [], [], []
        self.label_spans = []
        self.cycles, self.completions, self.sleep_points, self.clock_details = [], [], {}, []
        self.pid = None

    def issue(self, reason, reference):
        self.issues.append({'reason': reason, 'reference': reference})

    def sample(self, value):
        result = clock(value)
        self.samples.append(result)
        return result

    def segment(self, name, start, end, reference, loci=()):
        if end[0] < start[0]:
            raise ValueError('backward-monotonic')
        self.segments.append((name, start, end, reference, list(loci)))

    def lag_summary(self, value, reference):
        if not isinstance(value, dict):
            raise ValueError('invalid-loop-summary')
        count, maximum = integer(value['samples']), number(value['max_ms'])
        if not count and (maximum != 0 or value.get('scheduled') is not None or value.get('observed') is not None):
            raise ValueError('conflicting-loop-summary')
        if maximum < 0:
            raise ValueError('invalid-loop-summary')
        latest = None
        if count:
            a, b = clock(value['scheduled']), clock(value['observed'])
            if b[0] < a[0]:
                raise ValueError('invalid-loop-summary')
            latest = {'scheduled': point(a), 'observed': point(b)}
        self.lag.append({'reference': reference, 'samples': count, 'max_ms': seconds(maximum),
                         'latest_probe': latest, 'maximum_probe_interval': 'unknown',
                         'included_in_interval_totals': False})

    def bound(self, value, sequence=True):
        if (value.get('run_id') != self.run or type(value.get('process_id')) is not int
                or not 0 < value['process_id'] < 2**63 or value['process_id'] != self.pid):
            raise ValueError('conflicting-identity')
        if sequence and (type(value.get('sequence')) is not int or not 0 < value['sequence'] < 2**63
                         or not identity(value.get('attempt_id'))):
            raise ValueError('invalid-identity')

    def cycle(self, start, finish, batches):
        value, ref = finish['value'], finish['reference']
        self.bound(start['value']); self.bound(value)
        if finish['reference']['seq'] <= start['reference']['seq']:
            raise ValueError('conflicting-record-order')
        keys = ('run_id', 'process_id', 'sequence', 'attempt_id')
        if any(start['value'][k] != value[k] for k in keys):
            raise ValueError('conflicting-identity')
        boundaries = value['boundaries']
        if not isinstance(boundaries, dict) or set(boundaries) != set(MARKS):
            raise ValueError('unsupported-boundaries')
        marks = {k: self.sample(boundaries[k]) if boundaries[k] is not None else None for k in MARKS}
        reached = [v for v in marks.values() if v is not None]
        if any(b[0] < a[0] for a, b in zip(reached, reached[1:])):
            raise ValueError('backward-monotonic')
        if marks['attempt_start'] != clock(start['value']['clock']):
            raise ValueError('conflicting-attempt-start')
        required = {'attempt_start', 'attempt_finish'}
        for flag in ('batch_started', 'outcome_retained', 'acquisition_counted'):
            if type(value.get(flag)) is not bool:
                raise ValueError('invalid-flags')
        publication, terminal = value['publication'], value['terminal']
        if value.get('failure_kind') is not None and value['failure_kind'] not in ERRORS:
            raise ValueError('unsupported-failure-kind')
        if terminal not in {'completed', 'failed', 'deadline', 'cancelled', 'storage'} or publication not in {
                'not-started', 'prevented-storage-budget', 'prevented-inactive', 'failed', 'published'}:
            raise ValueError('unsupported-terminal')
        if (value.get('not_started_reason') != (None if value['batch_started'] else terminal)
                or value.get('not_published_reason') != (None if publication == 'published' else terminal)):
            raise ValueError('conflicting-terminal-reason')
        if not value['batch_started'] and any(marks[k] is not None for k in ('retention_start', 'retention_end')):
            raise ValueError('unexpected-retention')
        if marks['collection_end'] is not None and marks['collection_start'] is None:
            raise ValueError('missing-collection-start')
        if value['acquisition_counted'] != (marks['completion'] is not None):
            raise ValueError('conflicting-completion')
        if marks['lock_acquired'] is not None:
            required.update(('lock_wait_start', 'lock_released'))
        elif any(marks[k] is not None for k in MARKS[3:-1]):
            raise ValueError('unsupported-pre-lock-path')
        if marks['collection_start'] is not None:
            required.add('collection_end')
        if value['batch_started']:
            required.update(('lock_wait_start', 'lock_acquired', 'lock_released', 'collection_start', 'collection_end'))
        elif value['outcome_retained'] or value['acquisition_counted'] or publication != 'not-started':
            raise ValueError('unsupported-pre-batch-path')
        originals = batches.get(value['attempt_id'], [])
        acquisition, requests = value.get('acquisition'), []
        if value['batch_started']:
            starts = [b for b in originals if b['phase'] == 'start']
            outcomes = [b for b in originals if b['phase'] == 'outcome']
            if len(originals) != 2 or len(starts) != 1 or len(outcomes) != 1 or not value['outcome_retained']:
                raise ValueError('missing-original-batch')
            required.update(('retention_start', 'retention_end'))
            a, b = starts[0], outcomes[0]
            if a['reference']['rowid'] >= b['reference']['rowid']:
                raise ValueError('conflicting-batch-order')
            if not isinstance(a['account'], str) or not a['account']:
                raise ValueError('invalid-batch-binding')
            if a['account'] != b['account'] or not isinstance(a['value'], dict) or not isinstance(b['value'], dict):
                raise ValueError('conflicting-batch')
            for timestamp in (a['value']['since'], a['value']['until'], b['value']['received_at']):
                clock({'monotonic_seconds': ZERO, 'wall_at': timestamp})
            if not isinstance(acquisition, dict) or acquisition != b['value'].get('diagnostics'):
                raise ValueError('conflicting-acquisition')
            if (acquisition.get('batch') != value['attempt_id'] or acquisition.get('run_id') != self.run
                    or acquisition.get('process_id') != self.pid):
                raise ValueError('conflicting-acquisition')
            if type(b['value'].get('complete')) is not bool or (value['acquisition_counted'] and not b['value']['complete']):
                raise ValueError('conflicting-acquisition-count')
            requests = acquisition.get('requests')
            if not isinstance(requests, list) or len(requests) > 7:
                raise ValueError('unsupported-requests')
            previous = marks['collection_start']
            for request in requests:
                lo, hi = clock(request['started_clock']), clock(request['ended_clock'])
                if previous is None or lo[0] < previous[0] or marks['retention_start'] is None or hi[0] > marks['retention_start'][0]:
                    raise ValueError('conflicting-request-range')
                previous = hi
            requests = [request_locus(r) for r in requests]
            self.clock_details.extend({'reference': ref, **r} for r in requests)
        elif originals or acquisition is not None:
            raise ValueError('unexpected-batch')
        if publication == 'published':
            required.update(('publication_start', 'publication_end', 'sample_start'))
            if terminal == 'completed' or marks['sample_end'] is not None:
                required.add('sample_end')
        elif publication == 'failed':
            required.add('publication_start')
            if marks['publication_end'] is not None or marks['sample_start'] is not None:
                raise ValueError('conflicting-publication')
        elif any(marks[k] is not None for k in ('publication_start', 'publication_end', 'sample_start', 'sample_end')):
            raise ValueError('conflicting-publication')
        if publication in {'prevented-storage-budget', 'prevented-inactive'} and value['acquisition_counted']:
            raise ValueError('conflicting-guard-count')
        if value['acquisition_counted'] and publication not in {'published', 'failed'}:
            raise ValueError('conflicting-counted-path')
        if not all(marks[k] is not None for k in required):
            raise ValueError('missing-boundary')
        loci = sorted({r['locus'] for r in requests})
        failure = acquisition.get('failure_kind') if acquisition else value.get('failure_kind')
        if failure == 'storage':
            loci.append('storage')
        elif failure in {'TimeoutError', 'CancelledError'}:
            loci.append('deadline/cancellation')
        elif failure and not any(r['locus'] not in {'unknown', 'slow-success'} for r in requests):
            loci.append('unknown')
        if not requests and value['batch_started'] and not failure:
            loci.append('unknown')
        for name, a, b, labels in (
                ('lock-wait', 'lock_wait_start', 'lock_acquired', ['lock-wait']),
                ('collection', 'collection_start', 'collection_end', loci),
                ('publication', 'publication_start', 'publication_end', ['slow-success']),
                ('immediate-sample', 'sample_start', 'sample_end', ['slow-success'])):
            if marks[a] is not None and marks[b] is not None:
                self.segment(name, marks[a], marks[b], ref, labels)
        outer_failure = value.get('failure_kind')
        if outer_failure and (marks['collection_start'] is None or marks['collection_end'] is None
                              or outer_failure != failure):
            locus = ('storage' if outer_failure == 'storage' else 'deadline/cancellation'
                     if outer_failure in {'TimeoutError', 'CancelledError'} else 'unknown')
            if marks['sample_start'] is not None and marks['sample_end'] is None:
                lo = marks['sample_start']
            elif marks['publication_start'] is not None and marks['publication_end'] is None:
                lo = marks['publication_start']
            else:
                lo = marks['lock_wait_start'] or marks['attempt_start']
            # Failure bounds supply attribution only, never an inferred execution duration.
            self.label_spans.append((lo, marks['attempt_finish'], locus))
        self.lag_summary(value['loop_lag'], ref)
        if value['acquisition_counted']:
            self.completions.append(marks['completion'])
        self.cycles.append({'sequence': value['sequence'], 'reference': ref,
                            'batch_started': value['batch_started'], 'outcome_retained': value['outcome_retained'],
                            'batch_references': [r['reference'] for r in originals],
                            'failure_kind': value.get('failure_kind'),
                            'acquisition_counted': value['acquisition_counted'], 'publication': publication,
                            'terminal': terminal, 'requests': requests, 'boundaries': marks})

    def sleep(self, start, finish):
        a, b, ref = start['value'], finish['value'], finish['reference']
        if finish['reference']['seq'] <= start['reference']['seq']:
            raise ValueError('conflicting-record-order')
        self.bound(a, False); self.bound(b, False)
        if (type(a.get('sequence')) is not int or a['sequence'] <= 0 or a['sequence'] != b.get('sequence')
                or number(a['intended_seconds']) != number(b['intended_seconds'])):
            raise ValueError('conflicting-sleep')
        intended = number(b['intended_seconds'])
        if not 0 <= intended <= 60 or b.get('result') not in {'woke', 'interrupted'}:
            raise ValueError('unsupported-sleep')
        scheduled, entered = self.sample(b['scheduled']), self.sample(b['entered'])
        target, wake = self.sample(b['scheduled_wake']), self.sample(b['wake'])
        if clock(a['clock']) != scheduled or not scheduled[0] <= entered[0] <= wake[0]:
            raise ValueError('conflicting-sleep')
        # Planned targets are intentionally unrounded producer additions; they are distinct samples.
        clock(a['scheduled_wake'])
        self.segment('diagnostic-write-overhead', scheduled, entered, ref)
        if entered[0] <= target[0] <= wake[0]:
            self.segment('sleep', entered, target, ref)
            self.segment('wake-delay', target, wake, ref, ['loop/scheduler-delay'])
        else:
            self.segment('sleep', entered, wake, ref)
        self.lag_summary(b['loop_lag'], ref)
        self.sleep_points[a['sequence']] = [scheduled, entered, *([target] if entered[0] <= target[0] <= wake[0] else []), wake]
        return a['sequence']

    def populations(self, summary):
        result = {}
        for name in ('matched_publications', 'received_bytes', 'request_budget_units'):
            result[name] = integer(summary[name])
        latencies = summary['latency']
        names = ('acquisition', 'publication', 'state', 'lock_wait', 'scheduling_delay', 'event_loop_lag', 'acquisition_execution')
        result['latency'] = {}
        for name in names:
            value = latencies[name]
            upper = value['p95_upper_ms']
            if upper is not None:
                integer(upper)
            result['latency'][name] = {'samples': integer(value['samples']), 'p95_upper_ms': upper,
                                       'over_5000_ms': integer(value['over_5000_ms'])}
        for name in ('availability_samples', 'publication_availability_samples'):
            value = summary[name]
            if not isinstance(value, dict) or not set(value) <= {'current', 'incomplete'}:
                raise ValueError('unsupported-population')
            result[name] = {k: integer(v) for k, v in value.items()}
        return result

    def intervals(self, start, end):
        edges = [start, *self.completions, end]
        if any(b[0] < a[0] for a, b in zip(edges, edges[1:])):
            self.issue('conflicting-completion-order', {'table': 'events'})
            return []
        result = []
        tau = self.policy.get('tau_seconds') if self.eligible else None
        tau_c = self.policy.get('tau_c_seconds') if self.eligible else None
        for index, (a, b) in enumerate(zip(edges, edges[1:])):
            try:
                pieces, covered, cursor, labels = [], [], a, []
                # Source order was validated before this traversal. Never repair ordering by sorting clocks.
                residual_points = []
                for name, lo, hi, ref, loci in self.segments:
                    if hi[0] <= a[0] or lo[0] >= b[0] or hi[0] == lo[0]:
                        continue
                    lo = a if lo[0] < a[0] else lo
                    hi = b if hi[0] > b[0] else hi
                    if lo[0] < cursor[0]:
                        raise ValueError('overlapping-spans')
                    if cursor[0] < lo[0]:
                        residual_points.append((cursor, lo))
                    pieces.append({'category': name, 'reference': ref, **duration(lo, hi), 'loci': loci})
                    covered.append((hi[0]-lo[0], hi[1]-lo[1]))
                    cursor = hi
                    if hi[0] > lo[0]:
                        labels.extend(loci)
                if cursor[0] < b[0]:
                    residual_points.append((cursor, b))
                residuals = []
                for lo, hi in residual_points:
                    # Keep every recorded boundary inside residual, including opposing wall steps.
                    internal = [p for p in self.samples if lo[0] < p[0] < hi[0]]
                    ordered = []
                    for p in internal:
                        if not ordered or p[0] >= ordered[-1][0]:
                            ordered.append(p)
                    for x, y in zip([lo, *ordered], [*ordered, hi]):
                        residuals.append({'category': 'residual', **duration(x, y)})
                mono, wall = b[0]-a[0], b[1]-a[1]
                rm = mono-sum((v[0] for v in covered), ZERO)
                rw = wall-sum((v[1] for v in covered), ZERO)
                # Also expose subspans (e.g. a request) whose opposing steps cancel in the parent.
                discrepancies = [duration(x, y) for x, y in zip(self.samples, self.samples[1:])
                                 if a[0] <= x[0] <= y[0] <= b[0] and y[1]-x[1] != y[0]-x[0]]
                discrepancies.extend({k: r[k] for k in ('monotonic_seconds', 'wall_seconds', 'clock_discrepancy_seconds')}
                                     for r in self.clock_details if Decimal(r['clock_discrepancy_seconds']) != 0
                                     and a[0] <= Decimal(r['start_monotonic_seconds']) <= Decimal(r['end_monotonic_seconds']) <= b[0])
                discrepancies.extend({k: phase[k] for k in ('monotonic_seconds', 'wall_seconds', 'clock_discrepancy_seconds')}
                                     for r in self.clock_details
                                     if a[0] <= Decimal(r['start_monotonic_seconds']) <= Decimal(r['end_monotonic_seconds']) <= b[0]
                                     for phase in r['phase_measurements']
                                     if 'clock_discrepancy_seconds' in phase and Decimal(phase['clock_discrepancy_seconds']) != 0)
                candidate = mono > 120 or wall > 120 or (tau_c is not None and abs(wall-mono) > tau_c)
                if discrepancies or wall != mono:
                    labels.append('clock-discontinuity')
                labels.extend(locus for lo, hi, locus in self.label_spans
                              if lo[0] < b[0] and hi[0] > a[0])
                e2 = UNKNOWN if tau is None or tau_c is None else SAT if abs(rm) <= tau else FAIL
                e3 = (UNKNOWN if 'unknown' in labels or not labels else SAT) if candidate else (NA if tau_c is not None else UNKNOWN)
                root = 'local' if labels and set(labels) <= {'lock-wait', 'loop/scheduler-delay', 'storage', 'local-budget/cooldown'} else 'indeterminate'
                allow = self.policy.get('allow_indeterminate_e4') if self.eligible else None
                e4 = (UNKNOWN if allow is None else FAIL if root == 'indeterminate' and not allow
                      else UNKNOWN if root == 'indeterminate' and (e2 != SAT or e3 != SAT)
                      else SAT) if candidate else (NA if tau_c is not None else UNKNOWN)
                result.append({'index': index, 'start': point(a), 'end': point(b), **duration(a, b),
                    'candidate': candidate, 'candidate_completeness': SAT if tau_c is not None else UNKNOWN,
                    'contributions': pieces, 'residual_components': residuals,
                    'residual_monotonic_seconds': seconds(rm), 'residual_wall_seconds': seconds(rw),
                    'clock_discrepancies': discrepancies, 'loci': sorted(set(labels)),
                    'E2': e2, 'E3': e3, 'root_cause': root, 'E4_policy': e4})
            except DEFECTS:
                self.issue('invalid-interval', {'interval': index})
                result.append({'index': index, 'E2': UNKNOWN, 'E3': UNKNOWN, 'E4_policy': UNKNOWN,
                               'root_cause': 'indeterminate', 'candidate': None})
        return result

    def run_analysis(self):
        events, summaries, batches = [], [], {}
        for row in self.rows:
            value = row.get('value')
            if value is None:
                self.issue('malformed-record', row['reference']); continue
            if row['kind'] == 'batch':
                batches.setdefault(row['id'], []).append(row); continue
            if row['kind'] == 'event' and row.get('type') == 'activity_rollout_previous' and legacy_summary(value):
                continue
            embedded = value.get('clock_diagnostics')
            run = embedded.get('run_id') if isinstance(embedded, dict) else value.get('run_id')
            if run != self.run:
                if not identity(run) or (row.get('type') == 'activity_rollout_stopped' and value.get('run_id') == self.run):
                    self.issue('unassignable-record', row['reference'])
                continue
            if row['kind'] == 'summary' or row.get('type') in {'activity_rollout_stopped', 'activity_rollout_previous'}:
                summaries.append(row)
            else:
                events.append(row)
        starts = [r for r in events if r.get('type') == 'activity_rollout_started']
        stops = [r for r in summaries if r.get('type') == 'activity_rollout_stopped']
        terminal, beginning, ending, counters, populations = [], None, None, None, None
        if len(starts) != 1:
            self.issue('missing-or-duplicate-observation-start', {'table': 'events'})
        else:
            try:
                value = starts[0]['value']; self.pid = integer(value['process_id'])
                if not self.pid or number(value['duration_seconds']) != 86400:
                    raise ValueError('invalid-run')
                beginning = self.sample(value['clock'])
                if beginning[0] != 0:
                    raise ValueError('unsupported-observation-origin')
            except DEFECTS:
                self.issue('invalid-observation-start', starts[0]['reference'])
        if len(stops) != 1:
            self.issue('missing-or-duplicate-observation-end', {'table': 'events'})
        for row in summaries:
            try:
                v = row['value']; c = v['clock_diagnostics']
                if c['run_id'] != self.run or c['process_id'] != self.pid:
                    raise ValueError('conflicting-summary-identity')
                if row.get('type') == 'activity_rollout_stopped' and v.get('run_id') != self.run:
                    raise ValueError('conflicting-summary-identity')
                if clock(c['start']) != beginning:
                    raise ValueError('conflicting-observation-start')
                if v['status'] != 'stopped' or c.get('end') is None:
                    continue
                end = self.sample(c['end']); count = (integer(v['cycles']), integer(v['complete_acquisitions']))
                if count[1] > count[0]:
                    raise ValueError('conflicting-counters')
                terminal.append((count, end, row))
            except DEFECTS:
                self.issue('invalid-summary', row['reference'])
        if terminal and all((x[0], x[1]) == (terminal[0][0], terminal[0][1]) for x in terminal):
            counters, ending, row = terminal[-1]
            try:
                populations = self.populations(row['value'])
            except DEFECTS:
                self.issue('invalid-populations', row['reference'])
        else:
            self.issue('missing-or-conflicting-terminal-counters', {'table': 'state/events'})
        for row in events:
            if row.get('type') == 'activity_attempt_abandoned':
                self.issue('abandoned-cycle', row['reference'])
        attempts = [r for r in events if r.get('type') == 'activity_attempt_started']
        finishes = []
        for row in events:
            if row.get('type') == 'activity_attempt_finished':
                sequence = row['value'].get('sequence')
                if type(sequence) is not int or not 0 < sequence < 2**63:
                    self.issue('invalid-attempt-sequence', row['reference'])
                else:
                    finishes.append(row)
        used = set()
        for start in attempts:
            try:
                v = start['value']; self.bound(v)
                matches = [r for r in finishes if r['value'].get('sequence') == v['sequence']]
                if len(matches) != 1 or v['sequence'] in used:
                    raise ValueError('missing-or-duplicate-attempt')
                if starts and start['reference']['seq'] <= starts[0]['reference']['seq']:
                    raise ValueError('conflicting-run-order')
                used.add(v['sequence']); self.cycle(start, matches[0], batches)
            except DEFECTS:
                self.issue('invalid-cycle', start['reference'])
        if len(finishes) != len(attempts) or any(r['value'].get('sequence') not in used for r in finishes):
            self.issue('unpaired-attempt-finish', {'table': 'events'})
        if counters and (len(attempts) != counters[0]
                         or any(r['value'].get('sequence') != n for n, r in enumerate(attempts, 1))
                         or len(self.completions) != counters[1]):
            self.issue('counter-lifecycle-mismatch', {'table': 'events'})
        if counters and len(self.completions) == counters[1]:
            for _count, _end, row in terminal:
                try:
                    last = row['value']['clock_diagnostics'].get('last_completion')
                    if (clock(last) if last is not None else None) != (self.completions[-1] if self.completions else None):
                        raise ValueError('conflicting-last-completion')
                except DEFECTS:
                    self.issue('conflicting-last-completion', row['reference'])
        sleep_starts = [r for r in events if r.get('type') == 'activity_observation_sleep_started']
        sleep_finishes = [r for r in events if r.get('type') == 'activity_observation_sleep_finished']
        sleeps, sleep_segments = set(), []
        for a in sleep_starts:
            try:
                matches = [b for b in sleep_finishes if b['value'].get('sequence') == a['value'].get('sequence')]
                if len(matches) != 1 or a['value']['sequence'] in sleeps:
                    raise ValueError('missing-or-duplicate-sleep')
                seq = a['value']['sequence']
                prior = [r for r in finishes if r['value'].get('sequence') == seq]
                following = [r for r in attempts if r['value'].get('sequence') == seq+1]
                if (len(prior) != 1 or a['reference']['seq'] <= prior[0]['reference']['seq']
                        or (following and matches[0]['reference']['seq'] >= following[0]['reference']['seq'])
                        or (following and matches[0]['value'].get('result') != 'woke')
                        or (counters and not 1 <= seq <= counters[0])):
                    raise ValueError('conflicting-sleep-order')
                scheduled = clock(matches[0]['value']['scheduled'])
                wake = clock(matches[0]['value']['wake'])
                if (scheduled[0] < clock(prior[0]['value']['boundaries']['attempt_finish'])[0]
                        or (following and wake[0] > clock(following[0]['value']['clock'])[0])):
                    raise ValueError('conflicting-sleep-clock-order')
                before = len(self.segments); sleeps.add(self.sleep(a, matches[0])); sleep_segments.extend(self.segments[before:]); del self.segments[before:]
            except DEFECTS:
                self.issue('invalid-sleep', a['reference'])
        if len(sleep_finishes) != len(sleep_starts):
            self.issue('unpaired-sleep-finish', {'table': 'events'})
        if counters and len({seq for seq in sleeps if seq < counters[0]}) != max(0, counters[0]-1):
            self.issue('missing-between-cycle-sleep', {'table': 'events'})
        if counters and self.cycles and ending is not None:
            last = self.cycles[-1]
            if (last['sequence'] not in sleeps and ending[0] > last['boundaries']['attempt_finish'][0]
                    and ending[0] < 86400 and last['terminal'] not in {'cancelled', 'deadline'}
                    and last['publication'] != 'prevented-inactive'):
                self.issue('missing-terminal-sleep', {'table': 'events'})
        # Insert sleeps by their recorded sequence position, rather than sorting wall or monotonic clocks.
        merged = []
        for c in self.cycles:
            merged.extend(s for s in self.segments if s[3] == c['reference'])
            refs = {r['reference']['seq'] for r in sleep_finishes if r['value'].get('sequence') == c['sequence']}
            merged.extend(s for s in sleep_segments if s[3].get('seq') in refs)
        self.segments = merged
        # Global samples must follow logical boundary order; duplicate nested samples remain diagnostic only.
        self.samples = [beginning] if beginning is not None else []
        for c in self.cycles:
            self.samples.extend(p for p in c['boundaries'].values() if p is not None)
            self.samples.extend(self.sleep_points.get(c['sequence'], []))
        if ending is not None:
            self.samples.append(ending)
        ratio = UNKNOWN if counters is None else SAT if counters[0] > 0 and 100*counters[1] >= 99*counters[0] else FAIL
        intervals = self.intervals(beginning, ending) if beginning is not None and ending is not None else []
        e1 = UNKNOWN if self.issues else SAT
        e2 = verdict([i['E2'] for i in intervals]) if intervals else UNKNOWN
        e3 = verdict([i['E3'] for i in intervals]) if intervals else UNKNOWN
        e4 = verdict([i['E4_policy'] for i in intervals]) if intervals else UNKNOWN
        if self.issues:
            e2, e3, e4 = UNKNOWN, UNKNOWN, UNKNOWN
        policy_state = SAT if self.eligible and all(self.policy.get(k) is not None for k in (
            'tau_seconds', 'tau_c_seconds', 'allow_indeterminate_e4')) else UNKNOWN
        states = [e1, e2, e3, e4, ratio, policy_state]
        return {'run_id': self.run, 'process_id': self.pid,
                'counters': {'cycles': counters[0] if counters else None,
                             'complete_acquisitions': counters[1] if counters else None, 'ratio_requirement': ratio},
                'cycles': [{**{k: v for k, v in c.items() if k != 'boundaries'},
                            'boundaries': {k: point(v) if v is not None else None for k, v in c['boundaries'].items()}} for c in self.cycles],
                'populations': populations, 'E1': e1, 'E2': e2, 'E3': e3, 'E4_policy': e4,
                'policy_evaluation': policy_state, 'synthetic_policy': self.eligible,
                'intervals': intervals, 'loop_lag': self.lag, 'issues': self.issues,
                'exit_code': 1 if FAIL in states else 3 if UNKNOWN in states else 0}


def analyze(run_id, rows, policy=None, synthetic=False):
    """Evaluate decoded records; all clock arithmetic is independent of ambient context."""
    with exact():
        return Analysis(run_id, rows, policy, synthetic).run_analysis()
