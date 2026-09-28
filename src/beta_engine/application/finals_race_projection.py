"""Canonical projection from Run-owned season evidence into the Finals Race kernel."""

from __future__ import annotations

from beta_engine.application.calendar_package_run_adapter import RunCalendarProjection
from beta_engine.domain.finals import (
    WorldTourFinalsRaceConfiguration,
    WorldTourFinalsRaceInput,
    WorldTourFinalsRacePlayer,
    WorldTourFinalsRaceResult,
    WorldTourFinalsRaceSnapshot,
    calculate_world_tour_finals_race,
)
from beta_engine.domain.rankings.official import OfficialRankingSnapshot
from beta_engine.domain.rankings.tournament_source import OwnedTournamentRankingSource
from beta_engine.domain.rankings.transition_authority import RankingTransitionAuthority


def project_canonical_world_tour_finals_race_input(
    *,
    configuration: WorldTourFinalsRaceConfiguration,
    calendar: RunCalendarProjection,
    cutoff_publication: OfficialRankingSnapshot,
    transition_authority: RankingTransitionAuthority,
    tournament_sources: tuple[OwnedTournamentRankingSource, ...],
) -> WorldTourFinalsRaceInput:
    """Freeze canonical source evidence for one configured seasonal Race."""

    if (calendar.run_id, calendar.branch_id) != (
        configuration.run_id,
        configuration.branch_id,
    ):
        raise ValueError("Finals Race Calendar projection scope mismatch")
    if calendar.content_fingerprint != configuration.calendar_content_fingerprint:
        raise ValueError("Finals Race Calendar projection fingerprint mismatch")

    if (
        cutoff_publication.run_id,
        cutoff_publication.branch_id,
        cutoff_publication.week,
        cutoff_publication.fingerprint,
    ) != (
        configuration.run_id,
        configuration.branch_id,
        configuration.cutoff_week,
        configuration.cutoff_official_ranking_fingerprint,
    ):
        raise ValueError("Finals Race cutoff publication identity mismatch")

    if (
        transition_authority.run_id,
        transition_authority.branch_id,
        transition_authority.target_week,
        transition_authority.fingerprint,
    ) != (
        configuration.run_id,
        configuration.branch_id,
        configuration.cutoff_week,
        configuration.cutoff_transition_fingerprint,
    ):
        raise ValueError("Finals Race cutoff transition authority mismatch")
    if cutoff_publication.policy != transition_authority.policy:
        raise ValueError(
            "Finals Race cutoff publication policy differs from Ranking Transition"
        )

    events = {event.event_id: event for event in calendar.calendar.events}
    finals_event = events.get(configuration.finals_event_id)
    if finals_event is None:
        raise ValueError(
            "Finals Race configuration references a Finals Edition absent from frozen Calendar"
        )
    if finals_event.season != calendar.season:
        raise ValueError("Finals Race Edition belongs to another Calendar season")
    if configuration.cutoff_week.week > finals_event.season_week:
        raise ValueError(
            "Finals Race cutoff must not be later than the configured Finals Edition"
        )

    available_categories = {event.category for event in calendar.calendar.events}
    missing_categories = sorted(
        set(configuration.eligible_categories) - available_categories
    )
    if missing_categories:
        raise ValueError(
            "Finals Race configuration references categories absent from frozen Calendar: "
            + ", ".join(missing_categories)
        )

    transition_players = {
        player.player_id: player for player in transition_authority.players
    }
    published_player_ids = tuple(row.player_id for row in cutoff_publication.rows)
    if any(player_id not in transition_players for player_id in published_player_ids):
        raise ValueError(
            "Finals Race published cutoff roster is absent from Ranking Transition authority"
        )
    # The selected Official Ranking is the Race time boundary, not a player-eligibility
    # or ordering authority. Freeze the transition roster and its stored tie tokens;
    # later Finals participant selection handles availability/qualification separately.
    players = tuple(
        WorldTourFinalsRacePlayer(
            player_id=player.player_id,
            tie_break_token=player.tie_break_token,
        )
        for player in sorted(
            transition_authority.players,
            key=lambda item: item.player_id,
        )
    )

    eligible_results: list[WorldTourFinalsRaceResult] = []
    seen_editions: set[str] = set()
    for source in sorted(
        tournament_sources,
        key=lambda item: (
            item.binding.completed_week.ordinal,
            item.binding.edition_id,
            item.binding.event_id,
        ),
    ):
        binding = source.binding
        if (binding.run_id, binding.branch_id) != (
            configuration.run_id,
            configuration.branch_id,
        ):
            raise ValueError("Finals Race owned tournament source scope mismatch")
        if binding.completed_week.season_index != configuration.target_season_index:
            continue
        if (
            binding.first_publication_week is None
            or binding.first_publication_week.ordinal > configuration.cutoff_week.ordinal
        ):
            continue

        event = events.get(binding.event_id)
        if event is None:
            raise ValueError(
                "Finals Race canonical tournament source is absent from frozen Calendar"
            )
        if event.category not in configuration.eligible_categories:
            continue
        if binding.edition_id in seen_editions:
            raise ValueError("Finals Race contains duplicate eligible Edition source")
        seen_editions.add(binding.edition_id)

        if source.canonical_result is None or source.canonical_awards is None:
            raise ValueError(
                "Finals Race eligible tournament requires canonical result and point-award authority"
            )
        result = source.canonical_result
        awards = source.canonical_awards
        if (
            result.run_id,
            result.branch_id,
            result.event_id,
            result.completed_week,
            result.fingerprint,
        ) != (
            configuration.run_id,
            configuration.branch_id,
            binding.event_id,
            binding.completed_week,
            binding.expected_result_fingerprint,
        ):
            raise ValueError("Finals Race canonical tournament result evidence mismatch")
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

        for award in awards.awards:
            if award.player_id not in transition_players:
                raise ValueError(
                    "Finals Race tournament source references player outside cutoff transition roster"
                )
            eligible_results.append(
                WorldTourFinalsRaceResult(
                    run_id=configuration.run_id,
                    branch_id=configuration.branch_id,
                    edition_id=binding.edition_id,
                    event_id=binding.event_id,
                    player_id=award.player_id,
                    completed_week=binding.completed_week,
                    race_points=award.race_points_awarded,
                    source_award_fingerprint=award.award_fingerprint,
                )
            )

    return WorldTourFinalsRaceInput(
        run_id=configuration.run_id,
        branch_id=configuration.branch_id,
        target_season_index=configuration.target_season_index,
        cutoff_week=configuration.cutoff_week,
        cutoff_official_ranking_fingerprint=(
            configuration.cutoff_official_ranking_fingerprint
        ),
        eligibility_fingerprint=configuration.eligibility_fingerprint,
        policy_id=configuration.policy_id,
        best_n=configuration.best_n,
        players=players,
        eligible_results=tuple(eligible_results),
    )


def build_canonical_world_tour_finals_race_snapshot(
    *,
    configuration: WorldTourFinalsRaceConfiguration,
    calendar: RunCalendarProjection,
    cutoff_publication: OfficialRankingSnapshot,
    transition_authority: RankingTransitionAuthority,
    tournament_sources: tuple[OwnedTournamentRankingSource, ...],
) -> WorldTourFinalsRaceSnapshot:
    """Project canonical evidence and execute the single Race calculation kernel."""

    source = project_canonical_world_tour_finals_race_input(
        configuration=configuration,
        calendar=calendar,
        cutoff_publication=cutoff_publication,
        transition_authority=transition_authority,
        tournament_sources=tournament_sources,
    )
    return calculate_world_tour_finals_race(source)
