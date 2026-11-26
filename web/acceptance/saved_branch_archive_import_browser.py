"""Real Chromium/HTTP/SQLite acceptance for cold archive restore.

Construct a portable archive with the production MatchEngine and explicit Save,
then upload it via the actual Admin browser to an independent cold SQLite target.
Verify preview isolation, then explicitly restore a whole Run and restart.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

API_PORT = 8023
# Match the backend's intentionally narrow DEV_ALLOWED_ORIGINS (5173 only).
WEB_PORT = 5173


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--custom", action="store_true")
    args = parser.parse_args()
    work = Path(__file__).resolve().parents[2] / "work"
    root = args.root.resolve()
    if root.parent != work.resolve() or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9_-]{0,100}", root.name
    ):
        raise ValueError("Browser evidence must live in one work/<case-name> directory")
    if args.serve:
        if not root.is_dir():
            raise ValueError("Target fixture directory must exist")
        import uvicorn
        from beta_engine.main import create_app

        uvicorn.run(
            create_app(database_url=f"sqlite:///{root / 'target.sqlite'}"),
            host="127.0.0.1",
            port=API_PORT,
            log_level="warning",
        )
        return

    from playwright.sync_api import Error as PlaywrightError, expect, sync_playwright

    from beta_engine.domain.run_branch_archive import Archive
    from scripts.native_tour_browser_acceptance import stop_process, wait_http
    from tests.api.test_player_generation_calendar_gate import _dump
    from tests.api.test_custom_run_archive_api import preview_command, selection
    from tests.api.test_full_run_archive_api import create_branch, full_preview
    from tests.api.test_run_branch_archive_api import archive_root, export, manual_match, raw_request
    from tests.api.test_saved_revision_history_api import ApiServer, _request

    work.mkdir(exist_ok=True)
    root.mkdir(exist_ok=False)
    source_path = root / "source.sqlite"
    target_path = root / "target.sqlite"
    archive_file = root / "valid-browser-source.sqbranch"
    tampered_file = root / "tampered-browser-source.sqbranch"
    collision_file = root / "collision-browser-source.sqbranch"
    collision_name = "Browser archive collision"

    with ApiServer(database_url=f"sqlite:///{source_path}") as source:
        run_id, branch_id, match, saved = manual_match(source)
        saved_head = saved["saved_revision"]["revision_id"]
        _, initial_export = export(source, run_id, branch_id)
        fork = create_branch(source, run_id, branch_id, initial_export["history"][0]["revision_id"])
        if args.custom:
            omitted = create_branch(source, run_id, branch_id, initial_export["history"][0]["revision_id"])
            reviewed_export, command = preview_command(source, selection(run_id, branch_id, [fork]))
            assert reviewed_export["omitted_branch_ids"] == [omitted]
        else:
            reviewed_export, command = full_preview(source, run_id, branch_id)
        status, raw = raw_request(archive_root(source) + "/export", json.dumps(command).encode())
        assert status == 200, raw[:2000]
        assert match["result"], "Source must use an actual completed MatchEngine result"
        assert reviewed_export["selected_head_revision_id"] == saved_head
        archive = Archive(raw)
        assert archive.run.run_id == run_id
        archive_file.write_bytes(raw)
        tampered = bytearray(raw)
        tampered[-1] ^= 1
        tampered_file.write_bytes(tampered)
        history_paths = [
            f"/run-containers/{run_id}/branches/{bid}/saved-revisions"
            for bid in (branch_id, fork)
        ]
        histories = [_request("GET", source.base_url + path) for path in history_paths]
        assert all(status == 200 for status, _ in histories)
        replay_path = (
            f"/admin/runs/{run_id}/branches/{branch_id}/authoritative-simulation"
            "/match-replay?group_id=standalone-match-group-1"
        )
        code, other = _request(
            "POST", source.base_url + "/run-containers", {"display_name": collision_name}
        )
        assert code == 201, other
        collision, _ = export(source, other["run_id"], other["viewer_branch_id"])
        collision_file.write_bytes(collision)
        source_state = _dump(source_path)
    assert source_state == _dump(source_path)
    source.app.state.runtime.repository._engine.dispose()
    for suffix in ("", "-wal", "-shm"):
        Path(str(source_path) + suffix).unlink(missing_ok=True)

    api = f"http://127.0.0.1:{API_PORT}"
    web = f"http://127.0.0.1:{WEB_PORT}"
    backend_log = (root / "backend.log").open("w")
    frontend_log = (root / "frontend.log").open("w")

    def start_backend():
        proc = subprocess.Popen(
            [sys.executable, __file__, "--serve", "--root", str(root)],
            stdout=backend_log, stderr=subprocess.STDOUT, start_new_session=True,
        )
        wait_http(api + "/health", proc)
        return proc

    server = start_backend()
    frontend = subprocess.Popen(
        [
            "npm", "--prefix", "web", "run", "dev", "--",
            "--host", "127.0.0.1", "--port", str(WEB_PORT), "--strictPort",
        ],
        env={**os.environ, "VITE_API_BASE_URL": api},
        stdout=frontend_log, stderr=subprocess.STDOUT, start_new_session=True,
    )
    requests: list[str] = []
    errors: list[str] = []
    external: list[str] = []

    try:
        wait_http(web, frontend)
        baseline = _dump(target_path)
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            context = browser.new_context(viewport={"width": 1400, "height": 950})

            def local_only(route):
                url = urlsplit(route.request.url)
                if url.scheme == "http" and url.hostname == "127.0.0.1" and url.port in {
                    API_PORT, WEB_PORT
                }:
                    route.continue_()
                else:
                    external.append(route.request.url)
                    route.abort()

            context.route("**/*", local_only)
            # Verify that our browser is not capable of reaching external sites.
            probe_url = "https://example.invalid/squash-import-network-deny-probe"
            probe = context.new_page()
            try:
                try:
                    probe.goto(probe_url, wait_until="domcontentloaded", timeout=10000)
                except PlaywrightError as exc:
                    assert "net::ERR_FAILED" in str(exc), str(exc)
                else:
                    raise AssertionError("Network deny probe unexpectedly succeeded")
            finally:
                probe.close()
            assert external == [probe_url], external
            external.clear()

            context.add_init_script(
                "if (!localStorage.getItem('squash-engine-language-v1')) localStorage.setItem('squash-engine-language-v1', 'en')"
            )
            page = context.new_page()
            page.on("pageerror", lambda err: errors.append(str(err)))
            page.on(
                "request",
                lambda req: requests.append(req.url)
                if req.method in {"POST", "PUT", "PATCH", "DELETE"} else None,
            )
            page.goto(web + "/admin/archive/import")
            expect(page.get_by_role("heading", name="Saved Branch import review")).to_be_visible()
            assert not requests, requests
            expect(page.get_by_role("button", name="Validate archive and conflicts")).to_be_disabled()
            assert page.get_by_role("button", name="Restore Run", exact=True).count() == 0

            picker = page.get_by_label("Select an archive up to 128 MiB")
            picker.set_input_files(str(archive_file))
            assert not requests, "Choosing a file must not trigger preview"
            review_button = page.get_by_role("button", name="Validate archive and conflicts")
            expect(review_button).to_be_enabled()
            with page.expect_response(
                lambda resp: resp.request.method == "POST" and
                resp.url.endswith("/admin/run-archives/import/preview"),
                timeout=180000,
            ) as actual_review:
                review_button.click()
            first = actual_review.value
            assert first.status == 200, first.text()[:2000]
            # Large archive histories can be evicted from Chromium's DevTools
            # response cache after the application has consumed the body.
            # Verify the actual rendered, SHA-256-bound result rather than
            # calling response.json() after the fact.
            expect(page.get_by_text(
                "The archive is verified and currently has no target identity conflicts."
            )).to_be_visible(timeout=20000)
            expect(page.get_by_text(run_id, exact=True)).to_be_visible()
            expect(page.get_by_text(branch_id, exact=True).first).to_be_visible()
            expect(page.get_by_text(saved_head, exact=True)).to_be_visible()
            expect(page.get_by_text(hashlib.sha256(raw).hexdigest(), exact=True)).to_be_visible()
            assert _dump(target_path) == baseline, "Import preview wrote to the cold SQLite target"
            assert len(requests) == 1 and requests[0].endswith("/import/preview"), requests
            expect(page.get_by_role("button", name="Restore Run")).to_be_disabled()
            scope_label = "Custom Branch selection" if args.custom else "Entire Saved Run"
            expect(page.get_by_text(scope_label, exact=True)).to_be_visible()
            page.screenshot(path=str(root / "import-clean-en.png"), full_page=True)

            # CS/EN is a presentation switch, never a new import request.
            page.get_by_role("combobox", name="Language / Jazyk").select_option("cs")
            expect(page.get_by_text(
                "Archiv je ověřený a v této chvíli nemá konflikt identit."
            )).to_be_visible()
            assert len(requests) == 1
            page.screenshot(path=str(root / "import-clean-cs.png"), full_page=True)

            # A second file must clear previously reviewed authority; the
            # tampered bytes are sent to the REAL parser and rejected.
            picker = page.get_by_label("Vybrat archiv do 128 MiB")
            picker.set_input_files(str(tampered_file))
            expect(page.get_by_text(
                "Archiv je ověřený a v této chvíli nemá konflikt identit."
            )).to_have_count(0)
            with page.expect_response(
                lambda resp: resp.request.method == "POST" and
                resp.url.endswith("/admin/run-archives/import/preview"),
                timeout=180000,
            ) as invalid_review:
                page.get_by_role("button", name="Ověřit archiv a konflikty").click()
            assert invalid_review.value.status == 409, invalid_review.value.text()[:2000]
            expect(page.get_by_role("alert")).to_be_visible()
            assert _dump(target_path) == baseline
            assert len(requests) == 2 and all(x.endswith("/import/preview") for x in requests)

            # A real persisted target-Run *name* collision blocks cold restore.
            # The creation itself is a deliberate test setup, not a browser
            # side effect of the import preview flow.
            code, collision_run = _request(
                "POST", api + "/run-containers",
                {"display_name": collision_name},
            )
            assert code == 201, collision_run
            colliding_state = _dump(target_path)
            picker.set_input_files(str(collision_file))
            with page.expect_response(
                lambda resp: resp.request.method == "POST" and
                resp.url.endswith("/admin/run-archives/import/preview"),
                timeout=180000,
            ) as collision_review:
                page.get_by_role("button", name="Ověřit archiv a konflikty").click()
            response = collision_review.value
            assert response.status == 200, response.text()[:2000]
            expect(page.get_by_text(
                "Import není možný: cílová databáze již obsahuje kolidující identity."
            )).to_be_visible()
            expect(page.get_by_text("run_name_exists", exact=False)).to_be_visible()
            expect(page.get_by_text(collision_name, exact=False).first).to_be_visible()
            assert _dump(target_path) == colliding_state
            assert all(x.endswith("/import/preview") for x in requests), requests
            page.screenshot(path=str(root / "import-collision-cs.png"), full_page=True)

            # Restart the actual backend. Same persisted target conflict
            # evidence must be observed without a hidden Save or restore.
            stop_process(server)
            server = start_backend()
            assert _dump(target_path) == colliding_state
            page.reload()
            expect(page.get_by_role("heading", name="Kontrola importu Saved Branch")).to_be_visible()
            expect(page.get_by_text(
                "Import není možný: cílová databáze již obsahuje kolidující identity."
            )).to_have_count(0)
            picker = page.get_by_label("Vybrat archiv do 128 MiB")
            picker.set_input_files(str(collision_file))
            with page.expect_response(
                lambda resp: resp.request.method == "POST" and
                resp.url.endswith("/admin/run-archives/import/preview"),
                timeout=180000,
            ) as reopened_review:
                page.get_by_role("button", name="Ověřit archiv a konflikty").click()
            assert reopened_review.value.status == 200
            # Reopened evidence must be displayed by the actual application,
            # not pulled back out of the browser's short-lived network cache.
            expect(page.get_by_text(
                "Import není možný: cílová databáze již obsahuje kolidující identity."
            )).to_be_visible()
            assert _dump(target_path) == colliding_state
            assert len(requests) == 4, requests
            assert all(url.endswith("/import/preview") for url in requests), requests

            picker.set_input_files(str(archive_file))
            page.get_by_role("button", name="Ověřit archiv a konflikty").click()
            restore = page.get_by_role("button", name="Obnovit Run")
            expect(restore).to_be_disabled(timeout=20000)
            page.get_by_label("Jméno operátora").fill("Archive browser acceptance")
            page.get_by_label("Důvod obnovy").fill("Restore a verified whole Run")
            expect(restore).to_be_disabled()
            assert _dump(target_path) == colliding_state
            page.get_by_role("checkbox", name="Potvrzuji obnovu z ověřeného souboru.").check()
            confirm_url = api + "/admin/run-archives/import/confirm?"
            committed_before_reply = []

            def lose_first_restore_response(route):
                if route.request.method != "POST" or committed_before_reply:
                    route.continue_()
                    return
                response = route.fetch(max_redirects=0, timeout=180000)
                committed_before_reply.append(response.status)
                route.abort()

            page.route(lambda url: url.startswith(confirm_url), lose_first_restore_response)
            restore.click()
            retry = page.get_by_role("button", name="Ověřit výsledek opakováním obnovy")
            expect(retry).to_be_enabled(timeout=180000)
            assert committed_before_reply == [201], committed_before_reply
            after_first_restore = _dump(target_path)
            assert after_first_restore != colliding_state
            with page.expect_response(
                lambda resp: resp.request.method == "POST"
                and "/admin/run-archives/import/confirm?" in resp.url,
                timeout=180000,
            ) as restore_response:
                retry.click()
            assert restore_response.value.status == 201, restore_response.value.text()[:2000]
            restored_link = page.get_by_role("link", name="Otevřít obnovený Run")
            expect(restored_link).to_have_attribute("href", f"/admin/runs/{run_id}")
            page.screenshot(path=str(root / "import-restored-cs.png"), full_page=True)
            confirm_requests = [url for url in requests if url.startswith(confirm_url)]
            assert len(requests) == 7 and len(confirm_requests) == 2
            assert parse_qs(urlsplit(confirm_requests[0]).query) == parse_qs(
                urlsplit(confirm_requests[1]).query
            )
            assert _dump(target_path) == after_first_restore, "Retry wrote duplicate rows"

            stop_process(server)
            server = start_backend()
            assert [_request("GET", api + path) for path in history_paths] == histories
            assert _request("GET", api + replay_path) == (200, match["stored_replay"])
            assert _request("GET", api + f"/run-containers/{collision_run['run_id']}")[0] == 200
            assert not errors, errors
            assert not external, external

            (root / "evidence.json").write_text(json.dumps({
                "source_run": run_id, "source_saved_head": saved_head,
                "archive_sha256": hashlib.sha256(raw).hexdigest(),
                "bytes": len(raw), "source_real_match": True,
                "independent_cold_target": True, "languages": ["en", "cs"],
                "clean_preview": True, "tampered_archive_rejected": True,
                "persisted_name_conflict": True, "reopened_conflict": True,
                "target_sqlite_unchanged_by_previews": True,
                "preview_http_post_count": 5, "page_errors": errors,
                "blocked_external_requests": external,
                "browser_external_deny_probe": True,
                "import_confirm_calls": 2, "restore_performed": True,
                "lost_response_exact_retry_without_writes": True,
                "restored_branch_count": 2, "archive_scope": reviewed_export["scope"], "restart_preserved_history_and_replay": True
            }, indent=2))
            browser.close()
    finally:
        stop_process(frontend)
        stop_process(server)
        frontend_log.close()
        backend_log.close()


if __name__ == "__main__":
    main()
