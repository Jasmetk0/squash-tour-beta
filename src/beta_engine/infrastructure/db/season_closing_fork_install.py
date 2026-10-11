"""Install verified post-season Closing Ranking archives into target-owned SQLite.

This is a lower-level part of the eventual Saved Revision fork transaction, not
authorization to fork Season Transition World Events or bypass the existing
fork guard. Its caller must supply immutable Saved Revision ranking states
after remapping target-owned history, within the outer branch transaction.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from beta_engine.infrastructure.db.ranking_fork_remap import (
    _remap_season_closing_archives,
)
from beta_engine.infrastructure.db.season_closing_rankings import (
    SeasonClosingRankingStore,
)


def install_verified_fork_season_closings(
    session: Session,
    *,
    source_state,
    target_state,
    proposed_archives: tuple,
    run_id: str,
    source_branch_id: str,
    target_branch_id: str,
) -> tuple:
    """Append entire proven archive history or roll back the nested savepoint."""
    if (
        not session.in_transaction()
        or (source_state.run_id, source_state.branch_id)
        != (run_id, source_branch_id)
        or (target_state.run_id, target_state.branch_id)
        != (run_id, target_branch_id)
        or source_branch_id == target_branch_id
        or not source_state.season_closing_rankings
        or target_state.season_closing_rankings
    ):
        raise ValueError("Season Closing fork requires distinct proven source/target state")
    connection = session.connection()
    driver = connection.connection.driver_connection
    if (
        connection.dialect.name != "sqlite"
        or driver is None
        or not driver.in_transaction
    ):
        raise ValueError("Season Closing fork installation requires physical SQLite transaction")

    # Do not trust a caller-supplied archive, or merely its checksum.
    # Regenerate all boundaries from the original and target-owned frozen
    # ranking histories, including corrected results and zero-version history.
    expected = _remap_season_closing_archives(
        source_state,
        target_entries=target_state.entries,
        target_sources=target_state.sources,
        target_zero_sources=target_state.zero_sources,
        target_branch_id=target_branch_id,
    )
    if expected != tuple(proposed_archives):
        raise ValueError("Season Closing fork archive differs from verified ranking replay")

    store = SeasonClosingRankingStore(session)
    with session.begin_nested():
        for archive in expected:
            store.install_restored(archive)
        if store.history(run_id=run_id, branch_id=target_branch_id) != expected:
            raise ValueError("Season Closing fork installed archive lineage differs")
    return expected
