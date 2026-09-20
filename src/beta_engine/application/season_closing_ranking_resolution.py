"""Canonical resolution/staging of Season Closing Ranking, including final Run."""

from sqlalchemy.orm import Session

from beta_engine.application.ranking_tournament_ingestion import (
    prepare_canonical_tournament_ranking_sources,
    prepare_final_season_closing_ranking_results,
    prepare_tournament_ranking_sources,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.rankings.season_closing import (
    SeasonClosingRankingSnapshot,
    calculate_season_closing_ranking,
)
from beta_engine.infrastructure.db.models import (
    AuthoritativeWorldStateModel,
    PublishedOfficialRankingModel,
)
from beta_engine.infrastructure.db.official_rankings import OfficialRankingCandidateStore
from beta_engine.infrastructure.db.owned_tournament_sources import (
    OwnedTournamentRankingSourceStore,
)
from beta_engine.infrastructure.db.player_lifecycle_state import (
    get_lifecycle,
    project_lifecycle_tour_entries_through_week,
)
from beta_engine.infrastructure.db.ranking_result_history import OfficialRankingResultStore
from beta_engine.infrastructure.db.ranking_zero_history import OfficialRankingZeroStore
from beta_engine.infrastructure.db.season_closing_rankings import SeasonClosingRankingStore


def _season_boundary_target(completed_week: RankingWeek) -> RankingWeek | None:
    if completed_week.week != 61:
        raise ValueError("Season Closing Ranking resolution requires completed Week 61")
    if completed_week.season_index == 49:
        return None
    return RankingWeek(season_index=completed_week.season_index + 1, week=1)


def _owned_week61_results(
    session: Session,
    *,
    run_id: str,
    branch_id: str,
    completed_week: RankingWeek,
):
    target_week = _season_boundary_target(completed_week)
    final_season = target_week is None
    results = {}
    for source in OwnedTournamentRankingSourceStore(session).history(
        run_id=run_id,
        branch_id=branch_id,
    ):
        if source is None:
            raise ValueError("Owned tournament source history is incomplete")
        binding = source.binding
        if binding.completed_week != completed_week:
            continue

        if final_season:
            if (
                source.schema_version != "owned_tournament_ranking_source.v6"
                or not binding.closing_only
                or binding.closing_eligibility_ordinal
                != completed_week.ordinal + 1
                or source.canonical_result is None
                or source.canonical_awards is None
            ):
                raise ValueError(
                    "Final Week 61 tournament source is not canonical Closing-only evidence"
                )
            projected = prepare_final_season_closing_ranking_results(
                binding,
                source.canonical_result,
                source.canonical_awards,
            )
        else:
            if (
                binding.closing_only
                or binding.first_publication_week != target_week
                or source.schema_version == "owned_tournament_ranking_source.v6"
            ):
                raise ValueError(
                    "Week 61 tournament source has a non-canonical publication boundary"
                )
            if source.schema_version in {
                "owned_tournament_ranking_source.v3",
                "owned_tournament_ranking_source.v4",
                "owned_tournament_ranking_source.v5",
            }:
                if source.canonical_result is None or source.canonical_awards is None:
                    raise ValueError(
                        "Canonical Week 61 tournament source is incomplete"
                    )
                versions = prepare_canonical_tournament_ranking_sources(
                    binding,
                    source.canonical_result,
                    source.canonical_awards,
                )
            else:
                if source.result is None or source.awards is None:
                    raise ValueError(
                        "Historical Week 61 tournament source is incomplete"
                    )
                versions = prepare_tournament_ranking_sources(
                    binding,
                    source.result,
                    source.awards,
                )
            if any(version.effective_week != target_week for version in versions):
                raise ValueError(
                    "Week 61 tournament ranking source resolved outside the season boundary"
                )
            projected = tuple(version.result for version in versions)

        for result in projected:
            key = (result.edition_id, result.player_id)
            current = results.get(key)
            if current is not None and current != result:
                raise ValueError("Conflicting Week 61 tournament ranking source")
            results[key] = result
    return results


def resolve_canonical_season_closing_ranking(
    session: Session,
    *,
    run_id: str,
    branch_id: str,
    completed_week: RankingWeek,
) -> SeasonClosingRankingSnapshot:
    """Resolve a Closing Ranking only from persisted canonical Run/Branch state."""

    target_week = _season_boundary_target(completed_week)
    history = OfficialRankingCandidateStore(session).history(
        run_id=run_id,
        branch_id=branch_id,
    )
    if not history or history[-1].week != completed_week:
        raise ValueError(
            "Season Closing Ranking requires the current Official Ranking Week 61 head"
        )
    predecessor = history[-1]

    publication = session.get(
        PublishedOfficialRankingModel,
        (run_id, branch_id, completed_week.ordinal),
    )
    world = session.get(AuthoritativeWorldStateModel, (run_id, branch_id))
    if (
        publication is None
        or publication.snapshot_fingerprint != predecessor.fingerprint
        or publication.payload_json != predecessor.model_dump_json()
        or world is None
        or world.current_ordinal != completed_week.ordinal
        or world.ranking_fingerprint != predecessor.fingerprint
    ):
        raise ValueError(
            "Season Closing Ranking requires the published authoritative Week 61 head"
        )

    lifecycle = get_lifecycle(
        session,
        run_id=run_id,
        branch_id=branch_id,
        week=completed_week,
    )
    if lifecycle is None:
        raise ValueError("Season Closing Ranking requires Week 61 player lifecycle state")
    effective_lifecycle = project_lifecycle_tour_entries_through_week(
        session,
        lifecycle,
        through_week=completed_week,
    )
    players = effective_lifecycle.ranking_roster()

    # Frozen Week-61 tournament sources have not passed through ordinary Week
    # Transition ingestion, so materialize them directly in-memory. Persisted result
    # history then overlays earlier results/corrections that are effective at the
    # same boundary.
    resolved = _owned_week61_results(
        session,
        run_id=run_id,
        branch_id=branch_id,
        completed_week=completed_week,
    )
    history_week = target_week or completed_week
    for result in OfficialRankingResultStore(session).resolve(
        run_id=run_id,
        branch_id=branch_id,
        week=history_week,
    ):
        if target_week is None and result.completed_week == completed_week:
            raise ValueError(
                "Final Week 61 tournament result cannot exist in Official ranking history"
            )
        key = (result.edition_id, result.player_id)
        owned_result = resolved.get(key)
        if target_week is not None and result.completed_week == completed_week:
            if owned_result is None:
                raise ValueError(
                    "Week 61 ranking result has no matching owned tournament source"
                )
            if owned_result != result:
                raise ValueError(
                    "Persisted Week 61 ranking result conflicts with owned tournament source"
                )
        elif owned_result is not None:
            raise ValueError(
                "Persisted ranking history conflicts with Closing-only tournament source"
            )
        resolved[key] = result

    zeros = OfficialRankingZeroStore(session).resolve(
        run_id=run_id,
        branch_id=branch_id,
        week=history_week,
    )
    return calculate_season_closing_ranking(
        run_id=run_id,
        branch_id=branch_id,
        completed_week=completed_week,
        policy=predecessor.policy,
        players=players,
        results=tuple(resolved[key] for key in sorted(resolved)),
        predecessor=predecessor,
        disciplinary_zeros=zeros,
    )


def stage_canonical_season_closing_ranking(
    session: Session,
    *,
    run_id: str,
    branch_id: str,
    completed_week: RankingWeek,
) -> SeasonClosingRankingSnapshot:
    """Resolve and append inside the caller-owned Season Transition transaction."""

    snapshot = resolve_canonical_season_closing_ranking(
        session,
        run_id=run_id,
        branch_id=branch_id,
        completed_week=completed_week,
    )
    return SeasonClosingRankingStore(session).append(snapshot)
