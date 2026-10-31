"""Launcher boundary tests; the frozen Windows acceptance is a separate gate."""
from __future__ import annotations

import functools
import importlib.util
import json
import socket
import threading
from pathlib import Path
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest

SPEC = importlib.util.spec_from_file_location(
    "desktop_launcher", Path(__file__).parents[1] / "desktop/launcher.py")
launcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(launcher)


@pytest.fixture
def bundle(tmp_path):
    root = tmp_path / "program"
    (root / "config").mkdir(parents=True)
    (root / "config/seed.txt").write_text("original", encoding="utf-8")
    (root / "web/dist/assets").mkdir(parents=True)
    (root / "web/dist/index.html").write_text("<html>compiled UI</html>", encoding="utf-8")
    (root / "web/dist/assets/main.js").write_text("console.log('app');", encoding="utf-8")
    build = {"format": "squash-desktop-preview.v1", "source_commit": "a" * 40}
    (root / "build-info.json").write_text(json.dumps(build), encoding="utf-8")
    return root, build


def test_same_build_restart_preserves_world_and_edited_packages(bundle, tmp_path):
    root, build = bundle
    data = tmp_path / "data"
    with launcher.DataLock(data):
        launcher.prepare_data(root, data, build)
    (data / "config/seed.txt").write_text("user edited", encoding="utf-8")
    (data / "beta_engine.db").write_bytes(b"saved world sentinel")
    with launcher.DataLock(data):
        launcher.prepare_data(root, data, build)
    assert (data / "config/seed.txt").read_text() == "user edited"
    assert (data / "beta_engine.db").read_bytes() == b"saved world sentinel"
    assert (root / "config/seed.txt").read_text() == "original"


def test_foreign_build_and_unknown_data_fail_closed(bundle, tmp_path):
    root, build = bundle
    data = tmp_path / "data"
    with launcher.DataLock(data):
        launcher.prepare_data(root, data, build)
    before = (data / "preview-owner.json").read_bytes()
    with launcher.DataLock(data), pytest.raises(launcher.LaunchError, match="another build"):
        launcher.prepare_data(root, data, {**build, "source_commit": "b" * 40})
    assert (data / "preview-owner.json").read_bytes() == before
    unknown = tmp_path / "existing"
    unknown.mkdir()
    (unknown / "beta_engine.db").write_bytes(b"do not overwrite")
    with launcher.DataLock(unknown), pytest.raises(launcher.LaunchError, match="Unrecognized"):
        launcher.prepare_data(root, unknown, build)
    assert (unknown / "beta_engine.db").read_bytes() == b"do not overwrite"
    assert not (unknown / "config").exists()


def test_interrupted_seed_copy_never_publishes_identity(bundle, tmp_path, monkeypatch):
    root, build = bundle
    data = tmp_path / "data"

    def disk_full(source, target):
        target.mkdir()
        (target / "partial").write_bytes(b"partial")
        raise OSError("disk full")

    monkeypatch.setattr(launcher.shutil, "copytree", disk_full)
    with launcher.DataLock(data), pytest.raises(OSError, match="disk full"):
        launcher.prepare_data(root, data, build)
    assert not (data / "preview-owner.json").exists()
    assert not (data / "config").exists()
    assert list(data.iterdir()) == [data / ".preview.lock"]


def test_os_lock_prevents_second_writer_and_can_be_reacquired(tmp_path):
    with (launcher.DataLock(tmp_path),
          pytest.raises(launcher.LaunchError, match="already in use"),
          launcher.DataLock(tmp_path)):
        pytest.fail("second writer acquired the lock")
    with launcher.DataLock(tmp_path):
        pass


@pytest.mark.parametrize("port", [5173, 8000])
def test_occupied_ports_reject_before_creating_data(bundle, tmp_path, port):
    root, _ = bundle
    with socket.socket() as foreign:
        foreign.bind(("127.0.0.1", port))
        foreign.listen(1)
        data = tmp_path / "untouched"
        with pytest.raises(launcher.LaunchError, match=f"Port {port}"):
            launcher.host(root, data, threading.Event(), open_browser=False)
        assert not data.exists()
        assert foreign.getsockname()[1] == port


def test_frontend_deep_links_assets_and_private_file_boundaries(bundle, tmp_path, monkeypatch):
    root, _ = bundle
    (root / "web/secret.txt").write_text("PRIVATE SENTINEL", encoding="utf-8")
    server = launcher.FrontendServer(("127.0.0.1", 0), functools.partial(
        launcher.FrontendHandler, files=launcher.compiled_files(root / "web/dist")))
    worker = threading.Thread(target=server.serve_forever)
    worker.start()

    def no_request_paths(*args, **kwargs):
        pytest.fail("An HTTP request must never construct or resolve a filesystem path")

    monkeypatch.setattr(launcher, "Path", no_request_paths)
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        for route in ("/", "/admin", "/admin/runs/test?tab=calendar", "/viewer/run"):
            with urlopen(base + route) as response:
                assert b"compiled UI" in response.read()
                assert response.headers["Cache-Control"] == "no-store"
        with urlopen(base + "/assets/main.js") as response:
            assert "javascript" in response.headers["Content-Type"]
            assert b"console.log" in response.read()
        for route in ("/assets/", "/config/seed.txt", "/beta_engine.db",
                      "/../secret.txt", "/%2e%2e/secret.txt", "/admin/../../secret.txt",
                      "/%5c..%5csecret.txt", "/%5c%5cremote-host%5cshare%5csecret",
                      "/assets/missing.js"):
            with pytest.raises(HTTPError) as error:
                urlopen(base + route)
            assert error.value.code == 404
    finally:
        server.shutdown()
        worker.join(timeout=5)
        server.server_close()


def test_build_identity_requires_complete_package(bundle, monkeypatch):
    root, build = bundle
    assert launcher.read_build(root) == build
    monkeypatch.setenv("LOCALAPPDATA", str(root / "appdata"))
    first = launcher.default_data_dir(build)
    assert first != launcher.default_data_dir({**build, "source_commit": "b" * 40})
    (root / "web/dist/index.html").unlink()
    with pytest.raises(launcher.LaunchError, match="Incomplete"):
        launcher.read_build(root)


def test_shutdown_retains_data_lock_until_late_worker_has_stopped(bundle, tmp_path, monkeypatch):
    import uvicorn

    import beta_engine.main

    root, _ = bundle
    data = tmp_path / "data"
    release = threading.Event()
    waiting = threading.Event()
    started = threading.Event()
    stop = threading.Event()
    worker = threading.Thread(target=release.wait)
    worker.start()
    app = SimpleNamespace(state=SimpleNamespace(
        full_simulation_worker=SimpleNamespace(thread=worker)))
    monkeypatch.setattr(beta_engine.main, "create_app", lambda **kwargs: app)
    monkeypatch.setattr(launcher.logging, "basicConfig", lambda **kwargs: None)

    class FakeServer:
        def __init__(self, config):
            self.started = False
            self.should_exit = False

        def run(self, sockets):
            self.started = True
            started.set()
            while not self.should_exit:
                stop.wait(0.01)

    original_wait = launcher.wait_for_thread

    def observe_wait(thread, label):
        if label == "simulation worker":
            waiting.set()
        original_wait(thread, label)

    monkeypatch.setattr(uvicorn, "Server", FakeServer)
    monkeypatch.setattr(launcher, "wait_for_thread", observe_wait)
    failures = []

    def run():
        try:
            launcher.host(root, data, stop, open_browser=False)
        except Exception as exc:  # noqa: BLE001 - report the test thread's failure on the main thread
            failures.append(exc)

    host_thread = threading.Thread(target=run)
    host_thread.start()
    try:
        assert started.wait(10)
        stop.set()
        assert waiting.wait(10)
        with pytest.raises(launcher.LaunchError, match="already in use"), launcher.DataLock(data):
            pytest.fail("data lock released before worker stopped")
    finally:
        stop.set()
        release.set()
        host_thread.join(10)
        worker.join(10)
    assert not host_thread.is_alive()
    assert not failures
    with launcher.DataLock(data):
        pass
