"""Atomic installer for a previously verified empty-week transition audit.

This is called only *inside* the transaction that has already materialized the
target-owned ranking, player lifecycle, sporting/health, and saved Run package.
Every inserted receipt/event is checked by recapturing full authoritative
ranking history before the target Saved Revision is committed.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from beta_engine.domain.rankings.revision_state import (
    RankingRevisionState,
    ranking_revision_states_equivalent,
)
from beta_engine.infrastructure.db.models import (
    AuthoritativeWeekTransitionReceiptModel,
    AuthoritativeWorldEventModel,
)
from beta_engine.infrastructure.db.ranking_revision_state import (
    capture_ranking_revision_state,
)


def install_remapped_week_transition_audit(
    session: Session,
    *,
    state: RankingRevisionState,
    run_id: str,
    branch_id: str,
    allow_verified_season_boundary: bool = False,
) -> RankingRevisionState:
    """Install a complete, validated, target-Branch audit without partial success."""
    if (
        not session.in_transaction()
        or (state.run_id, state.branch_id) != (run_id, branch_id)
        or state.authoritative_transition_state is None
    ):
        raise ValueError("Post-transition fork audit requires the target transaction")
    transition = state.authoritative_transition_state
    week_events = tuple(
        row for row in transition["events"]
        if row.get("event_kind") == "week_transition_completed"
    )
    season_events = tuple(
        row for row in transition["events"]
        if row.get("event_kind") == "season_transition_completed"
    )
    if (
        not transition["receipts"]
        or len(transition["receipts"]) != len(week_events)
        or len(transition["events"]) != len(week_events) + len(season_events)
        or (
            season_events
            and (
                not allow_verified_season_boundary
                or len(season_events) != 1
                or len(state.season_closing_rankings) != 1
                or season_events[0]["week_ordinal"]
                != state.season_closing_rankings[0].completed_week.ordinal + 1
            )
        )
        or (not season_events and allow_verified_season_boundary)
    ):
        raise ValueError("Post-transition fork requires paired verified Week/Season events")
    for row in transition["receipts"]:
        if session.get(
            AuthoritativeWeekTransitionReceiptModel,
            (run_id, branch_id, row["command_id"]),
        ) is not None:
            raise ValueError("Fork target already contains a transition receipt")
    for row in transition["events"]:
        if session.get(
            AuthoritativeWorldEventModel,
            (run_id, branch_id, row["command_id"]),
        ) is not None:
            raise ValueError("Fork target already contains a World Event")

    # Ranking/player histories were installed earlier in the same transaction.
    # Even successful insertion is rolled back when the captured full state is
    # not equivalent to the proposed frozen target evidence.
    for row in transition["receipts"]:
        session.add(AuthoritativeWeekTransitionReceiptModel(**row))
    for row in transition["events"]:
        session.add(AuthoritativeWorldEventModel(**row))
    session.flush()
    installed = capture_ranking_revision_state(
        session, run_id=run_id, branch_id=branch_id
    )
    if not ranking_revision_states_equivalent(installed, state):
        raise ValueError(
            "Installed fork transition audit differs from frozen target ranking"
        )
    return installed
