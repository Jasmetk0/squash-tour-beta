"""Portable internal preview host. Engine rules and Saved writers stay unchanged."""
from __future__ import annotations

import argparse
import contextlib
import functools
import json
import logging
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
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import ClassVar
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


class FrontendHandler(SimpleHTTPRequestHandler):
    """Serve only the compiled UI, with bounded SPA fallback and no listings."""

    extensions_map: ClassVar[dict] = {**SimpleHTTPRequestHandler.extensions_map,
                      ".js": "application/javascript", ".css": "text/css"}

    def send_head(self):
        path = unquote(urlsplit(self.path).path)
        relative = Path(path.lstrip("/"))
        target = (Path(self.directory) / relative).resolve()
        if not target.is_relative_to(Path(self.directory).resolve()):
            self.send_error(404)
            return None
        if path == "/" or path in ("/admin", "/viewer", "/runs", "/world") or (
            path.startswith(("/admin/", "/viewer/", "/runs/", "/world/"))
            and not target.is_file()
        ):
            self.path = "/index.html"
        return super().send_head()

    def list_directory(self, path):
        self.send_error(404)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def log_message(self, format, *args):
        logging.getLogger("desktop.frontend").info(format, *args)


class FrontendServer(ThreadingHTTPServer):
    allow_reuse_address = False
    daemon_threads = True


def reserve_api_socket() -> socket.socket:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if os.name == "nt":
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        sock.bind(("127.0.0.1", 8000))
        sock.listen(128)
        return sock
    except BaseException:
        sock.close()
        raise


def host(root: Path, data: Path, stop: threading.Event, *, open_browser: bool) -> None:
    import uvicorn

    from beta_engine.main import create_app

    # Reserve BOTH endpoints before initializing a database or opening a browser.
    # Never attach to, stop, or silently choose another existing application's port.
    try:
        frontend = FrontendServer(("127.0.0.1", 5173), functools.partial(
            FrontendHandler, directory=str(root / "web/dist")))
    except OSError as exc:
        raise LaunchError("Port 5173 is in use. Stop the other application and retry.") from exc
    try:
        api_socket = reserve_api_socket()
    except OSError as exc:
        frontend.server_close()
        raise LaunchError("Port 8000 is in use. Stop the other application and retry.") from exc
    api_thread = web_thread = None
    server = None
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
        while api_thread and api_thread.is_alive():
            api_thread.join(timeout=30)
            if api_thread.is_alive():
                print("Waiting for engine shutdown. Keep this window open.", flush=True)
        if web_thread and web_thread.is_alive():
            frontend.shutdown()
            web_thread.join(timeout=5)
        frontend.server_close()
        api_socket.close()
        os.chdir(previous_cwd)
        locks.close()


def main(argv=None) -> int:
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
