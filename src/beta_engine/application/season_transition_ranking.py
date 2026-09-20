"""Ordinary Season Transition Official Ranking staging for next Season Week 1."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from beta_engine.application.official_ranking_transition import RankingTransitionContext
from beta_engine.application.ranking_tournament_ingestion import (
    prepare_canonical_tournament_ranking_sources,
    prepare_tournament_ranking_sources,
)
from beta_engine.application.ranking_week_command import RankingWeekCommand
from beta_engine.application.season_transition_configuration import (
    validate_season_transition_configuration,
)
from beta_engine.application.season_transition_lifecycle import (
    SeasonTransitionLifecycleStage,
    resolve_season_transition_lifecycle,
)
from beta_engine.domain.rankings.official import (
    FrozenInput,
    OfficialRankingResult,
    OfficialRankingSnapshot,
    calculate_official_ranking,
)
from beta_engine.domain.season_transition_configuration import SeasonTransitionConfiguration
from beta_engine.infrastructure.db.official_rankings import OfficialRankingCandidateStore
from beta_engine.infrastructure.db.owned_tournament_sources import (
    OwnedTournamentRankingSourceStore,
)
from beta_engine.infrastructure.db.ranking_result_history import OfficialRankingResultStore
from beta_engine.infrastructure.db.ranking_week_command import stage_ranking_week_command
from beta_engine.infrastructure.db.ranking_zero_history import OfficialRankingZeroStore


class SeasonTransitionRankingStage(FrozenInput):
    schema_version: Literal["season_transition_ranking_stage.v1"] = (
        "season_transition_ranking_stage.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    configuration_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    lifecycle_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    predecessor_official_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    ranking_command_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    target_snapshot: OfficialRankingSnapshot


def _owned_boundary_versions(session, configuration: SeasonTransitionConfiguration):
    bindings = []
    versions = []
    for source in OwnedTournamentRankingSourceStore(session).history(
        run_id=configuration.run_id,
        branch_id=configuration.branch_id,
    ):
        if source is None:
            raise ValueError("Season Transition owned tournament source history is incomplete")
        binding = source.binding
        if binding.completed_week != configuration.completed_week:
            continue
        if (
            binding.closing_only
            or binding.first_publication_week != configuration.target_week
            or source.schema_version == "owned_tournament_ranking_source.v6"
        ):
            raise ValueError(
                "Season Transition Week-61 tournament source has a non-canonical Week-1 publication boundary"
            )

        if source.schema_version in {
            "owned_tournament_ranking_source.v3",
            "owned_tournament_ranking_source.v4",
            "owned_tournament_ranking_source.v5",
        }:
            if source.canonical_result is None or source.canonical_awards is None:
                raise ValueError(
                    "Season Transition canonical Week-61 tournament source is incomplete"
                )
            projected = prepare_canonical_tournament_ranking_sources(
                binding,
                source.canonical_result,
                source.canonical_awards,
            )
        else:
            if source.result is None or source.awards is None:
                raise ValueError(
                    "Season Transition historical Week-61 tournament source is incomplete"
                )
            projected = prepare_tournament_ranking_sources(
                binding,
                source.result,
                source.awards,
            )

        if any(version.effective_week != configuration.target_week for version in projected):
            raise ValueError(
                "Season Transition tournament ranking source resolves outside target Week 1"
            )
        bindings.append(binding)
        versions.extend(projected)

    edition_ids = [binding.edition_id for binding in bindings]
    event_ids = [binding.event_id for binding in bindings]
    if len(set(edition_ids)) != len(edition_ids) or len(set(event_ids)) != len(event_ids):
        raise ValueError("Season Transition has duplicate Week-61 tournament sources")
    return tuple(sorted(bindings, key=lambda item: item.edition_id)), tuple(versions)


def _resolved_target_results(
    session,
    configuration: SeasonTransitionConfiguration,
    projected_versions,
) -> tuple[OfficialRankingResult, ...]:
    persisted = OfficialRankingResultStore(session).resolve(
        run_id=configuration.run_id,
        branch_id=configuration.branch_id,
        week=configuration.target_week,
    )
    projected = {
        (version.result.edition_id, version.result.player_id): version.result
        for version in projected_versions
    }
    if len(projected) != len(projected_versions):
        raise ValueError("Season Transition projected tournament results are duplicated")

    resolved = {
        (result.edition_id, result.player_id): result
        for result in persisted
    }
    for key, result in projected.items():
        current = resolved.get(key)
        if current is not None and current != result:
            raise ValueError(
                "Persisted Week-61 ranking result conflicts with owned tournament source"
            )
        resolved[key] = result

    for result in persisted:
        if result.completed_week == configuration.completed_week:
            key = (result.edition_id, result.player_id)
            if key not in projected:
                raise ValueError(
                    "Persisted Week-61 ranking result has no matching owned tournament source"
                )

    return tuple(resolved[key] for key in sorted(resolved))


def _ranking_command(
    configuration: SeasonTransitionConfiguration,
    lifecycle: SeasonTransitionLifecycleStage,
    bindings,
) -> RankingWeekCommand:
    return RankingWeekCommand(
        command_id=f"season-transition-ranking:{configuration.fingerprint[:64]}",
        context=RankingTransitionContext(
            run_id=configuration.run_id,
            branch_id=configuration.branch_id,
            completed_week=configuration.completed_week,
            target_week=configuration.target_week,
            policy=configuration.target_ranking_policy,
            players=lifecycle.target_state.ranking_roster(),
            discipline="stored_zeros",
        ),
        tournaments=bindings,
    )


def resolve_season_transition_ranking(
    session,
    configuration: SeasonTransitionConfiguration,
) -> SeasonTransitionRankingStage:
    """Resolve the exact incoming Week-1 Official Ranking without persistence."""

    configuration = validate_season_transition_configuration(session, configuration)
    lifecycle = resolve_season_transition_lifecycle(session, configuration)

    history = OfficialRankingCandidateStore(session).history(
        run_id=configuration.run_id,
        branch_id=configuration.branch_id,
    )
    predecessor = history[-1] if history else None
    if (
        predecessor is None
        or predecessor.week != configuration.completed_week
        or predecessor.fingerprint != configuration.predecessor_official_fingerprint
    ):
        raise ValueError(
            "Season Transition Ranking requires the current Week-61 Official Ranking head"
        )

    bindings, projected_versions = _owned_boundary_versions(session, configuration)
    results = _resolved_target_results(session, configuration, projected_versions)
    zeros = OfficialRankingZeroStore(session).resolve(
        run_id=configuration.run_id,
        branch_id=configuration.branch_id,
        week=configuration.target_week,
    )
    candidate = calculate_official_ranking(
        run_id=configuration.run_id,
        branch_id=configuration.branch_id,
        week=configuration.target_week,
        policy=configuration.target_ranking_policy,
        players=lifecycle.target_state.ranking_roster(),
        results=results,
        previous=predecessor,
        disciplinary_zeros=zeros,
    )
    command = _ranking_command(configuration, lifecycle, bindings)

    return SeasonTransitionRankingStage(
        run_id=configuration.run_id,
        branch_id=configuration.branch_id,
        configuration_fingerprint=configuration.fingerprint,
        lifecycle_fingerprint=lifecycle.target_state.fingerprint,
        predecessor_official_fingerprint=predecessor.fingerprint,
        ranking_command_fingerprint=command.fingerprint,
        target_snapshot=candidate,
    )


def stage_season_transition_ranking(
    session,
    configuration: SeasonTransitionConfiguration,
) -> SeasonTransitionRankingStage:
    """Persist Week-1 ranking inputs/candidate inside a caller-owned SQLite transaction."""

    expected = resolve_season_transition_ranking(session, configuration)
    lifecycle = resolve_season_transition_lifecycle(session, configuration)
    bindings, _ = _owned_boundary_versions(session, configuration)
    command = _ranking_command(configuration, lifecycle, bindings)
    installed = stage_ranking_week_command(session, None, command)
    if installed.fingerprint != expected.target_snapshot.fingerprint:
        raise ValueError(
            "Season Transition Week-1 ranking stage differs from read-only resolution"
        )
    return expected.model_copy(update={"target_snapshot": installed})
