"""Paired real HTTP/SQLite Save measurements; instrumentation runs separately.

Prepare once, then use the SAME immutable input on each compared source tree.
All writes use disposable SQLite backups. A restart is a fresh Python process.
No instrumentation is installed in timing mode. No authority gate is bypassed.
"""

import argparse
import cProfile
from dataclasses import fields, is_dataclass
from enum import Enum
import functools
import gc
import hashlib
import json
import marshal
import multiprocessing
import os
from pathlib import Path
import platform
import pstats
import resource
import re
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.api.test_calendar_global_slots import copy_database, ready
from tests.api.test_calendar_tour_flow import command, execute, inspect, tour_url
from tests.api.test_saved_revision_history_api import ApiServer, _request


def workspace_path(value):
    """Keep disposable inputs and outputs beneath this checkout's work/ tree."""
    work = (Path.cwd() / 'work').resolve()
    candidate = Path(value).resolve()
    if candidate == work or not candidate.is_relative_to(work):
        raise argparse.ArgumentTypeError('Measurement paths must be inside this checkout\'s work/ directory')
    return candidate


def measurement_root(value):
    candidate = workspace_path(value)
    work = (Path.cwd() / 'work').resolve()
    if candidate.parent != work or re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}', candidate.name) is None:
        raise argparse.ArgumentTypeError('Output must be work/<case-name>, using letters, digits, _ or -')
    # Reconstruct from the fixed base and the allowlisted leaf, not CLI text.
    return work / candidate.name


def open_artifact(root, filename, *, binary=False):
    """Create one new report; reject traversal, symlinks and existing files."""
    if re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,99}', filename) is None:
        raise ValueError('Invalid report filename')
    directory = measurement_root(str(root))
    destination = directory / filename
    if destination.resolve().parent != directory:
        raise ValueError('Report escapes the measurement directory')
    return destination.open('xb' if binary else 'x')


def retained_bytes(root):
    """Reachable Python heap, deduplicated by identity, including model slots.

    This measures data retained by the cache, not serialized-input accounting.
    Classes/code/modules are not cache data. Allocator slack is reflected in RSS.
    """
    from pydantic import BaseModel

    seen, pending, size = set(), [root], 0
    while pending:
        value = pending.pop()
        if id(value) in seen:
            continue
        seen.add(id(value))
        size += sys.getsizeof(value)
        if isinstance(value, dict):
            pending.extend(value.keys())
            pending.extend(value.values())
        elif isinstance(value, (tuple, list, set, frozenset)):
            pending.extend(value)
        elif isinstance(value, BaseModel):
            pending.append(value.__dict__)
            for slot in ('__pydantic_extra__', '__pydantic_private__', '__pydantic_fields_set__'):
                pending.append(getattr(value, slot, None))
        elif isinstance(value, Enum):
            pending.extend((value.name, value.value))
        elif is_dataclass(value) and not isinstance(value, type):
            pending.extend(getattr(value, field.name) for field in fields(value))
            if hasattr(value, '__dict__'):
                pending.append(value.__dict__)
    return size


def memory(repo):
    gc.collect()
    cache = getattr(repo, '_global_tour_projection_cache', {})
    rss = int(Path('/proc/self/statm').read_text().split()[1]) * os.sysconf('SC_PAGE_SIZE')
    return dict(cache_entries=len(cache), cache_heap_bytes=retained_bytes(cache),
                cache_budget_bytes=sum(v[0] for v in cache.values()), rss_bytes=rss,
                peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


def observers(mode, root):
    if mode == 'timing':
        return {}, []
    from beta_engine.infrastructure.db import native_fork_source_projection as cache
    from beta_engine.infrastructure.db import calendar_sporting_checkpoint as cp
    from beta_engine.infrastructure.db import calendar_standalone_match_state as match_state
    from beta_engine.domain.tournaments import calendar_tour as tour
    from beta_engine.domain.tournaments import calendar_global_slots as slots
    from scripts.profile_native_full_simulation_metrics import measure_calls

    counts = {name: measure_calls(owner, name) for owner, name in (
        (cache, '_copy_decoded_value'), (cache, 'canonical_json'),
        (cache, 'decoded_global_checkpoint_component'), (cache, 'decoded_global_tour_source'),
        (cp, 'parse_checkpoint_json'), (tour, 'parse_tour_json'),
        (match_state, '_parse_saved_calendar_match_evidence'),
    )}
    checkpoint_copies = counts['checkpoint_root_copies'] = {'calls': 0}
    whole_copies = counts['whole_dto_copies'] = {'calls': 0}
    evidence_copies = counts['evidence_root_copies'] = {'calls': 0}
    original_copy = cache._copy_decoded_value

    def copied(value, *args, **kwargs):
        values = value if isinstance(value, tuple) else (value,)
        n = sum(getattr(item, 'schema_version', None) == 'calendar_sporting_checkpoint.v13'
                for item in values)
        checkpoint_copies['calls'] += n
        whole_copies['calls'] += bool(n and isinstance(value, tuple) and len(value) == 3)
        evidence_copies['calls'] += sum(str(getattr(item, 'schema_version', '')).startswith(
            ('calendar_opening_knockout.', 'calendar_scored_opening_knockout.',
             'calendar_standalone_match.', 'calendar_match.')) for item in values)
        return original_copy(value, *args, **kwargs)

    cache._copy_decoded_value = copied
    hashes = counts['checkpoint_full_hashes'] = {'calls': 0}
    original_hash = slots.canonical_hash

    def hashed(value):
        if isinstance(value, dict) and value.get('schema_version') == 'calendar_sporting_checkpoint.v13':
            hashes['calls'] += 1
        return original_hash(value)

    slots.canonical_hash = hashed
    profiles = []
    if mode == 'profile':
        from beta_engine.application.calendar_tour_service import CalendarTourService
        from beta_engine.infrastructure.db.repositories import SimulationPersistenceRepository
        for owner, name in ((CalendarTourService, 'inspect'),
                            (CalendarTourService, 'preview'), (CalendarTourService, 'execute'),
                            (SimulationPersistenceRepository, 'save_viewer_branch_selection_atomically')):
            original = getattr(owner, name)

            def wrap(original, name):
                @functools.wraps(original)
                def measured(*args, **kwargs):
                    profile = cProfile.Profile()
                    try:
                        return profile.runcall(original, *args, **kwargs)
                    finally:
                        profiles.append((name, profile))
                return measured
            setattr(owner, name, wrap(original, name))
    return counts, profiles


class WriterLockClock:
    """Wall time from each actual ``BEGIN IMMEDIATE`` to its COMMIT/ROLLBACK.

    SQLAlchemy connection events only observe statements; they never change
    them. One SQLite writer lock is one such interval on one DBAPI connection.
    """

    def __init__(self):
        import threading

        from sqlalchemy import event
        from sqlalchemy.engine import Engine

        self.intervals = []
        self._lock = threading.Lock()
        event.listen(Engine, 'before_cursor_execute', self._begin)
        event.listen(Engine, 'commit', self._end)
        event.listen(Engine, 'rollback', self._end)

    def _begin(self, connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip()[:15].upper() == 'BEGIN IMMEDIATE':
            connection.info['profile_writer_lock_start'] = time.perf_counter()

    def _end(self, connection):
        start = connection.info.pop('profile_writer_lock_start', None)
        if start is not None:
            with self._lock:
                self.intervals.append(time.perf_counter() - start)

    def mark(self):
        with self._lock:
            return len(self.intervals)

    def since(self, mark):
        with self._lock:
            values = self.intervals[mark:]
        return dict(writer_lock_count=len(values), writer_lock_seconds=sum(values),
                    writer_lock_max_seconds=max(values, default=0.0))


SLOT_SAVE_OBSERVED = (
    # (module, attribute, label) for --slot-plan --mode calls. Wrapping keeps
    # inputs/results/errors; per-call wall/CPU include the wrapper itself.
    ('beta_engine.infrastructure.db.calendar_sporting_checkpoint', 'read_checkpoint_for_save', None),
    ('beta_engine.infrastructure.db.native_fork_source_projection', 'take_live_calendar_component', None),
    ('beta_engine.infrastructure.db.calendar_sporting_checkpoint', '_checkpoint_for_capture', None),
    ('beta_engine.infrastructure.db.native_fork_source_projection', 'decoded_live_calendar_component', None),
    ('beta_engine.infrastructure.db.native_fork_source_projection', 'remember_committed_global_sources', None),
    ('beta_engine.infrastructure.db.native_fork_source_projection', '_value_identity', None),
    ('beta_engine.infrastructure.db.calendar_sporting_checkpoint', 'parse_checkpoint_json', None),
)


def slot_observers(mode):
    """Calls mode only: counts, inclusive wall/CPU and copy attribution by caller."""
    if mode == 'timing':
        return {}, []
    import importlib

    from scripts.profile_native_full_simulation_metrics import measure_calls

    counts = {}
    for module_name, attribute, _ in SLOT_SAVE_OBSERVED:
        module = importlib.import_module(module_name)
        if hasattr(module, attribute):
            counts[attribute] = measure_calls(module, attribute)
    from beta_engine.infrastructure.db import native_fork_source_projection as cache
    copies = counts['_copy_decoded_value_v13_by_caller'] = {}
    original_copy = cache._copy_decoded_value

    def copied(value, *args, **kwargs):
        values = value if isinstance(value, tuple) else (value,)
        is_checkpoint = any(getattr(item, 'schema_version', None) == 'calendar_sporting_checkpoint.v13'
                            for item in values)
        if not is_checkpoint:
            return original_copy(value, *args, **kwargs)
        caller = sys._getframe(1).f_code.co_name
        start, cpu = time.perf_counter(), time.thread_time()
        try:
            return original_copy(value, *args, **kwargs)
        finally:
            row = copies.setdefault(caller, {'calls': 0, 'wall_seconds': 0.0, 'thread_cpu_seconds': 0.0})
            row['calls'] += 1
            row['wall_seconds'] += time.perf_counter() - start
            row['thread_cpu_seconds'] += time.thread_time() - cpu

    cache._copy_decoded_value = copied
    profiles = []
    if mode == 'profile':
        from beta_engine.infrastructure.db.repositories import SimulationPersistenceRepository

        owner, name = SimulationPersistenceRepository, 'save_viewer_branch_selection_atomically'
        original = getattr(owner, name)

        @functools.wraps(original)
        def measured(*args, **kwargs):
            profile = cProfile.Profile()
            try:
                return profile.runcall(original, *args, **kwargs)
            finally:
                profiles.append((name, profile))
        setattr(owner, name, measured)
    return counts, profiles


def _snapshot_counts(counts):
    def copy(value):
        return {k: copy(v) for k, v in value.items()} if isinstance(value, dict) else value
    return copy(counts)


def _delta_counts(before, after):
    if isinstance(after, dict):
        return {k: _delta_counts(before.get(k, {} if isinstance(v, dict) else 0), v) for k, v in after.items()}
    return after - before


def _db_bytes(path):
    wal = path.with_name(path.name + '-wal')
    return dict(db_bytes=path.stat().st_size, wal_bytes=wal.stat().st_size if wal.exists() else 0)


def _history_digest(path):
    """Every Saved revision envelope/content hash and the live sporting row bytes.

    Read-only raw SQL after the server stopped. The signed content hash covers
    each complete payload (Saved v1 or v2 storage); timestamps are excluded.
    """
    import sqlite3

    with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as connection:
        live = connection.execute(
            'SELECT fingerprint, payload_json FROM calendar_player_sporting_checkpoints '
            "WHERE run_id='run' AND branch_id='branch'").fetchone()
        rows = [list(row) for row in connection.execute(
            'SELECT revision_id, branch_id, sequence, parent_revision_id, kind, content_hash_algorithm, '
            "content_hash, change_summary_json FROM branch_saved_revisions WHERE run_id='run' "
            'ORDER BY sequence, revision_id')]
    return dict(revisions=len(rows),
                history_sha256=hashlib.sha256(json.dumps(rows).encode()).hexdigest(),
                live_checkpoint_fingerprint=live[0] if live else None,
                live_checkpoint_bytes=len(live[1].encode()) if live else 0,
                live_checkpoint_sha256=hashlib.sha256(live[1].encode()).hexdigest() if live else None)


def _deterministic_ids(seed_text):
    """Same Saved/audit IDs in every compared run (as profile_native_week_ab.py)."""
    from itertools import count
    from uuid import NAMESPACE_URL, uuid5

    from beta_engine.api import deps

    ids = count()
    deps.uuid4 = lambda: uuid5(NAMESPACE_URL, f'save-slots:{seed_text}:{next(ids)}')


def _inspection_digest(view):
    return hashlib.sha256(json.dumps(view, sort_keys=True).encode()).hexdigest()


def slot_plan(a, local, digest):
    """next-slot -> GET -> POST Save -> GET x2 for three Save conditions.

    Slot 1 Save follows its GET in the same process (warm value cache).
    Slot 2 empties the process-local decode-value caches after its GET, the
    same state an evicted entry leaves (cold miss). No proof, Saved or live row
    is touched. Slot 3 is executed, the process exits with its dirty draft, and
    a fresh process performs GET -> Save -> GET x2 (after restart).
    """
    _deterministic_ids(f'{digest}:{"restart" if a.restart_child else "main"}')
    counts, profiles = slot_observers(a.mode)
    clock = WriterLockClock()
    rows = []
    import threading
    peak = {'rss': 0}
    stop = threading.Event()

    def sample():
        while not stop.is_set():
            rss = int(Path('/proc/self/statm').read_text().split()[1]) * os.sysconf('SC_PAGE_SIZE')
            peak['rss'] = max(peak['rss'], rss)
            stop.wait(0.05)

    sampler = threading.Thread(target=sample, daemon=True)
    sampler.start()
    with ApiServer(database_url=f'sqlite:///{local}') as server:
        repo = server.app.state.runtime.repository

        def phase(label, operation):
            before, mark = _snapshot_counts(counts), clock.mark()
            peak['rss'] = 0
            start, cpu = time.perf_counter(), time.process_time()
            value = operation()
            row = dict(phase=label, seconds=time.perf_counter() - start,
                       process_cpu_seconds=time.process_time() - cpu,
                       phase_peak_rss_bytes=peak['rss'],
                       process_peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                       **clock.since(mark), **_db_bytes(local))
            if a.mode != 'timing':
                row['calls'] = _delta_counts(before, _snapshot_counts(counts))
            rows.append(row)
            print(json.dumps(row), flush=True)
            return value

        def save(view):
            status, receipt = _request('POST', tour_url(server) + '/save', {
                'expected_draft_version': view['draft_version'],
                'expected_calendar_tour_fingerprint': view['tour_fingerprint'],
            })
            assert status == 201, receipt
            return receipt

        def next_slot(index):
            view = inspect(server)
            cmd = command(view, 'next-slot', name=f'save-slots:slot-{index}')
            return execute(server, cmd)

        def evict_decode_values():
            # Exactly what bounded eviction of these process-local values leaves.
            with repo._revision_validation_lock:
                for name in ('_live_calendar_value_cache', '_live_value_fingerprints',
                             '_global_tour_projection_cache', '_native_source_projection_cache'):
                    cache = getattr(repo, name, None)
                    if cache is not None:
                        cache.clear()

        if not a.restart_child:
            phase('initial_cold_get', lambda: inspect(server))
            phase('initial_warm_get', lambda: inspect(server))
            for index, condition in ((1, 'warm'), (2, 'cold_miss')):
                phase(f'slot{index}_next_slot', lambda: next_slot(index))
                view = phase(f'slot{index}_draft_get', lambda: inspect(server))
                assert not view['saved']
                if condition == 'cold_miss':
                    evict_decode_values()
                phase(f'slot{index}_save_{condition}', lambda: save(view))
                phase(f'slot{index}_saved_get', lambda: inspect(server))
                phase(f'slot{index}_saved_get_again', lambda: inspect(server))
            phase('slot3_next_slot', lambda: next_slot(3))
            view = phase('slot3_draft_get', lambda: inspect(server))
            assert not view['saved']
        else:
            view = phase('restart_first_get', lambda: inspect(server))
            assert not view['saved']
            phase('restart_second_get', lambda: inspect(server))
            phase('slot3_save_after_restart', lambda: save(view))
            phase('slot3_saved_get', lambda: inspect(server))
            final = phase('slot3_saved_get_again', lambda: inspect(server))
            editions = final.get('edition_evidence', {})
            rows.append(dict(phase='final', inspection_sha256=_inspection_digest(final),
                             match_count=sum(len(v['matches']) for v in editions.values()),
                             head=final['saved_head_revision_id']))
    stop.set()
    return rows, profiles


def slot_main(a):
    from contextlib import closing
    import sqlite3

    import beta_engine

    if not Path(beta_engine.__file__).resolve().is_relative_to((Path.cwd() / 'src').resolve()):
        # A shared editable environment must not measure another checkout.
        raise SystemExit('Imported engine is not this checkout; set PYTHONPATH=<checkout>/src')
    if not a.restart_child:
        if not a.input or not a.input_sha256:
            raise SystemExit('--slot-plan needs --input and --input-sha256')
    a.root.mkdir(parents=True, exist_ok=a.restart_child)
    local = a.root / 'run.db'
    if not a.restart_child:
        if hashlib.sha256(a.input.read_bytes()).hexdigest() != a.input_sha256:
            raise SystemExit('Input SHA-256 differs')
        # Fresh physical copy of the pinned fixture; the input is never opened read-write.
        with closing(sqlite3.connect(a.input.as_uri() + '?mode=ro', uri=True)) as source, \
                closing(sqlite3.connect(local)) as target:
            source.backup(target)
    digest = a.input_sha256 or json.loads((a.root / 'timings.json').read_text())['metadata']['input_sha256']
    rows, profiles = slot_plan(a, local, digest)
    metadata = dict(git_sha=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                    source_tree=subprocess.check_output(['git', 'rev-parse', 'HEAD:src'], text=True).strip(),
                    script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    input_sha256=digest, python=sys.version, platform=platform.platform(), mode=a.mode,
                    slot_plan=True, cpu_count=os.cpu_count(),
                    pythonhashseed=os.environ.get('PYTHONHASHSEED'),
                    new_run_storage=os.environ.get('BETA_ENGINE_NEW_RUN_SAVED_STORAGE'),
                    source_diff=subprocess.check_output(['git', 'diff', '--', 'src'], text=True))
    if a.restart_child:
        metadata['history'] = _history_digest(local)
    with open_artifact(a.root, 'restart.json' if a.restart_child else 'timings.json') as stream:
        json.dump(dict(metadata=metadata, phases=rows), stream, indent=2)
    for index, (name, profile) in enumerate(profiles):
        prefix = 'restart-' if a.restart_child else ''
        profile.create_stats()
        with open_artifact(a.root, f'{prefix}{index:02d}.pstats', binary=True) as stream:
            marshal.dump(profile.stats, stream)
        with open_artifact(a.root, f'{prefix}{index:02d}.txt') as stream:
            pstats.Stats(profile, stream=stream).strip_dirs().sort_stats('tottime').print_stats(80)
    if not a.restart_child:
        child = multiprocessing.get_context('spawn').Process(target=main, args=([
            f'--root={a.root}', f'--mode={a.mode}', '--slot-plan', '--restart-child',
        ],))
        child.start()
        child.join()
        if child.exitcode != 0:
            raise RuntimeError(f'Fresh-process restart failed with exit code {child.exitcode}')


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=measurement_root, required=True)
    p.add_argument('--input', type=workspace_path)
    p.add_argument('--prepare', action='store_true')
    p.add_argument('--players', type=int, default=8)
    p.add_argument('--width', type=int, default=80)
    p.add_argument('--mode', choices=('timing', 'calls', 'profile'), default='timing')
    p.add_argument('--tour-only', action='store_true', help='Save changed Tour metadata with the same large checkpoint')
    p.add_argument('--slot-plan', action='store_true',
                   help='slots-dN fixture (profile_native_week_ab.py prepare --slot-depth N): '
                        'three next-slot Saves warm / cold miss / after restart')
    p.add_argument('--input-sha256', help='required with --slot-plan: SHA-256 of --input')
    p.add_argument('--restart-child', action='store_true', help=argparse.SUPPRESS)
    a = p.parse_args(argv)
    if not a.prepare and subprocess.run(['git', 'diff', '--quiet', 'HEAD', '--', 'src'], check=False).returncode:
        raise ValueError('Commit the production source before measuring it')
    if a.slot_plan:
        return slot_main(a)
    a.root.mkdir(parents=True, exist_ok=a.restart_child)
    local = a.root / 'run.db'
    if a.prepare:
        with ApiServer(database_url=f'sqlite:///{local}') as server:
            ready(server, a.width, population=a.players)
        return
    if not a.restart_child:
        if not a.input:
            p.error('--input or --prepare is required')
        copy_database(a.input, local)
    digest = hashlib.sha256(local.read_bytes()).hexdigest()
    counts, profiles = observers(a.mode, a.root)
    rows = []
    with ApiServer(database_url=f'sqlite:///{local}') as server:
        repo = server.app.state.runtime.repository

        def phase(label, operation):
            before = {k: dict(v) for k, v in counts.items()}
            start = time.perf_counter()
            value = operation()
            elapsed = time.perf_counter() - start
            row = dict(phase=label, seconds=elapsed,
                       calls={k: {f: v[f] - before[k][f] for f in v} for k, v in counts.items()})
            if a.mode != 'timing':
                row.update(memory(repo))
            rows.append(row)
            print(json.dumps(row), flush=True)
            return value

        view = phase('restart_cold' if a.restart_child else 'cold', lambda: inspect(server))
        phase('restart_warm' if a.restart_child else 'warm', lambda: inspect(server))
        if not a.restart_child:
            original_checkpoint = view['checkpoint_fingerprint']

            def next_command(view, name, offset):
                if not a.tour_only:
                    return command(view, 'next-match', name=name)
                week = view['state']['week']
                return command(view, 'create-edition', name=name, data={
                    'schema_version': 'calendar_tournament_edition.v2',
                    'simulation_seed': 891, 'edition_id': name, 'name': name,
                    'week': {**week, 'week': week['week'] + offset},
                    'announcement_week': {**week, 'week': week['week'] + 1},
                    'start_slot': 1, 'main_entrant_count': 4, 'ranked': True,
                    'validity_weeks': week['calendar']['weeks_per_year'],
                    'point_table': {'champion': 100, 'finalist': 60, 'semifinal': 30},
                })

            prefix = 'measured-tour' if a.tour_only else 'measured'
            phase('first_command', lambda: execute(server, next_command(view, prefix + '-first', 2)))
            view = inspect(server)

            def save():
                status, receipt = _request('POST', tour_url(server) + '/save', {
                    'expected_draft_version': view['draft_version'],
                    'expected_calendar_tour_fingerprint': view['tour_fingerprint'],
                })
                assert status == 201, receipt
                return receipt

            phase('save_including_handoff', save)
            view = phase('immediate_saved_read', lambda: inspect(server))
            if a.tour_only:
                assert view['checkpoint_fingerprint'] == original_checkpoint
            phase('next_command', lambda: execute(server, next_command(view, prefix + '-next', 3)))
            view = inspect(server)
            phase('second_save', save)
            expected = inspect(server)
            if a.tour_only:
                assert expected['checkpoint_fingerprint'] == original_checkpoint
            with open_artifact(a.root, 'expected.json') as stream:
                json.dump(expected, stream, sort_keys=True)
        else:
            expected = json.loads((a.root / 'expected.json').read_text())
            assert view == expected, 'Complete inspection differs after a physical process restart'
    metadata = dict(git_sha=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                    source_tree=subprocess.check_output(['git', 'rev-parse', 'HEAD:src'], text=True).strip(),
                    script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    input_sha256=digest, python=sys.version, platform=platform.platform(), mode=a.mode,
                    tour_only=a.tour_only,
                    source_diff=subprocess.check_output(['git', 'diff', '--', 'src'], text=True))
    with open_artifact(a.root, 'restart.json' if a.restart_child else 'timings.json') as stream:
        json.dump(dict(metadata=metadata, phases=rows), stream, indent=2)
    for index, (name, profile) in enumerate(profiles):
        prefix = 'restart-' if a.restart_child else ''
        profile.create_stats()
        with open_artifact(a.root, f'{prefix}{index:02d}.pstats', binary=True) as stream:
            marshal.dump(profile.stats, stream)
        with open_artifact(a.root, f'{prefix}{index:02d}.txt') as stream:
            pstats.Stats(profile, stream=stream).strip_dirs().sort_stats('cumulative').print_stats(65)
    if not a.restart_child:
        # spawn starts a fresh interpreter and keeps the selected virtualenv.
        # Measurement values travel as Python data, never executable CLI text.
        child = multiprocessing.get_context('spawn').Process(target=main, args=([
            f'--root={a.root}', f'--mode={a.mode}', '--restart-child',
            *(['--tour-only'] if a.tour_only else []),
        ],))
        child.start()
        child.join()
        if child.exitcode != 0:
            raise RuntimeError(f'Fresh-process restart failed with exit code {child.exitcode}')


if __name__ == '__main__':
    main()
