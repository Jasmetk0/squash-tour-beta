"""Project canonical Run-owned tournament evidence into a Finals Race snapshot."""

from __future__ import annotations

from beta_engine.application.calendar_package_run_adapter import RunCalendarProjection
from beta_engine.domain.finals import (
    FinalsRaceConfiguration,
    FinalsRaceSnapshot,
    FinalsRaceTournamentAward,
    FinalsRaceTournamentSource,
    build_finals_race_snapshot,
)
from beta_engine.domain.rankings.tournament_source import OwnedTournamentRankingSource
from beta_engine.domain.rankings.transition_authority import RankingTransitionAuthority


def project_canonical_finals_race_snapshot(
    *,
    configuration: FinalsRaceConfiguration,
    calendar: RunCalendarProjection,
    tournament_sources: tuple[OwnedTournamentRankingSource, ...],
    transition_authority: RankingTransitionAuthority,
) -> FinalsRaceSnapshot:
    """Build one immutable Race snapshot from canonical Run/Branch-owned evidence."""

    if (calendar.run_id, calendar.branch_id) != (
        configuration.run_id,
        configuration.branch_id,
    ):
        raise ValueError("Finals Race Calendar projection scope mismatch")
    if calendar.content_fingerprint != configuration.calendar_content_fingerprint:
        raise ValueError("Finals Race Calendar projection fingerprint mismatch")
    if (
        transition_authority.run_id,
        transition_authority.branch_id,
        transition_authority.target_week,
        transition_authority.fingerprint,
    ) != (
        configuration.run_id,
        configuration.branch_id,
        configuration.cutoff_ranking_week,
        configuration.cutoff_transition_fingerprint,
    ):
        raise ValueError("Finals Race cutoff transition authority mismatch")

    events = {event.event_id: event for event in calendar.calendar.events}
    categories = {event.category for event in calendar.calendar.events}
    missing_categories = sorted(
        set(configuration.eligible_categories) - categories
    )
    if missing_categories:
        raise ValueError(
            "Finals Race configuration references categories absent from frozen Calendar: "
            + ", ".join(missing_categories)
        )

    projected_sources: list[FinalsRaceTournamentSource] = []
    for source in tournament_sources:
        binding = source.binding
        if (binding.run_id, binding.branch_id) != (
            configuration.run_id,
            configuration.branch_id,
        ):
            raise ValueError("Finals Race owned tournament source scope mismatch")
        if binding.completed_week.season_index != configuration.season_index:
            continue
        if (
            binding.first_publication_week is None
            or binding.first_publication_week.ordinal
            > configuration.cutoff_ranking_week.ordinal
        ):
            continue

        event = events.get(binding.event_id)
        if event is None:
            raise ValueError(
                "Finals Race canonical tournament source is absent from frozen Calendar"
            )
        if event.category not in configuration.eligible_categories:
            continue
        if source.canonical_awards is None:
            raise ValueError(
                "Finals Race eligible tournament requires canonical point-award authority"
            )
        if source.canonical_result is None:
            raise ValueError(
                "Finals Race eligible tournament requires canonical result authority"
            )
        awards = source.canonical_awards
        if (
            awards.run_id,
            awards.branch_id,
            awards.event_id,
            awards.completed_week,
            awards.fingerprint,
        ) != (
            configuration.run_id,
            configuration.branch_id,
            binding.event_id,
            binding.completed_week,
            binding.expected_award_fingerprint,
        ):
            raise ValueError("Finals Race canonical point-award evidence mismatch")

        projected_sources.append(
            FinalsRaceTournamentSource(
                run_id=configuration.run_id,
                branch_id=configuration.branch_id,
                event_id=binding.event_id,
                category=event.category,
                completed_week=binding.completed_week,
                first_publication_week=binding.first_publication_week,
                owned_source_fingerprint=source.fingerprint,
                point_award_fingerprint=awards.fingerprint,
                awards=tuple(
                    FinalsRaceTournamentAward(
                        player_id=award.player_id,
                        race_points_awarded=award.race_points_awarded,
                    )
                    for award in sorted(
                        awards.awards, key=lambda item: item.player_id
                    )
                ),
            )
        )

    return build_finals_race_snapshot(
        configuration=configuration,
        players=transition_authority.players,
        tournament_sources=tuple(
            sorted(projected_sources, key=lambda item: item.event_id)
        ),
        calendar_content_fingerprint=calendar.content_fingerprint,
        cutoff_transition_fingerprint=transition_authority.fingerprint,
    )
