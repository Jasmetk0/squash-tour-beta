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


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=measurement_root, required=True)
    p.add_argument('--input', type=workspace_path)
    p.add_argument('--prepare', action='store_true')
    p.add_argument('--players', type=int, default=8)
    p.add_argument('--width', type=int, default=80)
    p.add_argument('--mode', choices=('timing', 'calls', 'profile'), default='timing')
    p.add_argument('--tour-only', action='store_true', help='Save changed Tour metadata with the same large checkpoint')
    p.add_argument('--restart-child', action='store_true', help=argparse.SUPPRESS)
    a = p.parse_args(argv)
    if not a.prepare and subprocess.run(['git', 'diff', '--quiet', 'HEAD', '--', 'src'], check=False).returncode:
        raise ValueError('Commit the production source before measuring it')
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
            (a.root / 'expected.json').write_text(json.dumps(expected, sort_keys=True))
        else:
            expected = json.loads((a.root / 'expected.json').read_text())
            assert view == expected, 'Complete inspection differs after a physical process restart'
    metadata = dict(git_sha=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                    source_tree=subprocess.check_output(['git', 'rev-parse', 'HEAD:src'], text=True).strip(),
                    script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    input_sha256=digest, python=sys.version, platform=platform.platform(), mode=a.mode,
                    tour_only=a.tour_only,
                    source_diff=subprocess.check_output(['git', 'diff', '--', 'src'], text=True))
    (a.root / ('restart.json' if a.restart_child else 'timings.json')).write_text(
        json.dumps(dict(metadata=metadata, phases=rows), indent=2))
    for index, (name, profile) in enumerate(profiles):
        prefix = 'restart-' if a.restart_child else ''
        target = a.root / f'{prefix}{index:02d}'
        profile.dump_stats(str(target) + '.pstats')
        with Path(str(target) + '.txt').open('w') as stream:
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
