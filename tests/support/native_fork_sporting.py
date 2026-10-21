"""Actual pending-fork match/draft checks shared by pre/post-birth HTTP fixtures."""

import json
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest
from sqlalchemy import event, select

from beta_engine.application.calendar_continuation_service import (
    CalendarContinuationCommand,
)
from beta_engine.application.native_fork_sporting_service import (
    NativeForkSportingService,
)
from beta_engine.domain.native_fork_sporting import (
    NativeForkSportingCheckpoint,
    play_native_fork_match,
)
from beta_engine.domain.run_revisions import canonical_json
from beta_engine.infrastructure.db.models import (
    BranchSavedRevisionModel,
    BranchWorkingDraftModel,
)
from tests.api.test_player_generation_calendar_gate import _dump


def exercise_native_fork_sporting(repo, path, *, branch_id, player_pair=None):
    service = NativeForkSportingService(repo)
    view = service.inspect(run_id="run", branch_id=branch_id)
    initial = view["checkpoint"]
    if player_pair is None:
        player_pair = tuple(p.player_id for p in initial.players[:2])
    original_history = repo.get_branch_saved_revision_history(
        run_id="run", branch_id="branch"
    )
    with repo._session_factory() as session:
        draft_id = session.scalar(
            select(BranchWorkingDraftModel.draft_id).where(
                BranchWorkingDraftModel.branch_id == branch_id
            )
        )
    draft_prefix = f"INSERT INTO \"branch_working_drafts\" VALUES('{draft_id}',"

    def other_rows():
        return tuple(line for line in _dump(path) if not line.startswith(draft_prefix))

    original_rows = other_rows()

    def command(checkpoint, n):
        return CalendarContinuationCommand(
            command_id=f"fork-match-{n}",
            match_id=f"fork-match-{n}",
            expected_saved_head=checkpoint.root_saved_revision_id,
            expected_checkpoint_fingerprint=checkpoint.fingerprint,
            player_a_id=player_pair[0],
            player_b_id=player_pair[1],
            seed=121 + n,
            operator_label="Admin",
            audit_reason="Actual independent native fork draft test",
        )

    first = command(initial, 1)
    request = {
        "run_id": "run",
        "branch_id": branch_id,
        "command": first,
        "expected_draft_version": view["draft_version"],
    }
    before = _dump(path)
    preview = service.preview(**request)
    assert _dump(path) == before
    confirmed = request | {
        "expected_preview_fingerprint": preview["preview_fingerprint"],
        "explicit_confirmation": True,
    }
    for change in (
        {"explicit_confirmation": False},
        {"expected_preview_fingerprint": "0" * 64},
        {"expected_draft_version": view["draft_version"] + 1},
    ):
        with pytest.raises(ValueError):
            service.execute(**(confirmed | change))
        assert _dump(path) == before

    def fail_update(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith("UPDATE branch_working_drafts"):
            raise RuntimeError("injected fork draft write failure")

    event.listen(repo._engine, "before_cursor_execute", fail_update)
    try:
        with pytest.raises(RuntimeError, match="draft write failure"):
            service.execute(**confirmed)
    finally:
        event.remove(repo._engine, "before_cursor_execute", fail_update)
    assert _dump(path) == before
    with ThreadPoolExecutor(max_workers=2) as pool:
        receipts = list(pool.map(lambda _: service.execute(**confirmed), range(2)))
    assert receipts[0] == receipts[1] and receipts[0]["saved"] is False
    after_one = service.inspect(run_id="run", branch_id=branch_id)
    assert after_one["checkpoint"] == preview["checkpoint"]
    assert after_one["draft_version"] == view["draft_version"] + 1
    assert not after_one["saved"]
    assert other_rows() == original_rows
    assert (
        repo.get_branch_saved_revision_history(run_id="run", branch_id="branch")
        == original_history
    )
    assert (
        repo.get_run_branch(branch_id=branch_id).saved_head_revision_id
        == initial.root_saved_revision_id
    )
    assert (
        repo.get_branch_revision_state(branch_id=branch_id).working_draft.status
        == "dirty"
    )

    second = command(after_one["checkpoint"], 2)
    request_two = request | {
        "command": second,
        "expected_draft_version": after_one["draft_version"],
    }
    reviewed_two = service.preview(**request_two)
    receipt_two = service.execute(
        **request_two,
        expected_preview_fingerprint=reviewed_two["preview_fingerprint"],
        explicit_confirmation=True,
    )
    assert (
        receipt_two["checkpoint_fingerprint"] == reviewed_two["checkpoint"].fingerprint
    )
    # The first receipt remains exact even after a later command was applied.
    before = _dump(path)
    assert service.execute(**confirmed) == receipts[0]
    for change in (
        {"command": first.model_copy(update={"seed": 77})},
        {"expected_preview_fingerprint": "0" * 64},
    ):
        with pytest.raises(ValueError, match="retry conflicts"):
            service.execute(**(confirmed | change))
    assert _dump(path) == before
    assert other_rows() == original_rows

    # A self-consistent checkpoint generated with false biography inputs has
    # valid MatchEngine logs and hashes. Real-source replay must still reject it.
    with repo._session_factory() as session:
        _state, cp, world, prospects = service._context(
            session, run_id="run", branch_id=branch_id
        )
    false_world = SimpleNamespace(
        run_id=world.run_id,
        branch_id=world.branch_id,
        fingerprint=world.fingerprint,
        players=tuple(
            p.model_copy(update={"name": "Forged biography"}) for p in world.players
        ),
    )
    fake = NativeForkSportingCheckpoint(
        root_saved_revision_id=cp.root_saved_revision_id, baseline=cp.baseline
    )
    for n, step in enumerate(cp.steps, start=1):
        fake = play_native_fork_match(
            fake,
            command(fake, n),
            draft_version=step.draft_version_before,
            world=false_world,
            prospects=prospects,
        )
    assert fake.fingerprint != cp.fingerprint
    with repo._session_factory.begin() as session:
        row = session.get(BranchWorkingDraftModel, draft_id)
        actual_bytes = row.changes_json
        component = json.loads(actual_bytes)[0]
        component["state"], component["fingerprint"] = (
            fake.model_dump(mode="json"),
            fake.fingerprint,
        )
        row.changes_json = canonical_json([component])
    try:
        with pytest.raises(ValueError, match="actual MatchEngine replay"):
            service.inspect(run_id="run", branch_id=branch_id)
    finally:
        with repo._session_factory.begin() as session:
            session.get(BranchWorkingDraftModel, draft_id).changes_json = actual_bytes
    assert service.inspect(run_id="run", branch_id=branch_id)["checkpoint"] == cp

    # A changed immutable original source is rejected after a successful warm
    # draft inspection, without resetting or overwriting the draft.
    source_id = cp.baseline.source_binding.source.revision_id
    with repo._session_factory.begin() as session:
        row = session.get(BranchSavedRevisionModel, source_id)
        source_bytes = row.payload_json
        raw = json.loads(source_bytes)
        raw["run"]["display_name"] = "changed original source"
        row.payload_json = canonical_json(raw)
    try:
        corrupted = _dump(path)
        with pytest.raises(ValueError, match="integrity"):
            service.inspect(run_id="run", branch_id=branch_id)
        assert _dump(path) == corrupted
    finally:
        with repo._session_factory.begin() as session:
            session.get(BranchSavedRevisionModel, source_id).payload_json = source_bytes
    assert _dump(path) == before
    assert other_rows() == original_rows
    return {
        "checkpoint": cp,
        "first_request": confirmed,
        "first_receipt": receipts[0],
        "draft_version": receipt_two["draft_version"],
        "other_rows": original_rows,
        "draft_prefix": draft_prefix,
    }
