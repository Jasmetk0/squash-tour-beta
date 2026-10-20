"""Replay-owner boundary tests; Signed lineage authorization is mocked here."""

from types import SimpleNamespace

import pytest

from beta_engine.application.calendar_native_historical_replay import (
    authenticated_pre_birth_root,
)
from beta_engine.infrastructure.db.models import RunBranchModel
from tests.domain.test_calendar_native_sporting_checkpoint import prepared

pytestmark = pytest.mark.pr_critical


@pytest.fixture(scope="module")
def native():
    return prepared()[0]


def frame(owner):
    return {
        "content": (
            {
                "calendar_player_sporting_checkpoint": {
                    "state": owner.model_dump(mode="json"),
                    "fingerprint": owner.fingerprint,
                }
            }
            if owner is not None
            else {}
        )
    }


def boundary(native, payload, *, branch_run=None, missing=False, fail=False):
    calls = []
    branch = SimpleNamespace(
        run_id=branch_run or native.run_id,
        branch_id=native.branch_id,
        saved_head_revision_id="actual-head",
    )

    def get(model, key):
        assert model is RunBranchModel and key == native.branch_id
        return None if missing else branch

    session = SimpleNamespace(get=get)

    def authorize(**kwargs):
        assert kwargs == {
            "session": session,
            "branch": branch,
            "payload_revision_ids": frozenset({"actual-head"}),
        }
        calls.append("authenticated Saved HEAD")
        if fail:
            raise ValueError("corrupt Signed lineage")
        return (SimpleNamespace(payload=payload),)

    return (
        SimpleNamespace(_validated_branch_revision_lineage_in_session=authorize),
        session,
        calls,
    )


@pytest.mark.parametrize("saved_native", [False, True])
def test_saved_base_or_native_head_can_own_the_same_frozen_root(native, saved_native):
    repo, session, calls = boundary(
        native, frame(native if saved_native else native.source_checkpoint)
    )
    assert (
        authenticated_pre_birth_root(repo, session, native) == native.source_checkpoint
    )
    assert calls == ["authenticated Saved HEAD"]


@pytest.mark.parametrize("damage", ["missing", "foreign"])
def test_missing_or_foreign_branch_cannot_select_a_root(native, damage):
    repo, session, calls = boundary(
        native,
        frame(native),
        branch_run="foreign" if damage == "foreign" else None,
        missing=damage == "missing",
    )
    with pytest.raises(KeyError):
        authenticated_pre_birth_root(repo, session, native)
    assert calls == []


@pytest.mark.parametrize("missing", [False, True])
def test_absent_or_rehashed_different_signed_root_is_rejected(native, missing):
    owner = (
        None
        if missing
        else native.source_checkpoint.model_copy(
            update={"source_saved_head": "different-root"}
        )
    )
    repo, session, calls = boundary(native, frame(owner))
    with pytest.raises(ValueError, match="actual Signed owner"):
        authenticated_pre_birth_root(repo, session, native)
    assert calls


def test_broken_signed_lineage_is_not_replaced_by_a_self_attested_live_root(native):
    repo, session, _ = boundary(native, frame(native), fail=True)
    with pytest.raises(ValueError, match="corrupt Signed lineage"):
        authenticated_pre_birth_root(repo, session, native)


def test_old_or_unknown_owner_never_silently_enters_this_native_adapter(native):
    with pytest.raises(TypeError):
        authenticated_pre_birth_root(None, None, native.source_checkpoint)
