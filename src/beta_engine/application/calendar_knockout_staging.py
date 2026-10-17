"""All-or-nothing staging adapter for validated W-aware knockout evidence.

This writes ONLY unpublished calendar ranking source tables, not sporting
results, saved history, Viewer publication or Week/Season transition. Its
caller owns BEGIN IMMEDIATE, independently authenticates the supplied event
evidence fingerprint, and commits/rolls back the entire transaction.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from beta_engine.domain.rankings.calendar_source_history import (
    CalendarRankingResultVersion,
)
from beta_engine.domain.tournaments.calendar_knockout_ranking_evidence import (
    CalendarKnockoutRankingEvidence,
    prepare_calendar_knockout_ranking_versions,
)
from beta_engine.infrastructure.db.staged_calendar_ranking_sources import (
    CalendarRankingStagingConflict,
    StagedCalendarRankingSourceStore,
)


def stage_calendar_knockout_ranking_results(
    session: Session,
    *,
    evidence: CalendarKnockoutRankingEvidence,
    expected_evidence_fingerprint: str,
    expected_saved_head_revision_id: str,
) -> tuple[CalendarRankingResultVersion, ...]:
    """Stage a *whole* validated edition: no partial field or edited retry.

    Signed Saved HEAD and Run clock are validated in the same physical SQLite
    transaction by StagedCalendarRankingSourceStore, BEFORE any row is written.
    An existing edition can only be retried when its *entire* sorted history
    consists of exactly these initial versions; correction histories are not
    silently overwritten or conflated with a new source authority.
    """
    evidence = CalendarKnockoutRankingEvidence.model_validate_json(
        evidence.model_dump_json()
    )
    store = StagedCalendarRankingSourceStore(session)
    calendar = store._scope(
        run_id=evidence.run_id, branch_id=evidence.branch_id,
        expected_saved_head_revision_id=expected_saved_head_revision_id,
        writing=True,
    )
    versions = prepare_calendar_knockout_ranking_versions(
        evidence, run_calendar=calendar,
        expected_evidence_fingerprint=expected_evidence_fingerprint,
    )
    return _install_whole_edition(
        store, evidence.edition_id, versions,
        run_id=evidence.run_id, branch_id=evidence.branch_id,
        expected_saved_head_revision_id=expected_saved_head_revision_id,
    )


def _install_whole_edition(
    store: StagedCalendarRankingSourceStore,
    edition_id: str,
    versions: tuple[CalendarRankingResultVersion, ...],
    *,
    run_id: str,
    branch_id: str,
    expected_saved_head_revision_id: str,
) -> tuple[CalendarRankingResultVersion, ...]:
    """One atomic Edition insert under the caller's already-held SQLite lock.

    Shared by externally authored v1 evidence and richer MatchEngine witness
    evidence. No internal commit. Each version must have the exact Edition and
    the canonical full player population; conflicting/partial rows fail closed.
    """
    if not versions or any(
        (v.run_id, v.branch_id, v.result.edition_id)
        != (run_id, branch_id, edition_id)
        for v in versions
    ):
        raise ValueError("Incomplete or foreign calendar Edition batch")
    existing, _ = store.history(
        run_id=run_id,
        branch_id=branch_id,
        expected_saved_head_revision_id=expected_saved_head_revision_id,
    )
    for_edition = tuple(
        version for version in existing
        if version.result.edition_id == edition_id
    )
    if for_edition:
        if for_edition != versions:
            raise CalendarRankingStagingConflict(
                "Existing calendar Edition source is partial, corrected or different"
            )
        return versions
    for version in versions:
        store.append_result(
            version,
            expected_saved_head_revision_id=expected_saved_head_revision_id,
        )
    installed, _ = store.history(
        run_id=run_id,
        branch_id=branch_id,
        expected_saved_head_revision_id=expected_saved_head_revision_id,
    )
    if tuple(v for v in installed if v.result.edition_id == edition_id) != versions:
        raise ValueError("Whole calendar knockout ranking source batch was not installed")
    return versions
