"""Authenticate pre-birth match ownership without today's medical readiness."""

from beta_engine.infrastructure.db.calendar_standalone_match_state import (
    decode_prevalidated_calendar_sources,
)
from beta_engine.infrastructure.db.models import RunBranchModel


def authenticated_pre_birth_root(repository, session, state):
    if state.schema_version not in {"calendar_sporting_checkpoint.v11", "calendar_sporting_checkpoint.v12"}:
        raise TypeError("Historical native replay requires a supported v11 owner")
    branch = session.get(RunBranchModel, state.branch_id)
    if branch is None or branch.run_id != state.run_id:
        raise KeyError("Historical replay Run/Branch not found")
    # Readonly Saved authority: do not call the command context, require a clean
    # draft, or consume current live Health/lifecycle/source-generation readiness.
    revision = repository._validated_branch_revision_lineage_in_session(
        session=session,
        branch=branch,
        payload_revision_ids=frozenset({branch.saved_head_revision_id}),
    )[0]
    _, signed, _ = decode_prevalidated_calendar_sources(
        revision.payload, run_id=state.run_id, branch_id=state.branch_id
    )
    root = (
        signed.source_checkpoint
        if signed is not None and signed.schema_version in {"calendar_sporting_checkpoint.v11", "calendar_sporting_checkpoint.v12"}
        else signed
    )
    if root is None or root != state.source_checkpoint:
        raise ValueError(
            "Historical pre-birth root differs from its actual Signed owner"
        )
    return root
