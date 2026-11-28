"""Real Chromium Compact snapshot: Preview -> Download, standalone validation.

Production HTTP/SQLite Saved v2 Run with three Branches; the selected Branch
has three own Saved revisions (creation, really played match, Viewer choice)
and is NOT the Viewer Branch, whose current choice was Saved by another Branch.
Also re-checks that the full and custom archives still download in the same
browser session. This is NOT the 25-season/ATP release acceptance.

Usage: python web/acceptance/compact_snapshot_export_browser.py --root work/<case>
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
from types import SimpleNamespace
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

API_PORT = 8023
WEB_PORT = 5173
SAVED_V2 = {"BETA_ENGINE_NEW_RUN_SAVED_STORAGE": "saved_v2"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--serve", action="store_true")
    args = parser.parse_args()
    work = Path(__file__).resolve().parents[2] / "work"
    root = args.root.resolve()
    if root.parent != work.resolve() or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9_-]{0,100}", root.name
    ):
        raise ValueError("Browser evidence must be a single work/<case-name> directory")
    database = root / "source.sqlite"
    db = f"sqlite:///{database}"
    if args.serve:
        import uvicorn

        from beta_engine.main import create_app

        uvicorn.run(create_app(database_url=db), host="127.0.0.1", port=API_PORT,
                    log_level="warning")
        return
    work.mkdir(exist_ok=True)
    root.mkdir(exist_ok=False)
    os.environ.update(SAVED_V2)

    from playwright.sync_api import expect, sync_playwright

    from beta_engine.domain.run_branch_archive import Archive, CompactSnapshot
    from scripts.native_tour_browser_acceptance import stop_process, wait_http
    from tests.api.test_compact_snapshot_api import (
        ENGINE_SOURCE,
        STANDALONE,
        multi_branch_run,
        stage,
    )
    from tests.api.test_player_generation_calendar_gate import _dump
    from tests.api.test_saved_revision_history_api import ApiServer, _request

    with ApiServer(database_url=db) as fixture:
        rid, t1, t2, t3, played, initial, _ = multi_branch_run(fixture)
        status, listed = _request("GET", f"{fixture.base_url}/run-branches?run_id={rid}")
        assert status == 200, listed
        names = {b["branch_id"]: b["display_name"] for b in listed["run_branches"]}
        head = next(b for b in listed["run_branches"] if b["branch_id"] == t1)[
            "saved_head_revision_id"]
        original_state = _dump(database)
    fixture.app.state.runtime.repository._engine.dispose()

    api, web = f"http://127.0.0.1:{API_PORT}", f"http://127.0.0.1:{WEB_PORT}"
    errors, posts, blocked = [], [], []
    backend_log = (root / "backend.log").open("w")
    frontend_log = (root / "frontend.log").open("w")
    server = subprocess.Popen(
        [sys.executable, __file__, "--serve", "--root", str(root)],
        env={**os.environ, **SAVED_V2}, stdout=backend_log, stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    frontend = subprocess.Popen(
        ["npm", "--prefix", "web", "run", "dev", "--", "--host", "127.0.0.1",
         "--port", str(WEB_PORT), "--strictPort"],
        env={**os.environ, "VITE_API_BASE_URL": api},
        stdout=frontend_log, stderr=subprocess.STDOUT, start_new_session=True,
    )
    evidence = {"run_id": rid, "selected_branch_id": t1, "viewer_branch_id": t3,
                "fixture": "multi_branch_run: manual match + Viewer Saves, Saved v2"}
    try:
        wait_http(api + "/health", server)
        wait_http(web, frontend)
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            context = browser.new_context(viewport={"width": 1440, "height": 1100},
                                          accept_downloads=True)

            def local_only(route):
                address = urlsplit(route.request.url)
                if address.hostname == "127.0.0.1" and address.port in {API_PORT, WEB_PORT}:
                    route.continue_()
                else:
                    blocked.append(route.request.url)
                    route.abort()

            context.route("**/*", local_only)
            context.add_init_script("localStorage.setItem('squash-engine-language-v1', 'en')")
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("request", lambda r: posts.append(r.url)
                    if r.method in ("POST", "PUT", "PATCH", "DELETE") else None)

            def is_preview(response):
                return (response.request.method == "POST"
                        and response.url.endswith("/admin/run-archives/export/preview"))

            page.goto(f"{web}/admin/runs/{rid}/manage?branch={t1}")
            panel = page.get_by_role("region", name="Export Saved Branch")
            expect(panel.get_by_text(head, exact=False).first).to_be_visible()
            panel.get_by_role("combobox", name="Export scope").select_option("compact")
            expect(panel.get_by_text("Only the current Saved state")).to_be_visible()
            assert not posts, posts
            with page.expect_response(is_preview) as event:
                panel.get_by_role("button", name="Load export preview").click()
            assert event.value.status == 200, event.value.text()
            reviewed = event.value.json()
            assert reviewed["format"] == "run_compact_snapshot.v1"
            assert reviewed["selected_head_revision_id"] == head
            assert reviewed["source_context"]["selected_is_viewer_branch"] is False
            assert _dump(database) == original_state, "Preview wrote to SQLite"
            expect(panel.get_by_text("is not the Viewer Branch")).to_be_visible()
            expect(panel.get_by_text("cannot restore a playable Run")).to_be_visible()
            expect(panel.get_by_text(reviewed["content_hash"])).to_be_visible()
            panel.screenshot(path=str(root / "compact-review-en.png"))
            page.get_by_label("Language / Jazyk").select_option("cs")
            panel = page.get_by_role("region", name="Export uložené Branch")
            expect(panel.get_by_text("Vybraná větev není Viewer Branch")).to_be_visible()
            expect(panel.get_by_text("neobnoví hratelný Run")).to_be_visible()
            panel.screenshot(path=str(root / "compact-review-cs.png"))
            assert len(posts) == 1, "Language switch re-requested the preview"
            with page.expect_download() as download:
                panel.get_by_role("button", name="Stáhnout ověřený kompaktní snapshot").click()
            assert download.value.suggested_filename == "compact-snapshot-v1.sqsnap"
            compact_file = root / "compact-snapshot-v1.sqsnap"
            download.value.save_as(compact_file)
            raw = compact_file.read_bytes()
            assert len(raw) == reviewed["archive_size_bytes"]
            assert hashlib.sha256(raw).hexdigest() == reviewed["archive_digest"]
            snapshot = CompactSnapshot(raw)
            assert snapshot.head.revision_id == head and snapshot.head.branch_id == t1
            assert initial.encode() not in raw and t3.encode() not in raw
            assert [p for p in posts if "/admin/run-archives/" in p][-1].endswith("/export")
            assert _dump(database) == original_state, "Download wrote to SQLite"
            evidence.update(compact_bytes=len(raw), compact_sha256=reviewed["archive_digest"],
                            compact_head=head, compact_head_sequence=3,
                            compact_content_hash=reviewed["content_hash"])

            # Same Saved state through the existing archive modes, same session.
            page.get_by_label("Language / Jazyk").select_option("en")
            panel = page.get_by_role("region", name="Export Saved Branch")
            sizes = {}
            for mode, extra, filename in (
                ("branch", None, "saved-branch-v1.sqbranch"),
                ("full_run", None, "full-run-v1.sqbranch"),
                ("custom", t2, "custom-run-v1.sqbranch"),
            ):
                panel.get_by_role("combobox", name="Export scope").select_option(mode)
                if extra:
                    panel.get_by_role("checkbox", name=names[extra], exact=True).check()
                with page.expect_response(is_preview, timeout=180000) as event:
                    panel.get_by_role("button", name="Load export preview").click()
                assert event.value.status == 200, event.value.text()
                preview = event.value.json()
                with page.expect_download() as download:
                    panel.get_by_role("button", name="Download verified .sqbranch file").click()
                assert download.value.suggested_filename == filename
                target = root / filename
                download.value.save_as(target)
                archive = Archive(target.read_bytes())
                assert archive.raw_digest == preview["archive_digest"]
                same = next(r for r in archive.revisions if r.revision_id == head)
                assert same.model_dump() == snapshot.head.model_dump()
                sizes[mode] = {"bytes": archive.size, "revisions": len(archive.revisions),
                               "branches": len(archive.branches)}
            assert _dump(database) == original_state
            evidence["existing_archives_same_state"] = sizes

            # Unsaved change after Preview blocks Download; nothing is Saved.
            panel.get_by_role("combobox", name="Export scope").select_option("compact")
            with page.expect_response(is_preview) as event:
                panel.get_by_role("button", name="Load export preview").click()
            assert event.value.status == 200
            draft, version = stage(SimpleNamespace(base_url=api), rid, t1, t1)
            dirty_state = _dump(database)
            panel.get_by_role("button", name="Download verified compact snapshot").click()
            expect(panel.get_by_role("alert")).to_contain_text("Unsaved edits block export")
            assert _dump(database) == dirty_state
            # Explicit Save changes HEAD: the old review cannot download.
            status, saved = _request("POST", draft + "/save", {"expected_draft_version": version})
            assert status == 201, saved
            new_head = saved["saved_revision"]["revision_id"]
            expect(panel.get_by_role(
                "button", name="Download verified compact snapshot")).to_have_count(0)
            page.reload()
            panel = page.get_by_role("region", name="Export Saved Branch")
            panel.get_by_role("combobox", name="Export scope").select_option("compact")
            with page.expect_response(is_preview) as event:
                panel.get_by_role("button", name="Load export preview").click()
            fresh = event.value.json()
            assert fresh["selected_head_revision_id"] == new_head != head
            with page.expect_download() as download:
                panel.get_by_role("button", name="Download verified compact snapshot").click()
            fresh_file = root / "compact-after-save.sqsnap"
            download.value.save_as(fresh_file)
            assert hashlib.sha256(fresh_file.read_bytes()).hexdigest() == fresh["archive_digest"]
            assert CompactSnapshot(fresh_file.read_bytes()).head.sequence == 4
            evidence.update(unsaved_blocked_download=True, head_change_required_new_preview=True,
                            fresh_head=new_head)
            browser.close()
    finally:
        stop_process(frontend)
        stop_process(server)
        backend_log.close()
        frontend_log.close()

    # Standalone validation: isolated interpreter, empty cwd, no SQLite connect.
    reader = root / "standalone-reader"
    reader.mkdir()
    result = subprocess.run([sys.executable, "-I", "-c", STANDALONE, str(compact_file), ENGINE_SOURCE],
                            cwd=reader, capture_output=True, text=True, timeout=120, check=True)
    validated = json.loads(result.stdout)
    assert validated == {k: v for k, v in reviewed.items() if k != "source_context"}, validated
    assert list(reader.iterdir()) == []
    assert not errors, errors
    assert not blocked, blocked
    evidence.update(standalone_validation=validated["verified_uses"], page_errors=errors,
                    languages=["en", "cs"], played_match=bool(played["result"]),
                    sqlite_unchanged_by_preview_and_download=True)
    (root / "evidence.json").write_text(json.dumps(evidence, indent=2))
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
