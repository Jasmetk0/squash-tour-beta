"""Real native/fork fixture transfer; exact original proofs survive a cold target."""

from pathlib import Path

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.run_branch_archive import decode, encode
from tests.api.test_calendar_native_birth_week_execution import sign_prospects
from tests.api.test_calendar_tour_flow import setup
from tests.api.test_native_fork_public_continuation import Tour, fork
from tests.api.test_player_generation_calendar_gate import _dump
from tests.api.test_run_branch_archive_api import (
    archive_root,
    confirm,
    export,
    raw_request,
    upload_preview,
)
from tests.api.test_run_branch_archive_boundaries import resign, rewrite
from tests.api.test_saved_revision_history_api import ApiServer, _request
from tests.support.fax_reference import compute_source_tree_hash
from tests.support.run_branch_archive_http import ColdApiServer

pytestmark = pytest.mark.smoke


def test_native_fork_cold_restore_original_history_calendar_and_continuation(
    tmp_path, monkeypatch
):
    source, target = tmp_path / "native-A.db", tmp_path / "native-B.db"
    fax = Path("config/world_packages/official_fax_world").resolve()
    fax_hash = compute_source_tree_hash(fax)
    clock = RunCalendar(7, 1, 2030, 3)
    with ApiServer(database_url=f"sqlite:///{source}") as server:
        repo, _ = setup(server, clock, 4)
        signed = sign_prospects(server, repo, clock)
        created = fork(server, signed["revision_id"])
        bid = created["branch_id"]
        tour = Tour(server, bid)
        # The actual fork crosses a real native birth boundary and explicitly
        # Saves using the established runtime writer; no fixture re-signing.
        tour.execute("transition", "portable-fork-birth")
        saved = tour.save()
        view = tour.view()
        original_saved_payload = repo.get_branch_saved_revision(
            revision_id=saved["revision_id"]
        ).payload
        assert any(p["player_id"] == "born-native-15" for p in view["players"])
        history_url = f"/run-containers/run/branches/{bid}/saved-revisions"
        history = _request("GET", server.base_url + history_url)
        assert history[0] == 200, history
        before = _dump(source)
        raw, preview = export(server, "run", bid)
        assert _dump(source) == before
        assert len(preview["branches"]) == 2
        assert "run_prospect_source" in preview["included_components"]
        assert "native_fork_runtime" in preview["included_components"]
        assert "run_package_state" in preview["included_components"]
    repo._engine.dispose()
    source.unlink()
    for suffix in ("-wal", "-shm"):
        Path(str(source) + suffix).unlink(missing_ok=True)
    assert compute_source_tree_hash(fax) == fax_hash
    installation = tmp_path / "independent-installation"
    installation.mkdir()
    monkeypatch.chdir(installation)
    assert not Path("config").exists() and not source.exists()
    # All runtime repositories/caches below are fresh. The working directory
    # contains no Package files or legacy registries from installation A.
    with ColdApiServer(
        database_url=f"sqlite:///{target}", directory=installation
    ) as server:
        before = _dump(target)

        # Rehashing a modified ORIGINAL source cannot replace the independently
        # bound hash retained in the native baseline/source authority.
        def alter_original(rows):
            row = next(r for r in rows if r["revision_id"] == signed["revision_id"])
            summary = decode(row["change_summary_json"])
            summary["forged_original_annotation"] = True
            row["change_summary_json"] = encode(summary).decode()
            resign(row)

        forged = rewrite(raw, "revisions", alter_original)
        status, error = raw_request(archive_root(server) + "/import/preview", forged)
        assert status == 409 and b"source" in error.lower(), error[:1000]
        assert _dump(target) == before
        without_owner = rewrite(
            raw,
            "branches",
            lambda rows: rows.__setitem__(
                slice(None), [r for r in rows if r["branch_id"] != "branch"]
            ),
        )
        assert (
            raw_request(archive_root(server) + "/import/preview", without_owner)[0]
            == 409
        )
        assert _dump(target) == before
        review = upload_preview(server, raw)
        assert _dump(target) == before and review["can_restore"]
        status, receipt = confirm(server, raw, review)
        assert status == 201, receipt
        assert receipt["saved_head_revision_id"] == saved["revision_id"]
    with ColdApiServer(
        database_url=f"sqlite:///{target}", directory=installation
    ) as server:
        assert confirm(server, raw, review) == (201, receipt)
        assert _request("GET", server.base_url + history_url) == history
        restored_view = Tour(server, bid).view()
        assert restored_view["draft_version"] == 0
        # Live review fingerprints include the fresh clean Draft version. The
        # original immutable Saved bytes/fingerprints and sporting view survive.
        assert {
            k: v
            for k, v in restored_view.items()
            if k not in {"draft_version", "tour_fingerprint"}
        } == {
            k: v
            for k, v in view.items()
            if k not in {"draft_version", "tour_fingerprint"}
        }
        detail = _request(
            "GET", server.base_url + history_url + "/" + saved["revision_id"]
        )
        assert detail[0] == 200
        assert detail[1]["payload"] == original_saved_payload
        # Existing supported continuation and manual Save consume the imported
        # aggregate and original owner proofs, including the restored birth.
        tour = Tour(server, bid)
        tour.execute("transition", "after-portable-restore")
        new_saved = tour.save()
        assert new_saved["revision_id"] != saved["revision_id"]
        assert tour.view()["state"]["week"]["calendar"] == clock.to_metadata()
        original = Tour(server, "branch").view()
        assert original["saved_head_revision_id"] == signed["revision_id"]
    with ColdApiServer(
        database_url=f"sqlite:///{target}", directory=installation
    ) as server:
        assert (
            Tour(server, bid).view()["saved_head_revision_id"]
            == new_saved["revision_id"]
        )
        assert confirm(server, raw, review) == (201, receipt)
