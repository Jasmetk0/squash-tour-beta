"""Real HTTP/SQLite measurement of long native Tour Saved and season-archive reads.

Two subcommands, both against the production FastAPI app and SQLite:

``build``  plays the wide two-season scenario of
           ``tests/api/test_native_season_archive_wide.py`` (every week, both Season
           Transitions, real MatchEngine matches, explicit Saves) for one fixed Run
           clock. Every HTTP request is timed and written to ``build-requests.jsonl``.
           A consistent SQLite backup is retained after each closed season; these
           backups are the authentic inputs for ``read``.

``read``   copies one immutable input (SQLite backup API, input opened read-only),
           starts the server in a NEW OS process and measures, in order:
           cold reads, repeated (warm) reads, one ordinary Week Transition plus an
           explicit Save, reads after that Save, then a cold restart (another new
           process) with complete JSON equality against the pre-restart values.
           Server memory comes from ``/proc/<pid>/status`` (VmRSS / VmHWM).

``--profile`` (read only) wraps the server process in cProfile and writes one
``.pstats`` per phase. Profile runs are diagnostics and are never timing samples.

Cold means a fresh process, repository and in-memory proof caches; OS page caches
are not flushed. The script refuses to measure uncommitted production source.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import signal
import socket
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from urllib import error, request

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT), str(ROOT / 'tests' / 'api')]

# The normal acceptance transport bound. A read slower than this is a failed,
# censored observation, never a completed latency.
TRANSPORT_TIMEOUT = 120
TOUR = '/admin/runs/run/branches/branch/calendar-tour'
READS = (
    ('tour', ''),
    ('archive', '/seasons'),
    ('season0', '/seasons/0'),
    ('season1', '/seasons/1'),
    ('season1_vs_0', '/seasons/1?compare_to=0'),
    ('season0_vs_1', '/seasons/0?compare_to=1'),
)
CLOSED_SEASON_READS = ('season0', 'season1', 'season1_vs_0', 'season0_vs_1')


def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def environment():
    def git(*args):
        return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()
    return {
        'git_sha': git('rev-parse', 'HEAD'), 'source_tree': git('rev-parse', 'HEAD:src'),
        'script_sha256': sha256(__file__), 'python': sys.version.split()[0],
        'platform': platform.platform(), 'cpu_count': os.cpu_count(),
        'dependencies': {name: importlib.metadata.version(name) for name in
                         ('fastapi', 'pydantic', 'sqlalchemy', 'uvicorn')},
    }


def require_committed_source():
    if subprocess.run(['git', 'diff', '--quiet', 'HEAD', '--', 'src'], check=False, cwd=ROOT).returncode:
        raise SystemExit('Commit production source before measuring')


def backup(source, target):
    """Consistent copy; the source is opened read-only and both handles are closed."""
    src = sqlite3.connect(Path(source).resolve().as_uri() + '?mode=ro', uri=True)
    dst = sqlite3.connect(target)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()


def data_size(database):
    con = sqlite3.connect(Path(database).resolve().as_uri() + '?mode=ro', uri=True)
    try:
        rows, payload, largest = con.execute(
            'SELECT COUNT(*), SUM(LENGTH(payload_json)), MAX(LENGTH(payload_json)) '
            'FROM branch_saved_revisions').fetchone()
    finally:
        con.close()
    return {'sqlite_bytes': Path(database).stat().st_size, 'saved_revisions': rows,
            'saved_payload_bytes': payload, 'largest_saved_payload_bytes': largest}


# --------------------------------------------------------------------------- build

def build(args):
    require_committed_source()
    import tests.api.test_saved_revision_history_api as history_api
    from tests.api.test_calendar_global_slots import ready
    from tests.api.test_calendar_tour_flow import inspect
    from tests.api.test_native_season_archive_wide import (
        plan_second_season,
        play_season_editions,
        run_to_season_end,
    )

    args.root.mkdir(parents=True, exist_ok=False)
    log = open(args.root / 'build-requests.jsonl', 'w')  # noqa: SIM115 - closed below
    original = history_api._request
    phase = {'name': 'setup'}

    def timed(method, url, payload=None):
        start = time.perf_counter()
        code, body = original(method, url, payload)
        seconds = time.perf_counter() - start
        path = url.split('/calendar-tour', 1)[-1] if '/calendar-tour' in url else url.split('/', 3)[-1]
        log.write(json.dumps({'phase': phase['name'], 'method': method, 'path': path.split('?')[0],
                              'status': code, 'seconds': seconds}) + '\n')
        log.flush()
        return code, body

    # Every helper imported the function object by name; patch each module's binding.
    for module in list(sys.modules.values()):
        if getattr(module, '_request', None) is original:
            module._request = timed
    database = args.root / 'build.db'
    manifest = {'environment': environment(), 'width': args.width, 'inputs': {}}
    started = time.perf_counter()
    with history_api.ApiServer(database_url=f'sqlite:///{database}') as server:
        ready(server, args.width, seasons=3)
        for season, ids in enumerate((('parallel-a', 'parallel-b'), None)):
            if ids is None:
                phase['name'] = f'season{season}-plan'
                ids = plan_second_season(server, args.width)
            phase['name'] = f'season{season}-editions'
            play_season_editions(server, ids)
            phase['name'] = f'season{season}-weeks'
            run_to_season_end(server, args.width)
            assert inspect(server)['saved_completed_seasons'] == list(range(season + 1))
            name = f'w{args.width}-after-season{season}.db'
            backup(database, args.root / name)
            manifest['inputs'][name] = {'sha256': sha256(args.root / name),
                                        'elapsed_seconds': time.perf_counter() - started,
                                        **data_size(args.root / name)}
            (args.root / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    log.close()
    manifest['total_seconds'] = time.perf_counter() - started
    (args.root / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))


# ---------------------------------------------------------------------------- read

def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


class Server:
    """The production app in its own OS process (a real cold start)."""

    def __init__(self, database, root, profile_dir=None):
        self.port = free_port()
        self.base = f'http://127.0.0.1:{self.port}'
        launcher = root / 'server_launcher.py'
        launcher.write_text(LAUNCHER)
        command = [sys.executable, str(launcher), str(database), str(self.port)]
        if profile_dir is not None:
            command.append(str(profile_dir))
        self.process = subprocess.Popen(command, cwd=ROOT)
        deadline = time.time() + 60
        while time.time() < deadline:
            try:
                request.urlopen(self.base + '/health', timeout=2).read()
                return
            except OSError:
                time.sleep(0.05)
        raise RuntimeError('server did not start')

    def memory(self):
        values = {}
        with open(f'/proc/{self.process.pid}/status') as status:
            for line in status:
                key, _, rest = line.partition(':')
                if key in ('VmRSS', 'VmHWM'):
                    values[key] = int(rest.split()[0]) * 1024
        return values

    def stop(self):
        self.process.send_signal(signal.SIGINT)
        try:
            self.process.wait(timeout=60)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()


LAUNCHER = r'''
import cProfile, signal, sys
from pathlib import Path
root = Path(__file__).resolve().parents[0]
database, port = sys.argv[1], int(sys.argv[2])
profile_dir = Path(sys.argv[3]) if len(sys.argv) > 3 else None
import os
repo = os.getcwd()
sys.path[:0] = [repo + "/src", repo]
import uvicorn
from beta_engine.main import create_app
app = create_app(database_url="sqlite:///" + database)
if profile_dir is not None:
    # Synchronous endpoints run in AnyIO worker threads; profile exactly the
    # endpoint call there. The client sends requests one at a time.
    import threading
    import fastapi.routing as fastapi_routing
    state = {"profile": cProfile.Profile(), "lock": threading.Lock()}
    original_run = fastapi_routing.run_in_threadpool
    async def profiled_run(func, *args, **kwargs):
        def call(*inner_args, **inner_kwargs):
            with state["lock"]:
                profile = state["profile"]
                profile.enable()
                try:
                    return func(*inner_args, **inner_kwargs)
                finally:
                    profile.disable()
        return await original_run(call, *args, **kwargs)
    fastapi_routing.run_in_threadpool = profiled_run
    def rotate(*_):
        # Phase boundary requested by the client: dump and restart the profile.
        with state["lock"]:
            name = (profile_dir / "next-phase").read_text().strip()
            state["profile"].dump_stats(str(profile_dir / (name + ".pstats")))
            state["profile"] = cProfile.Profile()
    signal.signal(signal.SIGUSR1, rotate)
uvicorn.run(app, host="127.0.0.1", port=port, log_level="error")
'''


def http(method, url, payload=None):
    body = None if payload is None else json.dumps(payload).encode()
    req = request.Request(url, data=body, method=method)
    req.add_header('content-type', 'application/json')
    start = time.perf_counter()
    try:
        with request.urlopen(req, timeout=TRANSPORT_TIMEOUT) as response:
            raw = response.read()
            code = response.status
    except error.HTTPError as exc:
        raw, code = exc.read(), int(exc.code)
    except (TimeoutError, OSError) as exc:  # censored: the read did not complete
        return {'status': None, 'error': type(exc).__name__,
                'seconds': time.perf_counter() - start, 'timeout': True}, None
    seconds = time.perf_counter() - start
    return {'status': code, 'seconds': seconds, 'bytes': len(raw)}, raw


def read_set(server, phase, records, values, seasons=2):
    skip = set() if seasons >= 2 else {'season1', 'season1_vs_0', 'season0_vs_1'}
    for name, path in READS:
        if name in skip:
            continue
        record, raw = http('GET', server.base + TOUR + path)
        record.update(phase=phase, read=name)
        records.append(record)
        print(json.dumps(record), flush=True)
        if record.get('timeout'):
            # Censored at the transport bound: recorded, never a latency. The
            # server finishes the work; the next read waits for it.
            continue
        if raw is not None:
            values[name] = raw
        assert record['status'] == 200, (record, raw[:400] if raw else None)


def without_current_tour(value):
    if isinstance(value, dict):
        return {k: without_current_tour(v) for k, v in value.items() if k != 'source_tour_fingerprint'}
    if isinstance(value, list):
        return [without_current_tour(v) for v in value]
    return value


def tour_command(view, action, name):
    return {
        'action': action, 'command_id': name, 'edition_id': None,
        'expected_saved_head': view['saved_head_revision_id'],
        'expected_checkpoint_fingerprint': view['checkpoint_fingerprint'],
        'expected_tour_fingerprint': view['tour_fingerprint'],
        'seed': 231, 'operator_label': 'Admin',
        'audit_reason': 'Reviewed actual configured native Tour operation', 'data': {},
    }


def transition_and_save(server, records):
    """One ordinary Week Transition (preview, confirmed execute) and an explicit Save."""
    base = server.base + TOUR
    record, raw = http('GET', base)
    view = json.loads(raw)
    command = tour_command(view, 'transition', 'measurement-next-week')
    record, raw = http('POST', base + '/preview', command)
    record.update(phase='write', read='preview')
    records.append(record)
    assert record['status'] == 200, raw
    preview = json.loads(raw)
    record, raw = http('POST', base + '/execute', {
        'command': command, 'expected_preview_fingerprint': preview['preview_fingerprint'],
        'explicit_confirmation': True})
    record.update(phase='write', read='execute')
    records.append(record)
    assert record['status'] == 201, raw
    record, raw = http('GET', base)
    record.update(phase='write', read='draft_tour')
    records.append(record)
    view = json.loads(raw)
    record, raw = http('POST', base + '/save', {
        'expected_draft_version': view['draft_version'],
        'expected_calendar_tour_fingerprint': view['tour_fingerprint']})
    record.update(phase='write', read='save')
    records.append(record)
    assert record['status'] == 201, raw
    for item in records[-4:]:
        print(json.dumps(item), flush=True)
    return json.loads(raw)['saved_revision']['revision_id']


def read(args):
    require_committed_source()
    args.root.mkdir(parents=True, exist_ok=False)
    database = args.root / 'run.db'
    backup(args.input, database)
    result = {'environment': environment(), 'input': str(args.input),
              'input_sha256': sha256(args.input), 'copy_sha256_before_open': sha256(database),
              'profile': args.profile, 'data_before': data_size(database), 'phases': {}}
    profile_dir = None
    if args.profile:
        profile_dir = args.root / 'profiles'
        profile_dir.mkdir()
    records, memory = [], {}
    values = {}

    def boundary(server, name):
        memory[name] = server.memory()
        if profile_dir is not None:
            (profile_dir / 'next-phase').write_text(name)
            server.process.send_signal(signal.SIGUSR1)
            time.sleep(1.0)

    server = Server(database, args.root, profile_dir)
    try:
        memory['started'] = server.memory()
        cold = {}
        read_set(server, 'cold', records, cold, args.seasons)
        cold_values = dict(cold)
        boundary(server, 'cold')
        for repeat in range(args.repeats):
            warm = {}
            read_set(server, f'warm{repeat + 1}', records, warm, args.seasons)
            assert all(warm[k] == cold[k] for k in cold), 'repeated read changed a response'
            cold.update({k: v for k, v in warm.items() if k not in cold})
        boundary(server, 'warm')
        if not args.read_only:
            transition_and_save(server, records)
            boundary(server, 'write')
            after = {}
            read_set(server, 'after_save', records, after, args.seasons)
            boundary(server, 'after_save')
            # One more week cannot change closed seasons: their reads stay byte-identical.
            # Only the new Saved HEAD identifier and the fingerprint of the
            # current (advanced) Tour state may differ; closed seasons may not.
            for name in ('archive', *CLOSED_SEASON_READS):
                if name not in cold or name not in after:
                    continue  # censored read: nothing to compare
                old, new = json.loads(cold[name]), json.loads(after[name])
                assert old.pop('saved_head_revision_id') != new.pop('saved_head_revision_id'), name
                assert without_current_tour(old) == without_current_tour(new), name
            values = after
        else:
            values = cold
    finally:
        server.stop()
    restarted = Server(database, args.root, profile_dir)
    try:
        again = {}
        read_set(restarted, 'restart_cold', records, again, args.seasons)
        boundary(restarted, 'restart_cold')
        # Complete byte equality of every response across a real process restart.
        result['restart_equal'] = {name: again[name] == values[name] for name in values if name in again}
        assert all(result['restart_equal'].values()), result['restart_equal']
    finally:
        restarted.stop()
    result['records'] = records
    result['server_memory'] = memory
    result['data_after'] = data_size(database)
    result['response_sha256'] = {k: hashlib.sha256(v).hexdigest() for k, v in values.items()}
    # Cold responses of the immutable input: comparable across source trees.
    result['cold_response_sha256'] = {k: hashlib.sha256(v).hexdigest() for k, v in cold_values.items()}
    (args.root / 'result.json').write_text(json.dumps(result, indent=2))
    summary = {}
    for item in records:
        summary.setdefault(item['phase'], {})[item['read']] = round(item['seconds'], 3)
    print(json.dumps({'summary': summary, 'memory': memory}, indent=2))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    b = sub.add_parser('build')
    b.add_argument('--width', type=int, required=True, choices=(6, 52, 61, 80))
    b.add_argument('--root', type=Path, required=True)
    r = sub.add_parser('read')
    r.add_argument('--input', type=Path, required=True)
    r.add_argument('--root', type=Path, required=True)
    r.add_argument('--repeats', type=int, default=2)
    r.add_argument('--read-only', action='store_true')
    r.add_argument('--profile', action='store_true')
    r.add_argument('--seasons', type=int, choices=(1, 2), default=2,
                   help='closed seasons in the input (after-season0 inputs have one)')
    args = parser.parse_args(argv)
    build(args) if args.command == 'build' else read(args)


if __name__ == '__main__':
    main()
