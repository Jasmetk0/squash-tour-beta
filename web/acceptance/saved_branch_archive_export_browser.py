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
from urllib.parse import urlsplit

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

    from playwright.sync_api import Error as PlaywrightError, expect, sync_playwright

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
        historical_head = saved["saved_revision"]["parent_revision_id"]
        assert historical_head and historical_head != original_head
        status, fork = _request(
            "POST",
            f"{fixture.base_url}/run-containers/{run_id}/branches",
            {"source_branch_id": branch_id, "source_saved_revision_id": historical_head},
        )
        assert status == 201, fork
        fork_id = fork["branch_id"]
        assert fork["saved_head_revision_id"] == historical_head, fork
        original_state = _dump(database)
    fixture.app.state.runtime.repository._engine.dispose()

    api = f"http://127.0.0.1:{args.api_port}"
    web = f"http://127.0.0.1:{args.web_port}"
    errors = []
    post_requests = []
    blocked_external_requests = []
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
            # Hosted Ubuntu GitHub runners reject Chromium's user-namespace
            # sandbox via AppArmor. Playwright's default launch works here;
            # this test is NOT proof of browser sandbox confinement. Instead,
            # restrict all browser HTTP requests to the isolated local servers.
            browser = pw.chromium.launch()
            context = browser.new_context(
                viewport={"width": 1440, "height": 1100},
                accept_downloads=True,
            )
            def local_http_only(route):
                address = urlsplit(route.request.url)
                if (
                    address.scheme == "http"
                    and address.hostname == "127.0.0.1"
                    and address.port in {args.api_port, args.web_port}
                ):
                    route.continue_()
                else:
                    blocked_external_requests.append(route.request.url)
                    route.abort()

            context.route("**/*", local_http_only)
            # Negative control: prove an attempted external navigation is
            # intercepted and denied by this exact browser context. The
            # reserved .invalid host must never reach DNS or the network.
            probe_url = "http://example.invalid/squash-archive-network-probe"
            probe = context.new_page()
            try:
                try:
                    probe.goto(probe_url, wait_until="domcontentloaded", timeout=10000)
                except PlaywrightError as exc:
                    # A route.abort() must produce Chromium's explicit network
                    # failure, not an unrelated navigation or browser error.
                    assert "net::ERR_FAILED" in str(exc), str(exc)
                else:
                    raise AssertionError("External navigation escaped the browser route")
            finally:
                probe.close()
            assert blocked_external_requests == [probe_url], blocked_external_requests
            blocked_external_requests.clear()

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

            # The first export above is a real unmodified backend response.
            # Now corrupt just one byte of the same-length, same-MIME payload:
            # the browser must reject it by SHA-256, without offering a file.
            extra_downloads = []
            page.on("download", lambda item: extra_downloads.append(item.suggested_filename))
            tampered = bytearray(raw)
            tampered[-1] ^= 1
            assert len(tampered) == reviewed["archive_size_bytes"]
            assert hashlib.sha256(tampered).hexdigest() != reviewed["archive_digest"]
            page.route(
                "**/admin/run-archives/export",
                lambda route: route.fulfill(
                    status=200,
                    content_type="application/vnd.squash.saved-branch+json",
                    body=bytes(tampered),
                ),
                times=1,
            )
            with page.expect_response(
                lambda response: (
                    response.request.method == "POST"
                    and response.url.endswith("/admin/run-archives/export")
                    and response.status == 200
                )
            ):
                panel.get_by_role(
                    "button", name="Stáhnout ověřený soubor .sqbranch"
                ).click()
            expect(panel.get_by_role("alert")).to_contain_text(
                "Export digest differs from reviewed preview."
            )
            expect(panel.get_by_role(
                "button", name="Stáhnout ověřený soubor .sqbranch"
            )).to_have_count(0)
            assert not extra_downloads, extra_downloads
            tampered_downloads = list(extra_downloads)
            assert len(post_requests) == 3, post_requests
            assert _dump(database) == original_state, "Digest failure performed a write"
            with page.expect_response(
                lambda response: (
                    response.request.method == "POST"
                    and response.url.endswith("/admin/run-archives/export/preview")
                )
            ) as integrity_refresh:
                panel.get_by_role("button", name="Zkusit znovu").click()
            assert integrity_refresh.value.status == 200
            expect(panel.get_by_role(
                "button", name="Stáhnout ověřený soubor .sqbranch"
            )).to_be_enabled()
            assert len(post_requests) == 4, "SHA failure must require a new explicit preview"

            # Failure injection is limited to the next browser export response.
            # The initial preview and downloaded file above came from the real
            # production HTTP/SQLite backend; this 409 explicitly tests that a
            # stale export guard never falls through to an automatic download.
            page.route(
                "**/admin/run-archives/export",
                lambda route: route.fulfill(
                    status=409,
                    content_type="application/json",
                    body=json.dumps({
                        "detail": {
                            "code": "stale_export_preview",
                            "message": "Saved HEAD changed; review a fresh preview.",
                        }
                    }),
                ),
                times=1,
            )
            with page.expect_response(
                lambda response: (
                    response.request.method == "POST"
                    and response.url.endswith("/admin/run-archives/export")
                    and response.status == 409
                )
            ):
                panel.get_by_role(
                    "button", name="Stáhnout ověřený soubor .sqbranch"
                ).click()
            expect(panel.get_by_role("alert")).to_contain_text(
                "Saved HEAD changed"
            )
            expect(panel.get_by_role(
                "button", name="Stáhnout ověřený soubor .sqbranch"
            )).to_have_count(0)
            expect(panel.get_by_role(
                "button", name="Zkusit znovu"
            )).to_be_enabled()
            assert len(post_requests) == 5, post_requests
            assert not extra_downloads, extra_downloads
            assert _dump(database) == original_state, "Stale rejection performed a write"
            with page.expect_response(
                lambda response: (
                    response.request.method == "POST"
                    and response.url.endswith("/admin/run-archives/export/preview")
                )
            ) as fresh_preview_event:
                panel.get_by_role("button", name="Zkusit znovu").click()
            assert fresh_preview_event.value.status == 200
            expect(panel.get_by_role(
                "button", name="Stáhnout ověřený soubor .sqbranch"
            )).to_be_enabled()
            assert len(post_requests) == 6, "Preview must require an explicit new click"
            assert _dump(database) == original_state

            # Prove the previously rejected client case with real persisted
            # Branch owners: a historical fork inherits the source's older
            # Saved revision and has not written an owned revision itself.
            page.goto(f"{web}/admin/runs/{run_id}/manage?branch={fork_id}")
            fork_panel = page.get_by_role("region", name="Export Saved Branch")
            expect(fork_panel).to_be_visible()
            expect(fork_panel.get_by_text(historical_head, exact=False)).to_be_visible()
            with page.expect_response(
                lambda response: (
                    response.request.method == "POST"
                    and response.url.endswith("/admin/run-archives/export/preview")
                )
            ) as fork_review_event:
                fork_panel.get_by_role("button", name="Load export preview").click()
            fork_response = fork_review_event.value
            assert fork_response.status == 200, fork_response.text()
            fork_review = fork_response.json()
            assert fork_review["selected_branch_id"] == fork_id
            assert fork_review["selected_head_revision_id"] == historical_head
            assert any(
                branch["branch_id"] == fork_id and branch["role"] == "selected"
                for branch in fork_review["branches"]
            )
            assert any(
                branch["branch_id"] == branch_id and branch["role"] == "dependency"
                for branch in fork_review["branches"]
            )
            assert any(
                revision["revision_id"] == historical_head
                and revision["original_owner_branch_id"] == branch_id
                for revision in fork_review["history"]
            )
            with page.expect_download() as inherited_event:
                fork_panel.get_by_role(
                    "button", name="Download verified .sqbranch file"
                ).click()
            inherited_file = root / "fork-inherited-head.sqbranch"
            inherited_event.value.save_as(inherited_file)
            inherited_bytes = inherited_file.read_bytes()
            inherited_hash = hashlib.sha256(inherited_bytes).hexdigest()
            assert inherited_hash == fork_review["archive_digest"]
            assert len(inherited_bytes) == fork_review["archive_size_bytes"]
            inherited_archive = Archive(inherited_bytes)
            assert inherited_archive.envelope.selected_branch_id == fork_id
            assert inherited_archive.envelope.selected_head_revision_id == historical_head
            assert _dump(database) == original_state, "Inherited fork export performed a write"
            fork_panel.screenshot(path=str(root / "fork-inherited-en.png"))

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
            assert not blocked_external_requests, blocked_external_requests
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
                        "inherited_fork_id": fork_id,
                        "inherited_fork_sha256": inherited_hash,
                        "inherited_fork_selected_head": historical_head,
                        "inherited_fork_original_owner": branch_id,
                        "inherited_fork_browser_export": True,
                        "languages": ["en", "cs"],
                        "physical_reopen": True,
                        "sqlite_unchanged": True,
                        "tampered_payload_200_rejected_by_sha256": True,
                        "tampered_payload_downloads": tampered_downloads,
                        "explicit_repreview_after_digest_failure": True,
                        "stale_409_failure_injected": True,
                        "stale_409_cleared_download": True,
                        "explicit_repreview_after_409": True,
                        "post_requests": post_requests,
                        "page_errors": errors,
                        "blocked_external_requests": blocked_external_requests,
                        "external_navigation_deny_probe_verified": True,
                        "browser_sandbox": "unsupported_by_hosted_runner; local HTTP confined",
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
