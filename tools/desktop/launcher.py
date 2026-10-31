"""Portable internal preview host. Engine rules and Saved writers stay unchanged."""
from __future__ import annotations

import argparse
import contextlib
import functools
import json
import logging
import mimetypes
import multiprocessing
import os
import re
import shutil
import signal
import socket
import sys
import threading
import time
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit


class LaunchError(RuntimeError):
    """Actionable local setup error; never reset data to recover."""


def resource_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def read_build(root: Path) -> dict:
    try:
        value = json.loads((root / "build-info.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise LaunchError("Use the prepared Windows ZIP, not GitHub Code / Download ZIP.") from exc
    if (not isinstance(value, dict) or value.get("format") != "squash-desktop-preview.v1"
            or not re.fullmatch(r"[0-9a-f]{40}", str(value.get("source_commit", "")))):
        raise LaunchError("Invalid build identity. Download the complete Windows ZIP again.")
    if not (root / "config").is_dir() or not (root / "web/dist/index.html").is_file():
        raise LaunchError("Incomplete ZIP. Extract the whole folder before starting.")
    return value


def default_data_dir(build: dict) -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if not base:
        base = str(Path.home() / ".local/share")
    return Path(base) / "SquashEngine" / "Preview" / build["source_commit"]


class DataLock:
    """OS-owned lock releases even after a crash; no stale PID-file takeover."""

    def __init__(self, directory: Path):
        self.directory = directory
        self.file = None

    def __enter__(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        self.file = (self.directory / ".preview.lock").open("a+b")
        try:
            if os.name == "nt":
                import msvcrt
                self.file.seek(0, 2)
                if self.file.tell() == 0:
                    self.file.write(b"0")
                    self.file.flush()
                self.file.seek(0)
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self.file.close()
            self.file = None
            raise LaunchError("This data folder is already in use. Stop the other engine first.") from exc
        return self

    def __exit__(self, *args):
        if self.file:
            self.file.close()
            self.file = None


def prepare_data(root: Path, data: Path, build: dict) -> None:
    """Copy seed configuration once. Never overwrite an existing world's files."""
    marker = data / "preview-owner.json"
    if marker.exists():
        try:
            owner = json.loads(marker.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise LaunchError("Unreadable data identity. Keep this folder and restore a backup.") from exc
        if owner != {"format": build["format"], "source_commit": build["source_commit"]}:
            raise LaunchError("Data belongs to another build. Automatic migration is not supported.")
        if not (data / "config").is_dir():
            raise LaunchError("Existing data is incomplete. Restore its backup; nothing was reset.")
        return
    if any(p.name != ".preview.lock" for p in data.iterdir()):
        raise LaunchError("Unrecognized existing data. Select a new empty folder; nothing was overwritten.")
    staging = data / ("config-preparing-" + uuid.uuid4().hex)
    try:
        shutil.copytree(root / "config", staging)
        staging.rename(data / "config")
        temporary = data / "preview-owner.preparing"
        temporary.write_text(json.dumps({
            "format": build["format"], "source_commit": build["source_commit"],
        }), encoding="utf-8")
        temporary.replace(marker)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def compiled_files(directory: Path) -> dict[str, tuple[bytes, str]]:
    """Build the public URL map from trusted build outputs, never request paths."""
    files = {}
    for path in directory.rglob("*"):
        if path.is_symlink():
            raise LaunchError("The compiled UI must not contain symbolic links.")
        if path.is_file():
            media_type = {".js": "application/javascript", ".css": "text/css"}.get(path.suffix)
            media_type = media_type or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            files["/" + path.relative_to(directory).as_posix()] = (path.read_bytes(), media_type)
    if "/index.html" not in files:
        raise LaunchError("The compiled UI is incomplete. Extract the whole ZIP.")
    return files


class FrontendHandler(BaseHTTPRequestHandler):
    """Only an exact public asset lookup or a bounded SPA route can read a file."""

    def __init__(self, *args, files: dict[str, tuple[bytes, str]], **kwargs):
        self.files = files
        super().__init__(*args, **kwargs)

    def do_GET(self):
        self.send_asset(body=True)

    def do_HEAD(self):
        self.send_asset(body=False)

    def send_asset(self, *, body: bool):
        try:
            path = unquote(urlsplit(self.path).path, errors="strict")
        except (UnicodeError, ValueError):
            self.send_error(404)
            return
        if "\\" in path or "\x00" in path or ".." in path.split("/"):
            self.send_error(404)
            return
        # A URL never becomes a filesystem path (including UNC/device paths on
        # Windows). All public bytes were loaded from trusted files at startup.
        asset = self.files.get(path)
        if asset is None and (path == "/" or re.match(r"^/(admin|viewer|runs|world)(/|$)", path)):
            asset = self.files["/index.html"]
        if asset is None:
            self.send_error(404)
            return
        content, media_type = asset
        self.send_response(200)
        self.send_header("Content-Type", media_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        if body:
            self.wfile.write(content)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def log_message(self, format, *args):
        logging.getLogger("desktop.frontend").info(format, *args)


class FrontendServer(ThreadingHTTPServer):
    # POSIX REUSEADDR permits restart after TIME_WAIT, not a second listener.
    # Windows REUSEADDR can steal a live port; use exclusive ownership there.
    allow_reuse_address = os.name != "nt"
    daemon_threads = True

    def server_bind(self):
        if os.name == "nt":
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def reserve_api_socket() -> socket.socket:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if os.name == "nt":
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        else:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", 8000))
        sock.listen(128)
        return sock
    except BaseException:
        sock.close()
        raise


def wait_for_thread(thread: threading.Thread | None, label: str) -> None:
    while thread and thread.is_alive():
        thread.join(timeout=30)
        if thread.is_alive():
            print(f"Waiting for {label} shutdown. Keep this window open.", flush=True)


def host(root: Path, data: Path, stop: threading.Event, *, open_browser: bool) -> None:
    import uvicorn

    from beta_engine.main import create_app

    # Reserve BOTH endpoints before initializing a database or opening a browser.
    # Never attach to, stop, or silently choose another existing application's port.
    public_files = compiled_files(root / "web/dist")
    try:
        frontend = FrontendServer(("127.0.0.1", 5173), functools.partial(
            FrontendHandler, files=public_files))
    except OSError as exc:
        raise LaunchError("Port 5173 is in use. Stop the other application and retry.") from exc
    try:
        api_socket = reserve_api_socket()
    except OSError as exc:
        frontend.server_close()
        raise LaunchError("Port 8000 is in use. Stop the other application and retry.") from exc
    api_thread = web_thread = None
    server = None
    app = None
    locks = contextlib.ExitStack()
    previous_cwd = Path.cwd()
    try:
        locks.enter_context(DataLock(data))
        build = read_build(root)
        prepare_data(root, data, build)
        logging.basicConfig(filename=data / "launcher.log", encoding="utf-8",
                            level=logging.INFO, force=True)
        # Existing relative registries and package writes all live in the
        # isolated copy. The immutable distributed config is never the CWD.
        os.chdir(data)
        app = create_app(database_url="sqlite:///./beta_engine.db")
        server = uvicorn.Server(uvicorn.Config(
            app, host="127.0.0.1", port=8000, loop="asyncio", http="h11",
            ws="none", log_config=None, access_log=False,
        ))
        failures = []

        def api_main():
            try:
                server.run(sockets=[api_socket])
            except (Exception, SystemExit) as exc:
                logging.getLogger("desktop.backend").exception("Backend thread failed")
                failures.append(exc)

        api_thread = threading.Thread(target=api_main, name="desktop-api")
        api_thread.start()
        deadline = time.monotonic() + 60
        while not server.started:
            if failures or not api_thread.is_alive() or stop.is_set():
                raise LaunchError("Backend startup failed. See launcher.log; data was retained.")
            if time.monotonic() >= deadline:
                raise LaunchError("Backend startup timed out. See launcher.log.")
            time.sleep(0.05)
        web_thread = threading.Thread(target=frontend.serve_forever, name="desktop-ui")
        web_thread.start()
        print("READY http://127.0.0.1:5173", flush=True)
        if open_browser:
            webbrowser.open("http://127.0.0.1:5173")
        while not stop.wait(0.2):
            if failures or not api_thread.is_alive() or not web_thread.is_alive():
                raise LaunchError("A local server stopped. See launcher.log; saved data was retained.")
    finally:
        if server:
            server.should_exit = True
        wait_for_thread(api_thread, "engine")
        # The existing lifespan asks the dispatcher to stop but joins only for
        # five seconds. Retain ownership until an in-flight chunk has unwound;
        # do not exit a process with a still-writing daemon worker.
        worker = getattr(getattr(app, "state", None), "full_simulation_worker", None)
        if worker:
            wait_for_thread(worker.thread, "simulation worker")
        if web_thread and web_thread.is_alive():
            frontend.shutdown()
            web_thread.join(timeout=5)
        frontend.server_close()
        api_socket.close()
        os.chdir(previous_cwd)
        locks.close()


def main(argv=None) -> int:
    # Windows console supports Unicode; redirected logs otherwise use the local
    # ANSI code page and can crash on a Czech username before startup.
    for stream in (sys.stdout, sys.stderr):
        if stream and not stream.isatty():
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description="Squash Engine internal Windows preview")
    parser.add_argument("--no-browser", action="store_true", help="Do not open a browser automatically")
    parser.add_argument("--data-dir", type=Path, help="Advanced: empty or same-build test data folder")
    parser.add_argument("--version", action="store_true")
    args = parser.parse_args(argv)
    try:
        root = resource_root()
        build = read_build(root)
        if args.version:
            print(json.dumps(build, sort_keys=True))
            return 0
        data = (args.data_dir or default_data_dir(build)).resolve()
        if data == root or data.is_relative_to(root):
            raise LaunchError("Data must be outside the downloaded program folder.")
        print("Squash Engine - INTERNAL TEST BUILD / INTERNI TESTOVACI VERZE", flush=True)
        print("Source: " + build["source_commit"], flush=True)
        print("Data: " + str(data), flush=True)
        print("Save in Admin, then press ENTER here to stop. / Uloz v Adminu, pak zde stiskni ENTER.", flush=True)
        stop = threading.Event()

        def input_stop():
            try:
                input()
            except EOFError:
                return
            stop.set()

        threading.Thread(target=input_stop, name="desktop-console", daemon=True).start()
        # Ctrl+C also requests a graceful lifespan shutdown; no updater or tray.
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, lambda *_: stop.set())
        host(root, data, stop, open_browser=not args.no_browser)
        print("STOPPED / UKONCENO. Saved data retained.", flush=True)
        return 0
    except (LaunchError, OSError) as exc:
        print("ERROR / CHYBA: " + str(exc), file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    multiprocessing.freeze_support()
    sys.exit(main())
