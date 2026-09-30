from __future__ import annotations

import json

import pytest

from beta_engine.application.viewer_finals_race_read_model import (
    resolve_viewer_finals_race_history,
)
from beta_engine.domain.finals.participant_selection import (
    WorldTourFinalsParticipantSelectionConfiguration,
    WorldTourFinalsSelectedPlayer,
    select_world_tour_finals_participants,
)
from beta_engine.domain.finals.race import (
    WorldTourFinalsRaceInput,
    WorldTourFinalsRacePlayer,
    WorldTourFinalsRaceResult,
    calculate_world_tour_finals_race,
)
from beta_engine.domain.finals.race_configuration import (
    WorldTourFinalsRaceConfiguration,
)
from beta_engine.domain.finals.race_replacement import (
    WorldTourFinalsEffectiveParticipantState,
    initial_effective_participant_state,
)
from beta_engine.domain.rankings.official import RankingWeek


pytestmark = pytest.mark.pr_critical


def fp(value: str) -> str:
    return (value * 64)[:64]


def race_and_selection():
    configuration = WorldTourFinalsRaceConfiguration(
        run_id="run",
        branch_id="branch",
        target_season_index=4,
        finals_event_id="FINALS-2004",
        eligible_categories=("DIAMOND",),
        best_n=2,
        cutoff_week=RankingWeek(season_index=4, week=55),
        cutoff_official_ranking_fingerprint=fp("a"),
        cutoff_transition_fingerprint=fp("b"),
        calendar_content_fingerprint=fp("c"),
        adopted_by_command_id="race-config",
    )
    race = calculate_world_tour_finals_race(
        WorldTourFinalsRaceInput(
            run_id="run",
            branch_id="branch",
            target_season_index=4,
            cutoff_week=configuration.cutoff_week,
            cutoff_official_ranking_fingerprint=(
                configuration.cutoff_official_ranking_fingerprint
            ),
            eligibility_fingerprint=configuration.eligibility_fingerprint,
            policy_id=configuration.policy_id,
            best_n=2,
            players=(
                WorldTourFinalsRacePlayer(player_id="P1", tie_break_token="t1"),
                WorldTourFinalsRacePlayer(player_id="P2", tie_break_token="t2"),
                WorldTourFinalsRacePlayer(player_id="P3", tie_break_token="t3"),
            ),
            eligible_results=(
                WorldTourFinalsRaceResult(
                    run_id="run",
                    branch_id="branch",
                    edition_id="E1",
                    event_id="E1",
                    player_id="P1",
                    completed_week=RankingWeek(season_index=4, week=10),
                    race_points=100,
                    source_award_fingerprint=fp("1"),
                ),
                WorldTourFinalsRaceResult(
                    run_id="run",
                    branch_id="branch",
                    edition_id="E2",
                    event_id="E2",
                    player_id="P1",
                    completed_week=RankingWeek(season_index=4, week=20),
                    race_points=25,
                    source_award_fingerprint=fp("2"),
                ),
                WorldTourFinalsRaceResult(
                    run_id="run",
                    branch_id="branch",
                    edition_id="E1",
                    event_id="E1",
                    player_id="P2",
                    completed_week=RankingWeek(season_index=4, week=10),
                    race_points=90,
                    source_award_fingerprint=fp("3"),
                ),
                WorldTourFinalsRaceResult(
                    run_id="run",
                    branch_id="branch",
                    edition_id="E1",
                    event_id="E1",
                    player_id="P3",
                    completed_week=RankingWeek(season_index=4, week=10),
                    race_points=80,
                    source_award_fingerprint=fp("4"),
                ),
            ),
        )
    )
    selection_config = WorldTourFinalsParticipantSelectionConfiguration(
        run_id="run",
        branch_id="branch",
        target_season_index=4,
        finals_event_id="FINALS-2004",
        participant_capacity=2,
        direct_entry_event_ids=(),
        race_snapshot_fingerprint=race.fingerprint,
        calendar_content_fingerprint=configuration.calendar_content_fingerprint,
        adopted_by_command_id="selection-config",
    )
    selection = select_world_tour_finals_participants(
        configuration=selection_config,
        race_snapshot=race,
        direct_entry_winners=(),
    )
    return race, selection


def component_with_replacement() -> dict[str, object]:
    race, selection = race_and_selection()
    initial = initial_effective_participant_state(
        selection,
        command_id="initial-effective",
    )
    replacement = WorldTourFinalsEffectiveParticipantState(
        run_id="run",
        branch_id="branch",
        target_season_index=4,
        finals_event_id="FINALS-2004",
        initial_selection_fingerprint=selection.fingerprint,
        race_snapshot_fingerprint=race.fingerprint,
        predecessor_fingerprint=initial.fingerprint,
        participants=(
            selection.participants[0],
            WorldTourFinalsSelectedPlayer(
                player_id="P3",
                race_rank=3,
                race_points=80,
                seed=2,
                qualification_source="race",
            ),
        ),
        participant_capacity=2,
        withdrawn_player_ids=("P2",),
        created_by_command_id="replace-p2-with-p3",
    )
    return {
        "finals_race_snapshots": [
            {
                "run_id": "run",
                "branch_id": "branch",
                "target_season_index": 4,
                "snapshot_fingerprint": race.fingerprint,
                "configuration_fingerprint": fp("d"),
                "input_fingerprint": race.input_fingerprint,
                "cutoff_week_ordinal": race.cutoff_week.ordinal,
                "payload_json": race.model_dump_json(),
            }
        ],
        "finals_participant_snapshots": [
            {
                "run_id": "run",
                "branch_id": "branch",
                "target_season_index": 4,
                "snapshot_fingerprint": selection.fingerprint,
                "configuration_fingerprint": selection.configuration_fingerprint,
                "race_snapshot_fingerprint": race.fingerprint,
                "payload_json": selection.model_dump_json(),
            }
        ],
        "finals_effective_states": [
            {
                "run_id": "run",
                "branch_id": "branch",
                "target_season_index": 4,
                "finals_event_id": "FINALS-2004",
                "sequence": 1,
                "state_fingerprint": initial.fingerprint,
                "predecessor_fingerprint": None,
                "command_id": initial.created_by_command_id,
                "payload_json": initial.model_dump_json(),
            },
            {
                "run_id": "run",
                "branch_id": "branch",
                "target_season_index": 4,
                "finals_event_id": "FINALS-2004",
                "sequence": 2,
                "state_fingerprint": replacement.fingerprint,
                "predecessor_fingerprint": initial.fingerprint,
                "command_id": replacement.created_by_command_id,
                "payload_json": replacement.model_dump_json(),
            },
        ],
    }


def test_viewer_finals_race_projects_saved_sporting_facts_and_latest_effective_field() -> None:
    result = resolve_viewer_finals_race_history(
        component_with_replacement(),
        run_id="run",
        branch_id="branch",
    )

    assert result.schema_version == "viewer_finals_race_history.v1"
    assert result.latest_target_season_index == 4
    assert len(result.publications) == 1
    publication = result.publications[0]
    assert publication.target_season_index == 4
    assert publication.cutoff_week == 55
    assert publication.best_n == 2
    assert publication.selection_published is True
    assert publication.finals_event_id == "FINALS-2004"
    assert [row.player_id for row in publication.rows] == ["P1", "P2", "P3"]
    assert [row.race_points for row in publication.rows] == [125, 90, 80]
    assert publication.rows[0].tournaments_counted == 2

    by_player = {row.player_id: row for row in publication.rows}
    assert by_player["P1"].finals_selected is True
    assert by_player["P1"].finals_seed == 1
    assert by_player["P2"].finals_selected is False
    assert by_player["P2"].finals_seed is None
    assert by_player["P3"].finals_selected is True
    assert by_player["P3"].finals_seed == 2
    assert by_player["P3"].qualification_source == "race"
    assert [item.event_id for item in by_player["P1"].counted_results] == ["E1", "E2"]

    rendered = json.dumps(result.model_dump(mode="json"), sort_keys=True)
    for forbidden in (
        "fingerprint",
        "tie_break_token",
        "policy_id",
        "command_id",
        "eligibility",
        "source_award",
        "withdrawn_player_ids",
        "predecessor",
    ):
        assert forbidden not in rendered


def test_viewer_finals_race_distinguishes_pending_selection_from_not_selected() -> None:
    race, _ = race_and_selection()
    component = {
        "finals_race_snapshots": [
            {
                "run_id": "run",
                "branch_id": "branch",
                "target_season_index": 4,
                "snapshot_fingerprint": race.fingerprint,
                "configuration_fingerprint": fp("d"),
                "input_fingerprint": race.input_fingerprint,
                "cutoff_week_ordinal": race.cutoff_week.ordinal,
                "payload_json": race.model_dump_json(),
            }
        ]
    }
    result = resolve_viewer_finals_race_history(
        component,
        run_id="run",
        branch_id="branch",
    )
    publication = result.publications[0]
    assert publication.selection_published is False
    assert publication.finals_event_id is None
    assert all(row.finals_selected is None for row in publication.rows)


def test_viewer_finals_race_fails_closed_on_tampered_outer_identity() -> None:
    component = component_with_replacement()
    component["finals_race_snapshots"][0]["snapshot_fingerprint"] = fp("f")
    with pytest.raises(ValueError, match="fingerprint"):
        resolve_viewer_finals_race_history(
            component,
            run_id="run",
            branch_id="branch",
        )
