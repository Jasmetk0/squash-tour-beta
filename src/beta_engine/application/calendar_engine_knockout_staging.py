"""Stage a full knockout whose point sources are witnessed by MatchEngine logs.

This is an unpublished internal bridge. MatchResult and its rally log are
validated as completed engine-shaped records, but the external root receipt
still must be authenticated against Run-owned Saved match authority by the
future sporting writer. No user-facing official ranking promotion occurs.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from beta_engine.application.calendar_knockout_staging import (
    _install_whole_edition,
)
from beta_engine.domain.rankings.calendar_source_history import (
    CalendarRankingResultVersion,
)
from beta_engine.domain.tournaments.calendar_knockout_engine_witness import (
    CalendarEngineKnockoutEvidence,
    prepare_calendar_engine_knockout_versions,
)
from beta_engine.infrastructure.db.staged_calendar_ranking_sources import (
    StagedCalendarRankingSourceStore,
)


def stage_calendar_engine_knockout_results(
    session: Session,
    *,
    evidence: CalendarEngineKnockoutEvidence,
    expected_evidence_fingerprint: str,
    expected_saved_head_revision_id: str,
) -> tuple[CalendarRankingResultVersion, ...]:
    """A complete, atomic initial ranking source batch for one W-aware Edition.

    Requires physical caller-owned SQLite BEGIN IMMEDIATE. The verified Saved
    HEAD/Run clock and anti-publication/fork guards come from the staging store.
    Idempotent retries are exact; no partial/corrected history is overwritten.
    """
    evidence = CalendarEngineKnockoutEvidence.model_validate_json(
        evidence.model_dump_json()
    )
    bracket = evidence.bracket
    store = StagedCalendarRankingSourceStore(session)
    calendar = store._scope(
        run_id=bracket.run_id,
        branch_id=bracket.branch_id,
        expected_saved_head_revision_id=expected_saved_head_revision_id,
        writing=True,
    )
    versions = prepare_calendar_engine_knockout_versions(
        evidence,
        run_calendar=calendar,
        expected_evidence_fingerprint=expected_evidence_fingerprint,
    )
    return _install_whole_edition(
        store, bracket.edition_id, versions,
        run_id=bracket.run_id,
        branch_id=bracket.branch_id,
        expected_saved_head_revision_id=expected_saved_head_revision_id,
    )
