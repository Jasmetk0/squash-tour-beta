from __future__ import annotations

import hashlib
import json

import pytest

from beta_engine.application.canonical_tournament_points import (
    build_tournament_point_award_authority,
    project_tournament_point_award_legacy_dto,
)
from beta_engine.application.ranking_tournament_ingestion import (
    TournamentRankingBinding,
    prepare_canonical_tournament_ranking_sources,
)
from beta_engine.application.run_owned_match_package import (
    build_run_owned_match_package,
)
from beta_engine.application.season_point_awards_service import (
    FrozenPointAwardAuthority,
)
from beta_engine.application.official_ranking_transition import RankingTransitionContext
from beta_engine.application.ranking_week_command import RankingWeekCommand
from beta_engine.domain.rankings.official import (
    OfficialRankingPlayer,
    OfficialRankingPolicy,
    RankingWeek,
    calculate_official_ranking,
)
from beta_engine.domain.rankings.tournament_source import OwnedTournamentRankingSource
from beta_engine.domain.tournaments.draw_authority import TournamentDrawAuthorityBuilder
from beta_engine.domain.tournaments.draw_input_authority import TournamentDrawInputAuthority
from beta_engine.domain.tournaments.entry_field import TournamentEntryFieldCapacity
from beta_engine.domain.tournaments.models import CalendarEvent
from beta_engine.domain.tournaments.point_award_authority import (
    TournamentPointAwardAuthority,
)
from beta_engine.domain.tournaments.result_authority import (
    build_tournament_result_authority,
    project_tournament_result_legacy_dto,
)
from beta_engine.infrastructure.db.engine import (
    DatabaseSettings,
    create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.db.models import Base, RunBranchModel, RunContainerModel
from beta_engine.infrastructure.db.official_rankings import OfficialRankingCandidateStore
from beta_engine.infrastructure.db.owned_tournament_sources import (
    OwnedTournamentRankingSourceStore,
)
from beta_engine.infrastructure.db.ranking_week_command import RankingWeekCommandRunner


pytestmark = pytest.mark.smoke


@pytest.fixture
def database(tmp_path):
    engine = create_sqlite_engine(
        DatabaseSettings(url=f"sqlite:///{tmp_path / 'canonical-points.db'}")
    )
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    with factory.begin() as session:
        session.add(
            RunContainerModel(
                run_id="run",
                timeline_start_season=2000,
                timeline_end_season=2049,
            )
        )
        session.add(
            RunBranchModel(
                run_id="run",
                branch_id="branch",
                display_name="Timeline 1",
            )
        )
    yield factory
    engine.dispose()


def _input():
    return TournamentDrawInputAuthority(
        run_id="run",
        branch_id="branch",
        event_id="event",
        committed_by_command_id="input",
        draw_seed=4321,
        main_seed_count=2,
        qualification_seed_count=0,
        field_sequence=1,
        capacity=TournamentEntryFieldCapacity(
            main_draw_size=4,
            qualification_draw_size=0,
            qualifier_spots=0,
        ),
        tournament_ranking_authority_fingerprint="1" * 64,
        ranking_snapshot_fingerprint="2" * 64,
        entry_field_fingerprint="3" * 64,
        direct_main_player_ids=("A", "B", "C", "D"),
        qualification_player_ids=(),
        qualifier_placeholder_ids=(),
        withdrawn_player_ids=(),
        main_seed_player_ids=("A", "B"),
        qualification_seed_player_ids=(),
    )


def _event():
    return CalendarEvent(
        event_id="event",
        season="2000/2001",
        season_week=1,
        calendar_year=2000,
        year_week=1,
        template_id="template",
        event_name="Canonical Open",
        category="TEST",
        tour_level="WORLD_TOUR",
        host_country="CZE",
        region="Europe",
        main_draw_size=4,
        qualification_draw_size=0,
        qualifier_spots=0,
    )


def _complete(draw, package):
    projected = package.model_copy(deep=True)
    slots = {slot.slot_index: slot for slot in draw.main.slots}
    winners = {}
    by_id = {match.match_id: match for match in projected.main_draw_matches}

    def resolve(source):
        if source.startswith("winner:"):
            return winners[source.removeprefix("winner:")]
        slot = slots[int(source.removeprefix("slot:"))]
        return slot.player_id

    for node in sorted(
        draw.main.nodes,
        key=lambda item: (item.round_number, item.round_sequence),
    ):
        top = resolve(node.source_top)
        bottom = resolve(node.source_bottom)
        winner = top
        loser = bottom
        match = by_id[node.node_id]
        match.top_player_id = top
        match.bottom_player_id = bottom
        match.winner_player_id = winner
        match.loser_player_id = loser
        match.scoreline = "3-0"
        match.status = "completed"
        match.result_fingerprint = hashlib.sha256(
            f"{node.node_id}|{winner}|{loser}".encode()
        ).hexdigest()
        winners[node.node_id] = winner
    return projected


def _authorities():
    week = RankingWeek(season_index=0, week=1)
    draw = TournamentDrawAuthorityBuilder.build(
        draw_input=_input(),
        command_id="draw",
    )
    package = build_run_owned_match_package(
        draw=draw,
        event=_event(),
        week=week,
    )
    package = _complete(draw, package)
    result_authority = build_tournament_result_authority(
        run_id="run",
        branch_id="branch",
        week=week,
        draw=draw,
        package=package,
    )
    result = project_tournament_result_legacy_dto(
        authority=result_authority,
        event=_event(),
        package=package,
        seed=77,
    )
    frozen_points = FrozenPointAwardAuthority(
        ranking_status="ranked",
        point_distribution={
            "champion": 1000,
            "finalist": 650,
            "semifinal": 400,
            "quarterfinal": 250,
            "round_of_16": 120,
            "round_of_32": 60,
            "round_of_64": 30,
            "round_of_128": 10,
            "qualification_winner": 25,
            "qualification_final": 10,
            "qualification_semifinal": 5,
            "qualification_round": 0,
            "main_draw_participant": 0,
            "unknown": 0,
        },
        point_distribution_source="calendar_event.ranking_points_table",
    )
    point_authority = build_tournament_point_award_authority(
        result=result_authority,
        point_authority=frozen_points,
        seed=88,
    )
    awards = project_tournament_point_award_legacy_dto(
        authority=point_authority,
        result_authority=result_authority,
        result=result,
    )
    binding = TournamentRankingBinding(
        run_id="run",
        branch_id="branch",
        edition_id="event",
        event_id="event",
        completed_week=week,
        first_publication_week=RankingWeek(season_index=0, week=2),
        validity_weeks=61,
        ranking_status="ranked",
        expected_result_fingerprint=result_authority.fingerprint,
        expected_award_fingerprint=point_authority.fingerprint,
    )
    return result_authority, result, point_authority, awards, binding


def test_canonical_point_authority_maps_frozen_distribution_without_legacy_service():
    result_authority, _, point_authority, _, _ = _authorities()

    by_id = {award.player_id: award for award in point_authority.awards}
    assert by_id[result_authority.champion_player_id].ranking_points_awarded == 1000
    assert by_id[result_authority.finalist_player_id].ranking_points_awarded == 650
    semifinalists = [
        award
        for award in point_authority.awards
        if award.reached_stage == "semifinal"
    ]
    assert len(semifinalists) == 2
    assert all(award.ranking_points_awarded == 400 for award in semifinalists)
    assert point_authority.total_ranking_points == 2450
    assert point_authority.total_race_points == 2450


def test_canonical_point_authority_rejects_corrupt_distribution_on_reopen():
    _, _, point_authority, _, _ = _authorities()
    payload = point_authority.model_dump(mode="json")
    payload["point_distribution"][0][1] += 1

    with pytest.raises(ValueError, match="distribution snapshot mismatch"):
        TournamentPointAwardAuthority.model_validate(payload)


def test_canonical_point_authority_fails_closed_on_fallback_distribution():
    result_authority, _, _, _, _ = _authorities()
    with pytest.raises(ValueError, match="authored point distribution"):
        build_tournament_point_award_authority(
            result=result_authority,
            point_authority=FrozenPointAwardAuthority(
                ranking_status="ranked",
                point_distribution={"champion": 1000},
                point_distribution_source="fallback.default_stage_points",
            ),
            seed=88,
        )


def test_direct_canonical_ranking_materialization_uses_authority_fingerprints():
    result_authority, _, point_authority, _, binding = _authorities()
    versions = prepare_canonical_tournament_ranking_sources(
        binding,
        result_authority,
        point_authority,
    )

    assert {version.result.player_id for version in versions} == {
        player.player_id for player in result_authority.players
    }
    points = {
        version.result.player_id: version.result.main_points
        for version in versions
    }
    assert points[result_authority.champion_player_id] == 1000
    assert points[result_authority.finalist_player_id] == 650
    assert all(
        version.result.first_publication_week == RankingWeek(season_index=0, week=2)
        for version in versions
    )


def test_owned_source_v3_binds_canonical_points_and_compatibility_dto():
    result_authority, result, point_authority, awards, binding = _authorities()
    source = OwnedTournamentRankingSource(
        schema_version="owned_tournament_ranking_source.v3",
        binding=binding,
        result=result,
        awards=awards,
        canonical_result=result_authority,
        canonical_awards=point_authority,
        adopted_by_command_id="close",
        provenance_kind="canonical_run_owned_tournament_result_and_points",
    )
    assert (
        OwnedTournamentRankingSource.model_validate_json(source.model_dump_json())
        == source
    )

    changed = list(awards.awards)
    changed[0] = changed[0].model_copy(
        update={"ranking_points_awarded": changed[0].ranking_points_awarded + 1}
    )
    bad = awards.model_copy(update={"awards": changed})
    with pytest.raises(
        ValueError, match="point-award compatibility projection mismatch"
    ):
        OwnedTournamentRankingSource(
            schema_version="owned_tournament_ranking_source.v3",
            binding=binding,
            result=result,
            awards=bad,
            canonical_result=result_authority,
            canonical_awards=point_authority,
            adopted_by_command_id="close",
            provenance_kind="canonical_run_owned_tournament_result_and_points",
        )


def test_v2_fingerprint_contract_ignores_new_v3_field():
    result_authority, result, _, awards, _ = _authorities()
    legacy_binding = TournamentRankingBinding(
        run_id="run",
        branch_id="branch",
        edition_id="event",
        event_id="event",
        completed_week=RankingWeek(season_index=0, week=1),
        first_publication_week=RankingWeek(season_index=0, week=2),
        validity_weeks=61,
        ranking_status="ranked",
        expected_result_fingerprint=result.metadata.build_fingerprint,
        expected_award_fingerprint=awards.metadata.build_fingerprint,
    )
    v2 = OwnedTournamentRankingSource(
        schema_version="owned_tournament_ranking_source.v2",
        binding=legacy_binding,
        result=result,
        awards=awards,
        canonical_result=result_authority,
        adopted_by_command_id="old-close",
        provenance_kind="canonical_run_owned_tournament_result",
    )
    old_payload = v2.model_dump(mode="json")
    old_payload.pop("canonical_awards", None)
    expected = hashlib.sha256(
        json.dumps(old_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    historical_json = json.dumps(old_payload, sort_keys=True, separators=(",", ":"))
    reopened = OwnedTournamentRankingSource.model_validate_json(historical_json)

    assert reopened.schema_version == "owned_tournament_ranking_source.v2"
    assert reopened.canonical_awards is None
    assert reopened.fingerprint == expected



def test_ranking_week_ingests_v3_without_legacy_award_service(database):
    result_authority, result, point_authority, awards, binding = _authorities()
    source = OwnedTournamentRankingSource(
        schema_version="owned_tournament_ranking_source.v3",
        binding=binding,
        result=result,
        awards=awards,
        canonical_result=result_authority,
        canonical_awards=point_authority,
        adopted_by_command_id="close",
        provenance_kind="canonical_run_owned_tournament_result_and_points",
    )
    players = tuple(
        OfficialRankingPlayer(
            player_id=player.player_id,
            tie_break_token=player.player_id,
            tour_entry_week=RankingWeek(season_index=0, week=1),
        )
        for player in result_authority.players
    )
    policy = OfficialRankingPolicy(policy_id="policy")
    with database.begin() as session:
        OfficialRankingCandidateStore(session).append(
            calculate_official_ranking(
                run_id="run",
                branch_id="branch",
                week=binding.completed_week,
                policy=policy,
                players=players,
                results=(),
            ),
            bootstrap=True,
        )
        OwnedTournamentRankingSourceStore(session).append(source)

    command = RankingWeekCommand(
        command_id="ranking-from-canonical-points",
        tournaments=(binding,),
        context=RankingTransitionContext(
            run_id="run",
            branch_id="branch",
            completed_week=binding.completed_week,
            target_week=binding.first_publication_week,
            policy=policy,
            players=players,
            discipline="none",
        ),
    )
    snapshot = RankingWeekCommandRunner(database, awards=None).execute(command)
    expected = {
        award.player_id: award.ranking_points_awarded
        for award in point_authority.awards
    }
    assert {row.player_id: row.points for row in snapshot.rows} == expected
