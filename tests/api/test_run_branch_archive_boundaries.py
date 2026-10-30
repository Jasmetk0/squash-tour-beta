"""Adversarial real SQLite/HTTP boundaries, including actual concurrent writers."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from threading import Event, Lock

import pytest
from sqlalchemy import event

from beta_engine.domain.run_branch_archive import Archive, decode, digest, encode
from beta_engine.domain.run_revisions import saved_revision_content_hash
from beta_engine.infrastructure.db.models import BranchSavedRevisionModel
from tests.api.test_player_generation_calendar_gate import _dump
from tests.api.test_run_branch_archive_api import (
    archive_root,
    confirm,
    export,
    manual_match,
    raw_request,
    upload_preview,
)
from tests.api.test_saved_revision_history_api import ApiServer, _create_run, _request

pytestmark = pytest.mark.pr_critical


def rewrite(raw, part_name, mutate):
    """Attacker recomputes transport digests; original Saved hashes stay separate."""
    envelope = decode(raw)
    part = next(p for p in envelope["parts"] if p["name"] == part_name)
    data = decode(part["data_json"])
    mutate(data)
    serialized = encode(data)
    part.update(
        data_json=serialized.decode(), size=len(serialized), sha256=digest(serialized)
    )
    return encode(envelope)


def resign(row):
    values = {
        k: row[k]
        for k in (
            "revision_id",
            "run_id",
            "branch_id",
            "sequence",
            "parent_revision_id",
            "kind",
            "payload_schema_version",
        )
    }
    row["content_hash"] = saved_revision_content_hash(
        **values,
        payload=decode(row["payload_json"]),
        change_summary=decode(row["change_summary_json"]),
    )


@pytest.fixture(scope="module")
def manual_archive(tmp_path_factory):
    path = tmp_path_factory.mktemp("manual-portable-source") / "source.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        rid, bid, _, _ = manual_match(server)
        raw, _ = export(server, rid, bid)
    server.app.state.runtime.repository._engine.dispose()
    path.unlink()
    return raw


def test_hostile_archives_fail_before_target_writes(tmp_path, manual_archive):
    raw = manual_archive
    variants = [
        raw[:-40],
        encode({**decode(raw), "format": "run_branch_archive.v999"}),
        raw.replace(b'"scope":', b'"unexpected":true,"scope":', 1),
    ]
    variants.append(
        rewrite(
            raw,
            "revisions",
            lambda rows: rows[-1].update(
                payload_json=rows[-1]["payload_json"].replace('"P-A"', '"FORGED"')
            ),
        )
    )
    variants.append(rewrite(raw, "branches", lambda branches: branches.clear()))

    def cycle(rows):
        rows[0]["parent_revision_id"] = rows[-1]["revision_id"]
        resign(rows[0])

    variants.append(rewrite(raw, "revisions", cycle))

    def unknown(rows):
        rows[-1]["payload_schema_version"] = "run_saved_revision_v999"
        resign(rows[-1])

    variants.append(rewrite(raw, "revisions", unknown))

    def orphan(rows):
        extra = dict(rows[0])
        extra["revision_id"] = "unreachable-original"
        resign(extra)
        rows.insert(1, extra)

    variants.append(rewrite(raw, "revisions", orphan))

    def unsupported(rows):
        payload = decode(rows[-1]["payload_json"])
        payload["content"]["unknown_future_authority"] = {"state": {"opaque": True}}
        rows[-1]["payload_json"] = encode(payload).decode()
        resign(rows[-1])

    variants.append(rewrite(raw, "revisions", unsupported))

    def missing_runtime(rows):
        payload = decode(rows[-1]["payload_json"])
        del payload["content"]["initial_world"]
        rows[-1]["payload_json"] = encode(payload).decode()
        resign(rows[-1])

    variants.append(rewrite(raw, "revisions", missing_runtime))
    variants.append(raw + b"garbage")
    target = tmp_path / "hostile-target.db"
    with ApiServer(database_url=f"sqlite:///{target}") as server:
        _create_run(server, display_name="Keep this target Run")
        before = _dump(target)
        for candidate in variants:
            code, body = raw_request(
                archive_root(server) + "/import/preview", candidate
            )
            assert code == 409, body[:1000]
            assert _dump(target) == before


def test_late_receipt_failure_rolls_back_every_row_and_retry_survives_restart(
    tmp_path, manual_archive
):
    target = tmp_path / "late-target.db"
    with ApiServer(database_url=f"sqlite:///{target}") as server:
        other = _create_run(server, display_name="Unrelated must survive")
        review = upload_preview(server, manual_archive)
        before = _dump(target)
        repo = server.app.state.runtime.repository

        def refuse_receipt(conn, cursor, statement, parameters, context, executemany):
            if statement.startswith("INSERT INTO run_branch_archive_receipts"):
                raise ValueError("injected last receipt failure")

        event.listen(repo._engine, "before_cursor_execute", refuse_receipt)
        try:
            code, response = confirm(server, manual_archive, review)
            assert code == 409 and "last receipt failure" in str(response), response
        finally:
            event.remove(repo._engine, "before_cursor_execute", refuse_receipt)
        assert (
            _dump(target) == before
        )  # includes revision rows, allocator, draft and audits
        code, receipt = confirm(server, manual_archive, review)
        assert code == 201, receipt
        assert (
            _request("GET", server.base_url + "/run-containers/" + other[0])[0] == 200
        )
    repo._engine.dispose()
    with ApiServer(database_url=f"sqlite:///{target}") as server:
        assert confirm(server, manual_archive, review) == (201, receipt)
        before = _dump(target)
        # Semantically identical JSON encoded differently is different file bytes.
        assert confirm(server, manual_archive + b"\n", review)[0] == 409
        assert _dump(target) == before


def test_two_http_confirmations_cannot_bypass_identity_conflicts(
    tmp_path, manual_archive
):
    target = tmp_path / "concurrent-target.db"
    with ApiServer(database_url=f"sqlite:///{target}") as server:
        review = upload_preview(server, manual_archive)
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(
                pool.map(
                    lambda cmd: confirm(server, manual_archive, review, command_id=cmd),
                    ["import-A", "import-B"],
                )
            )
        assert sorted(x[0] for x in outcomes) == [201, 409], outcomes
        winner = next(x for x in outcomes if x[0] == 201)
        cmd = winner[1]["command_id"]
        with ThreadPoolExecutor(max_workers=2) as pool:
            retries = list(
                pool.map(
                    lambda _: confirm(server, manual_archive, review, command_id=cmd),
                    range(2),
                )
            )
        assert retries == [winner, winner]
        with server.app.state.runtime.repository._session_factory() as session:
            assert session.query(BranchSavedRevisionModel).count() == len(
                Archive(manual_archive).revisions
            )


def test_name_collision_and_identity_occupied_after_preview_invalidate_confirmation(
    tmp_path, manual_archive
):
    archive = Archive(manual_archive)
    target = tmp_path / "name-target.db"
    with ApiServer(database_url=f"sqlite:///{target}") as server:
        original_review = upload_preview(server, manual_archive)
        _create_run(server, display_name=archive.run.display_name)
        before = _dump(target)
        code, response = confirm(server, manual_archive, original_review)
        assert code == 409 and response["detail"]["code"] == "stale_import_preview", (
            response
        )
        review = upload_preview(server, manual_archive)
        assert not review["can_restore"]
        assert any(c["code"] == "run_name_exists" for c in review["conflicts"])
        assert confirm(server, manual_archive, review)[0] == 409
        assert _dump(target) == before


def test_export_reads_one_snapshot_while_real_save_commits_and_old_preview_stays_bound(
    tmp_path,
):
    source = tmp_path / "concurrent-source.db"
    with ApiServer(database_url=f"sqlite:///{source}") as server:
        rid, bid, initial = _create_run(server, display_name="Snapshot race")
        code, other = _request(
            "POST",
            server.base_url + f"/run-containers/{rid}/branches",
            {"source_branch_id": bid, "source_saved_revision_id": initial},
        )
        assert code == 201, other
        selection = {"run_id": rid, "branch_id": bid}
        code, preview = _request(
            "POST", archive_root(server) + "/export/preview", selection
        )
        assert code == 200, preview
        command = {
            **selection,
            "expected_head_revision_id": initial,
            "expected_archive_digest": preview["archive_digest"],
        }
        entered, release, guard = Event(), Event(), Lock()
        intercepted = False

        def pause_after_snapshot(
            conn, cursor, statement, parameters, context, executemany
        ):
            nonlocal intercepted
            if (
                statement.startswith("SELECT")
                and "FROM branch_saved_revisions" in statement
            ):
                with guard:
                    if intercepted:
                        return
                    intercepted = True
                entered.set()
                assert release.wait(30), (
                    "Save did not finish while export held its read snapshot"
                )

        repo = server.app.state.runtime.repository
        event.listen(repo._engine, "before_cursor_execute", pause_after_snapshot)
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                download = pool.submit(
                    raw_request,
                    archive_root(server) + "/export",
                    json.dumps(command).encode(),
                )
                assert entered.wait(30)
                # A separate real HTTP writer stages and Saves after the export
                # already read Run/Branch metadata, while that snapshot remains.
                draft_url = (
                    server.base_url
                    + f"/run-containers/{rid}/branches/{bid}/working-draft"
                )
                code, draft = _request(
                    "PUT",
                    draft_url + "/viewer-branch",
                    {
                        "viewer_branch_id": other["branch_id"],
                        "expected_draft_version": 0,
                    },
                )
                assert code == 200, draft
                code, saved = _request(
                    "POST",
                    draft_url + "/save",
                    {"expected_draft_version": draft["draft_version"]},
                )
                assert code == 201, saved
                release.set()
                status, raw = download.result(timeout=60)
                assert status == 200, raw[:1000]
        finally:
            release.set()
            event.remove(repo._engine, "before_cursor_execute", pause_after_snapshot)
        snapshot = Archive(raw)
        assert snapshot.raw_digest == preview["archive_digest"]
        assert snapshot.envelope.selected_head_revision_id == initial
        assert snapshot.run.viewer_branch_id == bid
        assert len(snapshot.revisions) == 1
        status, body = raw_request(
            archive_root(server) + "/export", json.dumps(command).encode()
        )
        assert (
            status == 409
            and json.loads(body)["detail"]["code"] == "stale_export_preview"
        )
        # Dirty unexported foreign Branch does not block selected scope.
        other_draft = (
            server.base_url
            + f"/run-containers/{rid}/branches/{other['branch_id']}/working-draft"
        )
        assert (
            _request(
                "PUT",
                other_draft + "/viewer-branch",
                {"viewer_branch_id": other["branch_id"], "expected_draft_version": 0},
            )[0]
            == 200
        )
        # It IS now the saved Viewer dependency, so its dirty current state blocks.
        assert (
            _request("POST", archive_root(server) + "/export/preview", selection)[0]
            == 409
        )


def test_unsaved_selected_authoring_blocks_but_dirty_omitted_branch_does_not(tmp_path):
    source = tmp_path / "unsaved-scope.db"
    with ApiServer(database_url=f"sqlite:///{source}") as server:
        rid, bid, head = _create_run(server, display_name="Draft scope")
        code, foreign = _request(
            "POST",
            server.base_url + f"/run-containers/{rid}/branches",
            {"source_branch_id": bid, "source_saved_revision_id": head},
        )
        assert code == 201, foreign
        foreign_draft = (
            server.base_url
            + f"/run-containers/{rid}/branches/{foreign['branch_id']}/working-draft"
        )
        code, dirty = _request(
            "PUT",
            foreign_draft + "/viewer-branch",
            {"viewer_branch_id": foreign["branch_id"], "expected_draft_version": 0},
        )
        assert code == 200 and dirty["status"] == "dirty", dirty
        raw, preview = export(server, rid, bid)
        assert preview["omitted_branch_ids"] == [foreign["branch_id"]]
        assert len(Archive(raw).branches) == 1
        root = (
            server.base_url
            + f"/admin/runs/{rid}/branches/{bid}/authoritative-simulation/standalone-match"
        )
        from tests.application.test_standalone_match_acceptance import _player

        assert (
            _request(
                "POST",
                root + "/players",
                {"player": _player("P-A", "A", technique=80).model_dump(mode="json")},
            )[0]
            == 200
        )
        before = _dump(source)
        code, blocked = _request(
            "POST",
            archive_root(server) + "/export/preview",
            {"run_id": rid, "branch_id": bid},
        )
        assert code == 409 and blocked["detail"]["code"] == "unsaved_changes", blocked
        assert _dump(source) == before


@pytest.mark.parametrize("attack", ["foreign_head", "bad_hash", "cycle"])
def test_corrupt_actual_source_lineage_cannot_be_exported(tmp_path, attack):
    source = tmp_path / f"source-{attack}.db"
    with ApiServer(database_url=f"sqlite:///{source}") as server:
        rid, bid, head = _create_run(server, display_name="Actual source integrity")
        _, _, foreign_head = _create_run(server, display_name="Foreign source Run")
        repo = server.app.state.runtime.repository
        from beta_engine.infrastructure.db.models import RunBranchModel

        with repo._session_factory.begin() as session:
            row = session.get(BranchSavedRevisionModel, head)
            if attack == "foreign_head":
                session.get(RunBranchModel, bid).saved_head_revision_id = foreign_head
            elif attack == "bad_hash":
                row.content_hash = "0" * 64
            else:
                row.parent_revision_id = head
                values = {
                    name: getattr(row, name)
                    for name in (
                        "revision_id",
                        "run_id",
                        "branch_id",
                        "sequence",
                        "parent_revision_id",
                        "kind",
                        "payload_schema_version",
                    )
                }
                row.content_hash = saved_revision_content_hash(
                    **values,
                    payload=decode(row.payload_json),
                    change_summary=decode(row.change_summary_json),
                )
        before = _dump(source)
        code, _ = _request(
            "POST",
            archive_root(server) + "/export/preview",
            {"run_id": rid, "branch_id": bid},
        )
        assert code == 409
        assert _dump(source) == before


def test_actual_viewer_selection_saved_by_third_branch_is_a_required_dependency(
    tmp_path,
):
    source, target = tmp_path / "viewer-source.db", tmp_path / "viewer-target.db"
    with ApiServer(database_url=f"sqlite:///{source}") as server:
        rid, selected, head = _create_run(
            server, display_name="Third Branch Viewer witness"
        )
        ids = []
        for _ in range(2):
            code, created = _request(
                "POST",
                server.base_url + f"/run-containers/{rid}/branches",
                {"source_branch_id": selected, "source_saved_revision_id": head},
            )
            assert code == 201, created
            ids.append(created["branch_id"])
        viewer, editor = ids
        draft = (
            server.base_url + f"/run-containers/{rid}/branches/{editor}/working-draft"
        )
        code, staged = _request(
            "PUT",
            draft + "/viewer-branch",
            {"viewer_branch_id": viewer, "expected_draft_version": 0},
        )
        assert code == 200, staged
        code, saved = _request(
            "POST", draft + "/save", {"expected_draft_version": staged["draft_version"]}
        )
        assert code == 201, saved
        raw, preview = export(server, rid, selected)
        assert (
            preview["run_activation_revision_id"]
            == saved["saved_revision"]["revision_id"]
        )
        assert len(preview["branches"]) == 3
        assert preview["selected_head_revision_id"] == head
    server.app.state.runtime.repository._engine.dispose()
    source.unlink()
    with ApiServer(database_url=f"sqlite:///{target}") as server:
        review = upload_preview(server, raw)
        code, receipt = confirm(server, raw, review)
        assert code == 201, receipt
        context = _request(
            "GET", server.base_url + f"/viewer/runs/{rid}/official-context"
        )
        assert context[0] == 200 and context[1]["official_branch_id"] == viewer, context
        assert context[1]["saved_head_revision_id"] == head


def test_unresolved_package_reference_survives_without_claiming_sporting_readiness(
    tmp_path,
):
    from beta_engine.domain.run_packages import PackageType, SourceReference
    from tests.application.test_run_package_snapshot import doc, entity

    source, target = tmp_path / "unresolved-A.db", tmp_path / "unresolved-B.db"
    with ApiServer(database_url=f"sqlite:///{source}") as server:
        rid, bid, head = _create_run(
            server, display_name="Incomplete independent Package"
        )
        reference = SourceReference(
            source_package_id="missing-categories",
            source_entity_id="category",
            expected_entity_kind="category",
        )
        document = doc(
            PackageType.SERIES,
            "portable-series",
            entities=(
                entity(
                    "series",
                    {"name": "Unresolved Series"},
                    "series",
                    "series",
                    (reference,),
                ),
            ),
        ).model_dump(mode="json")
        root = server.base_url + f"/admin/runs/{rid}/branches/{bid}/packages"
        code, reviewed = _request("POST", root + "/preview", {"document": document})
        assert code == 200 and reviewed["unresolved"], reviewed
        code, applied = _request(
            "POST",
            root + "/confirm",
            {
                "document": document,
                "command_id": "apply-incomplete",
                "expected_head_revision_id": head,
                "expected_draft_version": 0,
                "expected_state_fingerprint": None,
                "expected_preview_fingerprint": reviewed["preview_fingerprint"],
            },
        )
        assert code == 200, applied
        code, saved = _request(
            "POST",
            server.base_url
            + f"/run-containers/{rid}/branches/{bid}/working-draft/save",
            {"expected_draft_version": applied["draft_version"]},
        )
        assert code == 201, saved
        raw, _ = export(server, rid, bid)
    server.app.state.runtime.repository._engine.dispose()
    source.unlink()
    with ApiServer(database_url=f"sqlite:///{target}") as server:
        review = upload_preview(server, raw)
        assert (
            review["can_restore"] and not review["capabilities"]["automatic_simulation"]
        )
        code, receipt = confirm(server, raw, review)
        assert code == 201, receipt
        root = server.base_url + f"/admin/runs/{rid}/branches/{bid}/packages"
        code, restored = _request("GET", root)
        assert code == 200, restored
        assert restored["state"] == applied["state"]
        assert (
            restored["state"]["entities"][0]["references"][0]["source_package_id"]
            == "missing-categories"
        )


def test_forged_review_cannot_skip_complete_validation_before_target_writes(
    tmp_path, manual_archive
):
    from beta_engine.application.run_branch_archive_service import reviewed_import

    def remove_world(rows):
        payload = decode(rows[-1]["payload_json"])
        payload["content"].pop("initial_world")
        rows[-1]["payload_json"] = encode(payload).decode()
        resign(rows[-1])

    invalid = rewrite(manual_archive, "revisions", remove_world)
    target = tmp_path / "self-declared-review.db"
    with ApiServer(database_url=f"sqlite:///{target}") as server:
        repo = server.app.state.runtime.repository
        # Fingerprints are public integrity/staleness bindings, not signatures.
        # Deliberately compute one without invoking the real import preview.
        with repo._session_factory() as session:
            forged_review = reviewed_import(session, Archive(invalid))
        writes = []

        def observe_writes(conn, cursor, statement, parameters, context, executemany):
            if statement.startswith(("INSERT", "UPDATE", "DELETE")):
                writes.append(statement)

        before = _dump(target)
        event.listen(repo._engine, "before_cursor_execute", observe_writes)
        try:
            code, body = confirm(server, invalid, forged_review)
            assert (
                code == 409 and body["detail"]["code"] == "missing_runtime_dependency"
            ), body
        finally:
            event.remove(repo._engine, "before_cursor_execute", observe_writes)
        assert writes == []
        assert _dump(target) == before


def test_archive_sqlite_integer_overflow_is_a_concrete_prewrite_rejection(
    tmp_path, manual_archive
):
    invalid = rewrite(
        manual_archive,
        "branches",
        lambda branches: branches[0].update(branch_seed=2**100),
    )
    target = tmp_path / "unrepresentable-number.db"
    with ApiServer(database_url=f"sqlite:///{target}") as server:
        before = _dump(target)
        code, body = raw_request(archive_root(server) + "/import/preview", invalid)
        assert code == 409, body[:1000]
        assert _dump(target) == before
