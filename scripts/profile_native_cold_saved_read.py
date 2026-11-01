"""Real HTTP/SQLite cold Saved read and ordinary Week Transition measurements.

Use the same immutable production scenario backup for both committed source trees.
Timing mode installs no profiler, call counters or heap traversal. Restart uses a
fresh interpreter and compares the entire Saved inspection without normalization.
"""

import argparse
import hashlib
import importlib.metadata
import json
import marshal
import multiprocessing
import platform
import pstats
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.profile_native_save import (
    measurement_root,
    memory,
    observers,
    open_artifact,
    workspace_path,
)
from tests.api.test_calendar_tour_flow import command, inspect, tour_url
from tests.api.test_saved_revision_history_api import ApiServer, _request


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=measurement_root)
    parser.add_argument('--input', type=workspace_path)
    parser.add_argument('--mode', choices=('timing', 'calls', 'profile'), default='timing')
    parser.add_argument('--read-only', action='store_true')
    parser.add_argument('--direct-profile', action='store_true',
                        help='Diagnostic only: profile the production inspection service without HTTP transport')
    parser.add_argument('--restart-child', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if subprocess.run(['git', 'diff', '--quiet', 'HEAD', '--', 'src'], check=False).returncode:
        raise ValueError('Commit production source before measuring')
    if not args.restart_child and not args.input:
        parser.error('--input is required')
    if args.direct_profile and (args.mode != 'profile' or not args.read_only):
        parser.error('--direct-profile requires --mode profile --read-only')
    args.root.mkdir(parents=True, exist_ok=args.restart_child)
    database = args.root / 'run.db'
    if not args.restart_child:
        # Read only the immutable input; ordinary writes use this disposable copy.
        with (sqlite3.connect(args.input.as_uri() + '?mode=ro', uri=True) as source,
              sqlite3.connect(database) as target):
            source.backup(target)
    metadata = {
        'git_sha': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'source_tree': subprocess.check_output(['git', 'rev-parse', 'HEAD:src'], text=True).strip(),
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'database_sha256_before_open': hashlib.sha256(database.read_bytes()).hexdigest(),
        'python': sys.version, 'platform': platform.platform(), 'mode': args.mode,
        'dependencies': {name: importlib.metadata.version(name) for name in
                         ('fastapi', 'pydantic', 'sqlalchemy', 'uvicorn')},
        'argv': argv if argv is not None else sys.argv[1:],
    }
    counts, profiles = observers(args.mode, args.root)
    phases = []
    failure = None
    try:
        with ApiServer(database_url=f'sqlite:///{database}') as server:
            repository = server.app.state.runtime.repository
            if args.direct_profile:
                from beta_engine.application.calendar_tour_service import (
                    CalendarTourService,
                )
                def read():
                    value = CalendarTourService(repository).inspect(run_id='run', branch_id='branch')
                    # Compare the complete JSON DTO on both sides of restart,
                    # as the actual HTTP route does (tuples become JSON arrays).
                    return json.loads(json.dumps(value))
            else:
                def read():
                    return inspect(server)

            def phase(label, operation):
                before = {key: dict(value) for key, value in counts.items()}
                row = {'phase': label}
                started = time.perf_counter()
                try:
                    value = operation()
                except BaseException as exc:
                    row['failure'] = {'type': type(exc).__name__, 'message': str(exc)}
                    raise
                else:
                    return value
                finally:
                    row['seconds'] = time.perf_counter() - started
                    row['calls'] = {key: {field: value[field] - before[key][field]
                                  for field in value} for key, value in counts.items()}
                    if args.mode != 'timing':
                        row.update(memory(repository))
                    phases.append(row)
                    print(json.dumps(row), flush=True)

            view = phase('restart_cold' if args.restart_child else 'cold', read)
            warm = phase('restart_warm' if args.restart_child else 'warm', read)
            assert json.dumps(view, sort_keys=True) == json.dumps(warm, sort_keys=True), 'Complete cold/warm inspection differs'
            if args.restart_child:
                with open_artifact(args.root, 'restart-observed.json') as stream:
                    json.dump(view, stream, sort_keys=True)
                assert json.dumps(view, sort_keys=True) == (args.root / 'expected.json').read_text(), 'Complete inspection differs after physical process restart'
            else:
                with open_artifact(args.root, 'before.json') as stream:
                    json.dump(view, stream, sort_keys=True)
                if not args.read_only:
                    cmd = command(view, 'transition', name='cold-saved-performance-transition')

                    def preview():
                        status, response = _request('POST', tour_url(server) + '/preview', cmd)
                        assert status == 200, response
                        return response

                    review = phase('continuation_preview', preview)

                    def execute():
                        status, response = _request('POST', tour_url(server) + '/execute?include_inspection=true', {
                            'command': cmd, 'expected_preview_fingerprint': review['preview_fingerprint'],
                            'explicit_confirmation': True,
                        })
                        assert status == 201, response
                        assert not response['inspection']['saved']
                        return response['inspection']

                    view = phase('continuation_execute_and_inspection', execute)

                    def save():
                        status, receipt = _request('POST', tour_url(server) + '/save', {
                            'expected_draft_version': view['draft_version'],
                            'expected_calendar_tour_fingerprint': view['tour_fingerprint'],
                        })
                        assert status == 201, receipt
                        with open_artifact(args.root, 'receipt.json') as stream:
                            json.dump(receipt, stream, sort_keys=True)
                        return receipt

                    phase('save', save)
                    view = phase('saved_get', lambda: inspect(server))
                    assert view['saved']
                with open_artifact(args.root, 'expected.json') as stream:
                    json.dump(view, stream, sort_keys=True)
    except BaseException as exc:
        failure = {'type': type(exc).__name__, 'message': str(exc)}
        raise
    finally:
        with open_artifact(args.root, 'restart.json' if args.restart_child else 'timings.json') as stream:
            json.dump({'metadata': metadata, 'phases': phases, 'failure': failure}, stream, indent=2)
        for index, (name, profile) in enumerate(profiles):
            prefix = 'restart-' if args.restart_child else ''
            profile.create_stats()
            with open_artifact(args.root, f'{prefix}{index:02d}-{name}.pstats', binary=True) as stream:
                marshal.dump(profile.stats, stream)
            with open_artifact(args.root, f'{prefix}{index:02d}-{name}.txt') as stream:
                pstats.Stats(profile, stream=stream).strip_dirs().sort_stats('cumulative').print_stats(80)
    if not args.restart_child:
        child = multiprocessing.get_context('spawn').Process(target=main, args=([
            f'--root={args.root}', f'--mode={args.mode}', '--restart-child',
            *(['--read-only'] if args.read_only else []),
            *(['--direct-profile'] if args.direct_profile else []),
        ],))
        child.start()
        child.join()
        if child.exitcode != 0:
            raise RuntimeError(f'Fresh-process restart failed: {child.exitcode}')


if __name__ == '__main__':
    main()
