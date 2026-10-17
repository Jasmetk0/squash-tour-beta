"""Read-only migration bridge from *Saved* canonical FAX tournament evidence.

A validated legacy 61-week tournament authority may be projected into the
new calendar-aware ranking candidate type only when the identical authority
is in the signed immutable Saved Revision AND its live owned row still matches.
Do not reinterpret a legacy RankingWeek into Earth 52-week or W80 time.
This adapter neither writes staged sources nor publishes an Official Ranking.
"""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from beta_engine.application.ranking_tournament_ingestion import (
    prepare_canonical_tournament_ranking_sources,
)
from beta_engine.application.run_calendar_read_authority import (
    resolve_saved_run_calendar,
)
from beta_engine.domain.rankings.calendar_official import (
    CalendarOfficialRankingSnapshot,
    CalendarRankingPlayer,
    CalendarRankingResult,
    CalendarRankingWeek,
)
from beta_engine.domain.rankings.calendar_source_history import (
    CalendarRankingResultVersion,
)
from beta_engine.domain.rankings.official import OfficialRankingPolicy
from beta_engine.infrastructure.db.models import (
    BranchSavedRevisionModel,
    RunBranchModel,
)
from beta_engine.infrastructure.db.owned_tournament_sources import (
    OwnedTournamentRankingSourceStore,
)
from beta_engine.infrastructure.db.saved_revision_rankings import (
    load_saved_ranking_component,
)


def _w(week) -> CalendarRankingWeek:
    return CalendarRankingWeek(
        season_index=week.season_index, week=week.week,
    )


def saved_canonical_tournament_ranking_sources(
    session: Session,
    *,
    run_id: str,
    branch_id: str,
    expected_saved_head_revision_id: str,
    edition_id: str,
) -> tuple[CalendarRankingResultVersion, ...]:
    """Prove a complete canonical tournament in a signed, current Saved HEAD.

    The Run's signed clock, the Saved ranking component's internal hash, and
    the owned SQLite row's identity/hash must ALL agree. Legacy authoritative
    point projection is reused, not guessed. Corrections are not fabricated.
    The bridge returns inspectable initial source versions, not Official facts.
    """
    if not session.in_transaction():
        raise ValueError("Canonical tournament bridge requires a caller read transaction")
    connection = session.connection()
    raw = connection.connection.driver_connection
    if (
        connection.dialect.name != "sqlite"
        or raw is None or not raw.in_transaction
    ):
        raise ValueError("Canonical tournament bridge requires a physical SQLite read transaction")
    if not expected_saved_head_revision_id or not edition_id:
        raise ValueError("Saved HEAD and Edition identities are required")
    branch = session.get(RunBranchModel, branch_id)
    if branch is None or branch.run_id != run_id:
        raise ValueError("Canonical tournament bridge requires a matching Run/Branch")
    if branch.saved_head_revision_id != expected_saved_head_revision_id:
        raise ValueError("Canonical tournament bridge uses a stale Saved HEAD")
    if branch.forked_from_branch_id is not None:
        raise ValueError("Forked tournament ranking source needs a materialized ancestry adapter")

    calendar = resolve_saved_run_calendar(
        session, run_id=run_id, branch_id=branch_id,
    )
    # Legacy TournamentRankingBinding/RankingWeek, including final Closing,
    # only has 61-based FAX timing. Do not infer calendar Week equivalence.
    if (
        calendar.schema_version != "run_calendar.v1"
        or (calendar.weeks_per_year, calendar.season_start_year_week,
            calendar.start_year, calendar.season_count) != (61, 37, 2000, 50)
    ):
        raise ValueError(
            "Saved canonical legacy tournament bridge only supports explicit FAX 61-week clock"
        )

    revision = session.get(BranchSavedRevisionModel, expected_saved_head_revision_id)
    if (
        revision is None
        or revision.run_id != run_id
        or revision.branch_id != branch_id
    ):
        raise ValueError("Canonical tournament bridge Saved origin is unavailable")
    # resolve_saved_run_calendar has already authenticated this exact Saved
    # revision's content hash in the same physical SQLite transaction.
    payload = json.loads(revision.payload_json)
    ranking = load_saved_ranking_component(
        payload, run_id=run_id, branch_id=branch_id,
    )
    if ranking is None:
        raise ValueError("Signed Saved Revision lacks a ranking preparation component")
    stored = tuple(
        source for source in ranking.tournament_sources
        if source.binding.edition_id == edition_id
    )
    if len(stored) != 1:
        raise ValueError("Edition has no unique signed Saved tournament authority")
    source = stored[0]
    if (
        source.schema_version not in {
            "owned_tournament_ranking_source.v3",
            "owned_tournament_ranking_source.v4",
            "owned_tournament_ranking_source.v5",
        }
        or source.binding.closing_only
        or source.canonical_result is None
        or source.canonical_awards is None
    ):
        raise ValueError("Saved tournament is not eligible canonical Official source")
    live = OwnedTournamentRankingSourceStore(session).get(
        run_id=run_id, branch_id=branch_id, edition_id=edition_id,
    )
    if live is None or live.fingerprint != source.fingerprint:
        raise ValueError("Saved tournament authority differs from its live owned row")

    # Reuse the established canonical projection. It checks result/point
    # authority fingerprints, every player's earned points, event/Edition,
    # completion/publication, and individual award provenance.
    legacy = prepare_canonical_tournament_ranking_sources(
        source.binding, source.canonical_result, source.canonical_awards,
    )
    signed_result_versions = {
        (version.result.edition_id, version.result.player_id):
        version
        for version in ranking.sources
        if version.result.edition_id == edition_id
        and version.previous_fingerprint is None
    }
    if signed_result_versions:
        if (
            len(signed_result_versions) != len(legacy)
            or any(
                signed_result_versions.get(
                    (version.result.edition_id, version.result.player_id)
                ) != version
                for version in legacy
            )
        ):
            raise ValueError("Signed ranking result versions contradict canonical awards")
    result = []
    for version in legacy:
        item = version.result
        if item.first_publication_week is None:
            raise ValueError("Closing-only result cannot enter Official ranking candidate")
        result.append(CalendarRankingResultVersion(
            run_id=run_id,
            branch_id=branch_id,
            effective_week=_w(version.effective_week),
            previous_fingerprint=None,
            result=CalendarRankingResult(
                edition_id=item.edition_id,
                player_id=item.player_id,
                source_fingerprint=item.source_fingerprint,
                completed_week=_w(item.completed_week),
                first_publication_week=_w(item.first_publication_week),
                qualification_points=item.qualification_points,
                main_points=item.main_points,
                validity_weeks=item.validity_weeks,
                ranked=item.ranked,
                terminal_status=item.terminal_status,
            ),
        ))
    return tuple(result)


def preview_saved_canonical_tournament_ranking(
    session: Session,
    *,
    run_id: str,
    branch_id: str,
    expected_saved_head_revision_id: str,
    edition_id: str,
    week: CalendarRankingWeek,
    policy: OfficialRankingPolicy,
    players: tuple[CalendarRankingPlayer, ...],
    previous: CalendarOfficialRankingSnapshot | None = None,
):
    """Read-only candidate from signed canonical evidence; no staging writes.

    Like all calendar candidates, sporting publication and Saved correction
    replay require a distinct future Run-local authoritative writer.
    """
    from beta_engine.application.calendar_official_ranking_preview import (
        preview_calendar_official_ranking_from_saved_source_versions,
    )

    versions = saved_canonical_tournament_ranking_sources(
        session,
        run_id=run_id, branch_id=branch_id,
        expected_saved_head_revision_id=expected_saved_head_revision_id,
        edition_id=edition_id,
    )
    return preview_calendar_official_ranking_from_saved_source_versions(
        session,
        run_id=run_id, branch_id=branch_id,
        expected_saved_head_revision_id=expected_saved_head_revision_id,
        week=week, policy=policy, players=players,
        result_versions=versions, previous=previous,
    )
