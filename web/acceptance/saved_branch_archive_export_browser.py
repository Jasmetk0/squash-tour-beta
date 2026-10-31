"""Real Chromium Saved Branch export: reviewed bytes, CS/EN, no write, cold reopen.

Requires existing production HTTP/SQLite writers, a real Save and the merged
archive v1. This is NOT the whole Run/50-season archive or release acceptance.
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

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--api-port", type=int, default=8022)
    parser.add_argument("--web-port", type=int, default=5173)
    parser.add_argument("--serve", action="store_true")
    args = parser.parse_args()
    work = Path(__file__).resolve().parents[2] / "work"
    root = args.root.resolve()
    if root.parent != work.resolve() or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9_-]{0,100}", root.name
    ):
        raise ValueError("Browser evidence must be a single work/<case-name> directory")
    if args.serve:
        if not root.is_dir():
            raise ValueError("Use existing browser acceptance fixture directory")
    else:
        work.mkdir(exist_ok=True)
        root.mkdir(exist_ok=False)
    database = root / "source.sqlite"
    db = f"sqlite:///{database}"
    if args.serve:
        import uvicorn
        from beta_engine.main import create_app

        uvicorn.run(
            create_app(database_url=db),
            host="127.0.0.1",
            port=args.api_port,
            log_level="warning",
        )
        return

    from playwright.sync_api import expect, sync_playwright

    from beta_engine.domain.run_branch_archive import Archive
    from scripts.native_tour_browser_acceptance import stop_process, wait_http
    from tests.api.test_run_branch_archive_api import manual_match
    from tests.api.test_player_generation_calendar_gate import _dump
    from tests.api.test_saved_revision_history_api import ApiServer, _request

    if database.exists():
        raise ValueError("Use a fresh acceptance directory, never overwrite prior evidence")
    with ApiServer(database_url=db) as fixture:
        run_id, branch_id, played, saved = manual_match(fixture)
        original_head = saved["saved_revision"]["revision_id"]
        original_state = _dump(database)
    fixture.app.state.runtime.repository._engine.dispose()

    api = f"http://127.0.0.1:{args.api_port}"
    web = f"http://127.0.0.1:{args.web_port}"
    errors = []
    post_requests = []
    backend_log = (root / "backend.log").open("w")
    frontend_log = (root / "frontend.log").open("w")

    def start_backend():
        process = subprocess.Popen(
            [
                sys.executable, __file__, "--serve",
                "--root", str(root), "--api-port", str(args.api_port),
            ],
            stdout=backend_log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        wait_http(api + "/health", process)
        return process

    server = start_backend()
    frontend = subprocess.Popen(
        [
            "npm", "--prefix", "web", "run", "dev", "--",
            "--host", "127.0.0.1", "--port", str(args.web_port), "--strictPort"
        ],
        env={**os.environ, "VITE_API_BASE_URL": api},
        stdout=frontend_log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    try:
        wait_http(web, frontend)
        with sync_playwright() as pw:
            browser = pw.chromium.launch(args=["--no-sandbox"])
            context = browser.new_context(
                viewport={"width": 1440, "height": 1100},
                accept_downloads=True,
            )
            context.add_init_script(
                "localStorage.setItem('squash-engine-language-v1', 'en')"
            )
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on(
                "request",
                lambda request: post_requests.append(
                    {"method": request.method, "url": request.url}
                ) if request.method in ("POST", "PATCH", "PUT", "DELETE") else None,
            )
            page.goto(
                f"{web}/admin/runs/{run_id}/manage?branch={branch_id}"
            )
            panel = page.get_by_role("region", name="Export Saved Branch")
            expect(panel).to_be_visible()
            expect(panel.get_by_text(original_head, exact=False)).to_be_visible()
            expect(
                panel.get_by_role(
                    "button", name="Download verified .sqbranch file"
                )
            ).to_have_count(0)
            assert not post_requests, post_requests
            with page.expect_response(
                lambda response: (
                    response.request.method == "POST"
                    and response.url.endswith("/admin/run-archives/export/preview")
                )
            ) as preview_event:
                panel.get_by_role(
                    "button", name="Load export preview", exact=True
                ).click()
            response = preview_event.value
            assert response.status == 200, response.text()
            reviewed = response.json()
            expect(
                panel.get_by_role(
                    "button", name="Download verified .sqbranch file"
                )
            ).to_be_enabled()
            assert reviewed["selected_head_revision_id"] == original_head
            assert reviewed["selected_branch_id"] == branch_id
            assert reviewed["run_id"] == run_id
            assert reviewed["history"] and reviewed["archive_digest"]
            assert len(post_requests) == 1, post_requests
            assert _dump(database) == original_state, "Preview changed physical SQLite data"
            panel.screenshot(path=str(root / "review-en.png"))
            page.get_by_label("Language / Jazyk").select_option("cs")
            panel = page.get_by_role("region", name="Export uložené Branch")
            expect(panel.get_by_role(
                "button", name="Stáhnout ověřený soubor .sqbranch"
            )).to_be_enabled()
            assert len(post_requests) == 1, "Switching language triggered another preview"
            panel.screenshot(path=str(root / "review-cs.png"))
            with page.expect_download() as event:
                panel.get_by_role(
                    "button", name="Stáhnout ověřený soubor .sqbranch"
                ).click()
            download = event.value
            assert download.suggested_filename.endswith(".sqbranch")
            target = root / "browser-downloaded.sqbranch"
            download.save_as(target)
            raw = target.read_bytes()
            actual_hash = hashlib.sha256(raw).hexdigest()
            assert len(raw) == reviewed["archive_size_bytes"]
            assert actual_hash == reviewed["archive_digest"]
            archive = Archive(raw)
            assert archive.raw_digest == reviewed["archive_digest"]
            assert archive.envelope.selected_branch_id == branch_id
            assert archive.envelope.selected_head_revision_id == original_head
            assert {r.revision_id for r in archive.revisions} == {
                r["revision_id"] for r in reviewed["history"]
            }
            assert [b.branch_id for b in archive.branches] == [
                b["branch_id"] for b in reviewed["branches"]
            ]
            assert [r.content_hash for r in archive.revisions] == [
                r["content_hash"] for r in reviewed["history"]
            ]
            assert len(post_requests) == 2, post_requests
            assert post_requests[0]["url"].endswith("/export/preview")
            assert post_requests[1]["url"].endswith("/export")
            assert _dump(database) == original_state, "Export performed an implicit Save"
            code, draft = _request(
                "GET",
                f"{api}/run-containers/{run_id}/branches/{branch_id}/working-draft",
            )
            assert code == 200, draft
            assert draft["status"] == "clean"
            assert draft["base_saved_revision_id"] == original_head
            page.screenshot(path=str(root / "downloaded-cs.png"), full_page=True)
            stop_process(server)
            server = start_backend()
            code, reopened = _request(
                "GET",
                f"{api}/run-containers/{run_id}/branches/{branch_id}/working-draft",
            )
            assert code == 200 and reopened["base_saved_revision_id"] == original_head
            assert _dump(database) == original_state
            assert not errors, errors
            (root / "evidence.json").write_text(
                json.dumps(
                    {
                        "run_id": run_id,
                        "branch_id": branch_id,
                        "original_saved_head": original_head,
                        "reviewed_archive_digest": reviewed["archive_digest"],
                        "browser_download_sha256": actual_hash,
                        "download_bytes": len(raw),
                        "reviewed_history_count": len(reviewed["history"]),
                        "real_match_result": bool(played["result"]),
                        "languages": ["en", "cs"],
                        "physical_reopen": True,
                        "sqlite_unchanged": True,
                        "post_requests": post_requests,
                        "page_errors": errors,
                    },
                    indent=2,
                )
            )
            browser.close()
    finally:
        stop_process(frontend)
        stop_process(server)
        backend_log.close()
        frontend_log.close()


if __name__ == "__main__":
    main()
