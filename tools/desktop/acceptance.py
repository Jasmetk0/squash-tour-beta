"""Exercise the actual portable Windows build; never substitutes a source server."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


def get_json(path, *, timeout=30):
    with urlopen("http://127.0.0.1:8000" + path, timeout=timeout) as response:
        return json.load(response)


def config_digest(root):
    digest = hashlib.sha256()
    for path in sorted((root / "config").rglob("*")):
        if path.is_file():
            digest.update(path.relative_to(root).as_posix().encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


def child_env():
    env = os.environ.copy()
    windows = Path(env["SystemRoot"])
    env["PATH"] = os.pathsep.join([str(windows / "System32"), str(windows)])
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    return env


def launch(package, data, evidence, label, cwd, *, batch=False):
    logfile = (evidence / (label + ".log")).open("wb")
    if batch:
        # cmd requires the extra outer quote around a quoted batch filename.
        command = ('""' + str(package / "Spustit_Squash_Engine.bat")
                   + '" --no-browser --data-dir "' + str(data) + '""')
        args = '"' + os.environ["COMSPEC"] + '" /d /s /c ' + command
    else:
        args = [str(package / "SquashEnginePreview.exe"), "--no-browser", "--data-dir", str(data)]
    try:
        proc = subprocess.Popen(args, cwd=cwd, env=child_env(), stdin=subprocess.PIPE,
                                stdout=logfile, stderr=subprocess.STDOUT)
    finally:
        logfile.close()
    return proc


def wait_ready(proc):
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise AssertionError(f"Portable process exited during startup: {proc.returncode}")
        try:
            get_json("/run-containers")
            with urlopen("http://127.0.0.1:5173/admin", timeout=2) as response:
                if response.status == 200:
                    return
        except (URLError, TimeoutError, ConnectionError):
            pass
        time.sleep(0.2)
    raise AssertionError("Actual frozen application did not become ready")


def stop(proc):
    if proc.poll() is None:
        proc.stdin.write(b"\n")
        proc.stdin.flush()
        proc.wait(timeout=60)
    assert proc.returncode == 0, f"Shutdown failed: {proc.returncode}"
    for port in (8000, 5173):
        with socket.socket() as probe:
            assert probe.connect_ex(("127.0.0.1", port)) != 0, f"Port {port} still listening"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != "win32":
        raise SystemExit("This acceptance must execute the actual Windows executable on Windows.")
    from playwright.sync_api import sync_playwright

    evidence = args.evidence.resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="Squash preview "))
    package = work / "Program český prostor"
    shutil.copytree(args.package.resolve(), package)
    data = work / "Moje data žebříček"
    before = config_digest(package)
    metadata = json.loads((package / "build-info.json").read_text(encoding="utf-8"))
    processes = []
    try:
        # First run uses the actual double-click batch entry; host tools are absent.
        first = launch(package, data, evidence, "first-start", work, batch=True)
        processes.append(first)
        wait_ready(first)
        assert get_json("/world/packages", timeout=180)["packages"], "Bundled world sources were not loaded"
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page()
            try:
                page.goto("http://127.0.0.1:5173/admin/runs/new")
                page.get_by_role("combobox", name="Language / Jazyk").select_option("en")
                page.get_by_label("Unique Run name").fill("Portable Windows restart acceptance")
                page.get_by_role("button", name="Create isolated Run", exact=True).click()
                page.get_by_role("heading", name="World and Calendar copies", exact=True).wait_for(timeout=30000)
                run_url = page.url
                page.reload()
                page.get_by_role("heading", name="World and Calendar copies", exact=True).wait_for()
                page.screenshot(path=str(evidence / "created-run.png"), full_page=True)
            finally:
                browser.close()
        runs = get_json("/run-containers")
        (evidence / "created-runs.json").write_text(json.dumps(runs, indent=2), encoding="utf-8")
        # Resolve IDs from the actual detail URL rather than relying on a mock response.
        run_id = run_url.split("/runs/", 1)[1].split("/", 1)[0].split("?", 1)[0]
        detail = get_json("/run-containers/" + run_id)
        branches = get_json("/run-branches?run_id=" + run_id)["run_branches"]
        assert len(branches) == 1
        branch = branches[0]
        revision_path = ("/run-containers/" + run_id + "/branches/" + branch["branch_id"]
                         + "/saved-revisions/" + branch["saved_head_revision_id"])
        revision = get_json(revision_path)
        duplicate = launch(package, data, evidence, "duplicate-start", work)
        processes.append(duplicate)
        assert duplicate.wait(timeout=30) != 0, "Second engine unexpectedly started"
        assert get_json(revision_path) == revision
        stop(first)
        assert (data / "beta_engine.db").stat().st_size > 0
        # Restart from another CWD using the EXE directly; same build, same world.
        other_cwd = work / "Other working directory"
        other_cwd.mkdir()
        second = launch(package, data, evidence, "restart", other_cwd)
        processes.append(second)
        wait_ready(second)
        assert get_json("/run-containers/" + run_id) == detail
        assert get_json("/run-branches?run_id=" + run_id)["run_branches"] == branches
        assert get_json(revision_path) == revision
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page()
            try:
                page.goto(run_url)
                page.get_by_role("combobox", name="Language / Jazyk").select_option("en")
                page.get_by_role("heading", name="World and Calendar copies", exact=True).wait_for()
                page.screenshot(path=str(evidence / "restored-run.png"), full_page=True)
            finally:
                browser.close()
        stop(second)
        with socket.socket() as foreign:
            foreign.bind(("127.0.0.1", 8000))
            foreign.listen(1)
            untouched = work / "Port conflict must not create data"
            rejected = launch(package, untouched, evidence, "foreign-port", other_cwd)
            processes.append(rejected)
            assert rejected.wait(timeout=30) != 0
            assert not untouched.exists()
            assert foreign.getsockname()[1] == 8000
        # Ownership mismatch must leave a previously saved database byte-for-byte intact.
        database_before = (data / "beta_engine.db").read_bytes()
        owner = data / "preview-owner.json"
        original_owner = owner.read_bytes()
        changed = json.loads(original_owner)
        changed["source_commit"] = "f" * 40
        owner.write_text(json.dumps(changed), encoding="utf-8")
        rejected = launch(package, data, evidence, "different-build", work)
        processes.append(rejected)
        assert rejected.wait(timeout=30) != 0
        assert (data / "beta_engine.db").read_bytes() == database_before
        owner.write_bytes(original_owner)
        assert config_digest(package) == before, "Distributed config was modified"
        assert not list(package.rglob("*.db")), "Database leaked into program directory"
        report = {"status": "passed", "build": metadata, "run_id": run_id,
                  "revision_path": revision_path, "config_sha256": before,
                  "scope": "Portable startup, actual UI/SQLite empty Run Save, restart and launcher failures"}
        (evidence / "result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
    finally:
        for proc in processes:
            if proc.poll() is None:
                # Failure cleanup kills the test process tree, never a pre-existing service.
                subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], check=False)
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
