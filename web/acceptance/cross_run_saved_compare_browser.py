"""Real Chromium + HTTP/SQLite cross-Run Saved selection; no mocked API responses."""
from __future__ import annotations

import argparse
import functools
import json
import os
import subprocess
import tempfile
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import uvicorn
from playwright.sync_api import expect, sync_playwright

from beta_engine.main import create_app
from tests.support.cross_run_compare import params, snapshot
from tools.desktop.launcher import FrontendHandler, FrontendServer, compiled_files


def api(method, route, body=None):
    request = Request("http://127.0.0.1:8000" + route, method=method,
                      data=None if body is None else json.dumps(body).encode(),
                      headers={"Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=60) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        return error.code, json.load(error)


@contextmanager
def backend(database):
    app = create_app(database_url=f"sqlite:///{database}")
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="error"))
    thread = threading.Thread(target=server.run)
    thread.start()
    try:
        deadline = time.monotonic() + 30
        while True:
            try:
                if api("GET", "/health")[0] == 200:
                    break
            except (URLError, TimeoutError):
                pass
            if time.monotonic() > deadline or not thread.is_alive():
                raise AssertionError("Production API did not start")
            time.sleep(0.05)
        yield app
    finally:
        server.should_exit = True
        thread.join(20)
        assert not thread.is_alive(), "API shutdown did not finish"


def new_run(name):
    code, run = api("POST", "/run-containers", {"display_name": name})
    assert code == 201, run
    code, branches = api("GET", "/run-branches?" + urlencode({"run_id": run["run_id"]}))
    assert code == 200
    return run["run_id"], run["viewer_branch_id"], branches["run_branches"][0]["saved_head_revision_id"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    artifacts = args.artifacts.resolve()
    artifacts.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parents[2]
    with tempfile.TemporaryDirectory(prefix="cross-saved-browser-") as directory:
        database = Path(directory) / "browser.db"
        web = FrontendServer(("127.0.0.1", 5173), functools.partial(
            FrontendHandler, files=compiled_files(root / "web/dist")))
        web_thread = threading.Thread(target=web.serve_forever)
        web_thread.start()
        try:
            with backend(database):
                a, b = new_run("Saved comparison A"), new_run("Saved comparison B")
                code, fork = api("POST", f"/run-containers/{a[0]}/branches", {
                    "source_branch_id": a[1], "source_saved_revision_id": a[2]})
                assert code == 201, fork
                selected = (a[0], fork["branch_id"], a[2])
                draft = f"/run-containers/{a[0]}/branches/{fork['branch_id']}/working-draft"
                code, staged = api("PUT", draft + "/viewer-branch", {
                    "viewer_branch_id": fork["branch_id"], "expected_draft_version": 0})
                assert code == 200, staged
                code, saved = api("POST", draft + "/save", {"expected_draft_version": staged["draft_version"]})
                assert code == 201, saved
                route = "/admin/cross-run-compare?" + urlencode(params(selected, b))
                code, comparison = api("GET", route)
                assert code == 200, comparison
                assert comparison["from_source"]["revision"]["is_shared_revision"]
                assert comparison["from_source"]["revision"]["revision_branch_id"] == a[1]
                before = snapshot(database)
                writes, comparisons, page_errors = [], [], []
                with sync_playwright() as playwright:
                    options = {"headless": True}
                    if os.environ.get("SQUASH_BROWSER_EXECUTABLE"):
                        options["executable_path"] = os.environ["SQUASH_BROWSER_EXECUTABLE"]
                    browser = playwright.chromium.launch(**options)
                    page = browser.new_page(viewport={"width": 1440, "height": 1080})
                    page.on("pageerror", lambda error: page_errors.append(str(error)))
                    page.on("request", lambda req: writes.append(req.url)
                            if req.method not in ("GET", "HEAD", "OPTIONS") else None)
                    page.on("request", lambda req: comparisons.append(req.url)
                            if "/admin/cross-run-compare?" in req.url else None)
                    try:
                        page.goto("http://127.0.0.1:5173/admin/compare-runs")
                        page.get_by_role("combobox", name="Language / Jazyk").select_option("en")
                        for side, source in (("A", selected), ("B", b)):
                            page.get_by_label(side + " Run", exact=True).select_option(source[0])
                            page.get_by_label(side + " Branch", exact=True).select_option(source[1])
                            page.get_by_label(side + " Saved Revision", exact=True).select_option(source[2])
                        assert comparisons == []
                        page.get_by_role("button", name="Compare", exact=True).click()
                        table = page.get_by_role("table", name="Cross-Run comparison table")
                        expect(table).to_be_visible()
                        page.get_by_role("button", name="Inspect run:run_id", exact=True).click()
                        detail = page.get_by_label("Cross-Run difference detail", exact=True)
                        expect(detail).to_contain_text(a[0])
                        expect(detail).to_contain_text(b[0])
                        page.screenshot(path=str(artifacts / "cross-run-en.png"), full_page=True)
                        count = len(comparisons)
                        page.get_by_label("Cross-Run display filter", exact=True).select_option("all")
                        expect(table.locator("tbody tr")).to_have_count(
                            len(comparison["run_changes"]) + len(comparison["branch_changes"]) + len(comparison["components"]))
                        assert len(comparisons) == count
                        page.get_by_role("button", name="Swap A/B", exact=True).click()
                        expect(table).to_have_count(0)
                        assert len(comparisons) == count
                        expect(page.get_by_label("A Run", exact=True)).to_have_value(b[0])
                        page.get_by_role("button", name="Compare", exact=True).click()
                        expect(table).to_be_visible()
                        count = len(comparisons)
                        page.get_by_role("combobox", name="Language / Jazyk").select_option("cs")
                        expect(page.get_by_role("heading", name="Porovnání uložených stavů mezi Runy")).to_be_visible()
                        expect(page.get_by_label("A Run", exact=True)).to_have_value(b[0])
                        assert len(comparisons) == count
                        page.screenshot(path=str(artifacts / "cross-run-cs.png"), full_page=True)
                        page.reload()
                        expect(page.get_by_role("table", name="Tabulka porovnání Runů")).to_be_visible()
                        assert writes == [], writes
                        assert page_errors == [], page_errors
                    finally:
                        browser.close()
                assert snapshot(database) == before, "Browsing altered authoritative SQLite rows"
                assert api("GET", "/admin/cross-run-compare?" + urlencode(params((a[0], a[1], b[2]), b)))[0] == 404
            with backend(database):
                assert api("GET", route) == (200, comparison)
                assert snapshot(database) == before
            report = {"status": "passed", "source_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
                "a": selected, "b": b, "shared_original_branch": a[1],
                "browser_mutations": writes, "page_errors": page_errors, "comparison_requests": len(comparisons),
                "scope": "Actual selectors, shared ancestor, GET comparison, local filters, explicit Swap/Compare, CS/EN, reload, SQLite restart and non-mutation"}
            (artifacts / "result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
            print(json.dumps(report, indent=2))
        finally:
            web.shutdown()
            web_thread.join(10)
            web.server_close()


if __name__ == "__main__":
    main()
