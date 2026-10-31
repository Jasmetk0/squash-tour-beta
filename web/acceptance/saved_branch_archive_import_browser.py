"""Real Chromium/HTTP/SQLite acceptance for read-only Saved Branch import preview.

Construct a portable archive with the production MatchEngine and explicit Save,
then upload it via the actual Admin browser to an independent cold SQLite target.
Do not call /import/confirm; no archive restore is part of this gate.
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
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

API_PORT = 8023
# Match the backend's intentionally narrow DEV_ALLOWED_ORIGINS (5173 only).
WEB_PORT = 5173


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--serve", action="store_true")
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
    from tests.api.test_run_branch_archive_api import export, manual_match
    from tests.api.test_saved_revision_history_api import ApiServer, _request

    work.mkdir(exist_ok=True)
    root.mkdir(exist_ok=False)
    source_path = root / "source.sqlite"
    target_path = root / "target.sqlite"
    archive_file = root / "valid-browser-source.sqbranch"
    tampered_file = root / "tampered-browser-source.sqbranch"

    with ApiServer(database_url=f"sqlite:///{source_path}") as source:
        run_id, branch_id, match, saved = manual_match(source)
        saved_head = saved["saved_revision"]["revision_id"]
        raw, reviewed_export = export(source, run_id, branch_id)
        assert match["result"], "Source must use an actual completed MatchEngine result"
        assert reviewed_export["selected_head_revision_id"] == saved_head
        archive = Archive(raw)
        assert archive.run.run_id == run_id
        archive_file.write_bytes(raw)
        tampered = bytearray(raw)
        tampered[-1] ^= 1
        tampered_file.write_bytes(tampered)
        source_state = _dump(source_path)
    assert source_state == _dump(source_path)

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
                "localStorage.setItem('squash-engine-language-v1', 'en')"
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
            assert page.get_by_role("button", name="Restore", exact=True).count() == 0

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
            result = first.json()
            assert result["can_restore"] and not result["conflicts"], result
            assert result["archive_digest"] == hashlib.sha256(raw).hexdigest()
            assert result["archive_size_bytes"] == len(raw)
            assert result["selected_branch_id"] == branch_id
            assert result["selected_head_revision_id"] == saved_head
            expect(page.get_by_text(
                "The archive is verified and currently has no target identity conflicts."
            )).to_be_visible(timeout=20000)
            expect(page.get_by_text(run_id, exact=True)).to_be_visible()
            assert _dump(target_path) == baseline, "Import preview wrote to the cold SQLite target"
            assert len(requests) == 1 and requests[0].endswith("/import/preview"), requests
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
                {"display_name": archive.run.display_name},
            )
            assert code == 201, collision_run
            colliding_state = _dump(target_path)
            picker.set_input_files(str(archive_file))
            with page.expect_response(
                lambda resp: resp.request.method == "POST" and
                resp.url.endswith("/admin/run-archives/import/preview"),
                timeout=180000,
            ) as collision_review:
                page.get_by_role("button", name="Ověřit archiv a konflikty").click()
            response = collision_review.value
            assert response.status == 200, response.text()[:2000]
            result = response.json()
            assert not result["can_restore"], result
            assert any(x["code"] == "run_name_exists" for x in result["conflicts"]), result
            expect(page.get_by_text(
                "Import není možný: cílová databáze již obsahuje kolidující identity."
            )).to_be_visible()
            expect(page.get_by_text("run_name_exists", exact=False)).to_be_visible()
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
            picker.set_input_files(str(archive_file))
            with page.expect_response(
                lambda resp: resp.request.method == "POST" and
                resp.url.endswith("/admin/run-archives/import/preview"),
                timeout=180000,
            ) as reopened_review:
                page.get_by_role("button", name="Ověřit archiv a konflikty").click()
            assert reopened_review.value.status == 200
            assert not reopened_review.value.json()["can_restore"]
            expect(page.get_by_text(
                "Import není možný: cílová databáze již obsahuje kolidující identity."
            )).to_be_visible()
            assert _dump(target_path) == colliding_state
            assert len(requests) == 4, requests
            assert all(url.endswith("/import/preview") for url in requests), requests
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
                "preview_http_posts": requests, "page_errors": errors,
                "blocked_external_requests": external,
                "browser_external_deny_probe": True,
                "import_confirm_calls": 0, "restore_performed": False
            }, indent=2))
            browser.close()
    finally:
        stop_process(frontend)
        stop_process(server)
        frontend_log.close()
        backend_log.close()


if __name__ == "__main__":
    main()
