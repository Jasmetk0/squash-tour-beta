from __future__ import annotations

import json

import pytest
from sqlalchemy import select

from beta_engine.application.authoritative_run_simulation_driver import (
    AuthoritativeSimulationCommand,
    AuthoritativeWalkoverCommand,
)
from beta_engine.application.season_match_service import (
    MatchPackageGenerateRequest,
    MatchSimulateRequest,
)
from beta_engine.application.authoritative_slot_matches import (
    AuthoritativeSlotMatchExecutor,
)
from beta_engine.core import DeterministicRng
from beta_engine.domain.matches import MatchEngine, MatchInputSnapshot
from beta_engine.infrastructure.db.models import (
    AuthoritativeSimulationCommandModel,
    OwnedTournamentRankingSourceModel,
    RunBranchModel,
    RunContainerModel,
    SimulationEventGroupModel,
    SimulationSlotModel,
)
from beta_engine.infrastructure.db.owned_tournament_sources import (
    OwnedTournamentRankingSourceStore,
)

from test_authoritative_slot_matches import _driver_command, _driver_fixture
from test_season_match_service import make_match_service


pytestmark = pytest.mark.smoke


def test_adopted_tournament_freezes_point_authority(tmp_path):
    driver, factory, week = _driver_fixture(tmp_path / "frozen-awards")
    semifinals, _ = _driver_command(driver, week, "semifinals")
    driver.simulate_next_slot(semifinals)

    match_registry = driver.match_service._load_registry()
    event_id = next(iter(match_registry.matches_by_event_id))
    calendar_service = driver.awards_service.calendar_service
    calendar_registry = calendar_service._load_registry()
    calendar = calendar_registry.calendars_by_season["2000/2001"]
    event = next(item for item in calendar.events if item.event_id == event_id)
    event.ranking_points_table = {
        "winner": 999,
        "finalist": 888,
        "semifinalist": 777,
    }
    event.point_distribution_ref = None
    calendar_service._save_registry(calendar_registry)

    final, _ = _driver_command(driver, week, "final")
    driver.simulate_next_slot(final)
    with factory() as session:
        source = OwnedTournamentRankingSourceStore(session).history(
            run_id="run", branch_id="branch"
        )[0]
        by_stage = {
            award.reached_stage: award.ranking_points_awarded
            for award in source.awards.awards
        }
        assert by_stage["champion"] == 100
        assert by_stage["finalist"] == 60
        assert by_stage["semifinal"] == 30


@pytest.mark.parametrize("scope", ["run", "branch", "archived"])
def test_simulation_rejects_non_writable_scope_before_any_write(tmp_path, scope):
    driver, factory, week = _driver_fixture(tmp_path / scope)
    command, _ = _driver_command(driver, week, f"blocked-{scope}")
    with factory.begin() as session:
        if scope == "run":
            session.get(RunContainerModel, "run").read_only = 1
        else:
            branch = session.get(RunBranchModel, "branch")
            if scope == "branch":
                branch.read_only = 1
            else:
                branch.status = "archived"

    with pytest.raises(ValueError, match="not writable"):
        driver.simulate_next_slot(command)

    with factory() as session:
        assert session.scalars(select(SimulationSlotModel)).all() == []
        assert session.scalars(select(SimulationEventGroupModel)).all() == []
        assert session.scalars(select(AuthoritativeSimulationCommandModel)).all() == []
        assert session.scalars(select(OwnedTournamentRankingSourceModel)).all() == []


@pytest.mark.pr_critical
def test_terminal_walkover_closes_canonical_tournament_with_stage_points(tmp_path):
    driver, factory, week = _driver_fixture(tmp_path / "walkover-close")

    semifinals, _ = _driver_command(driver, week, "walkover-semifinals")
    driver.simulate_next_slot(semifinals)

    position = driver.position(run_id="run", branch_id="branch")
    assert len(position.eligible_match_ids) == 1
    final_match_id = position.eligible_match_ids[0]

    with factory() as session:
        semifinal_rows = session.scalars(
            select(SimulationEventGroupModel).where(
                SimulationEventGroupModel.run_id == "run",
                SimulationEventGroupModel.branch_id == "branch",
                SimulationEventGroupModel.week_ordinal == week.ordinal,
            )
        ).all()
        semifinal_groups = [
            AuthoritativeSlotMatchExecutor._load_group(row)
            for row in semifinal_rows
            if row.match_id != final_match_id
        ]
        assert len(semifinal_groups) == 2
        withdrawn = semifinal_groups[0].result.winner_player_id

    payload = driver.commit_post_cutoff_walkover(
        AuthoritativeWalkoverCommand(
            command_id="walkover-final-close",
            run_id="run",
            branch_id="branch",
            expected_week=week,
            expected_position_fingerprint=position.position_fingerprint,
            expected_revision_id="revision",
            group_id=final_match_id,
            withdrawn_player_id=withdrawn,
        )
    )

    assert payload["walkover"]["scoreline"] == "W/O"
    assert payload["walkover"]["withdrawn_player_id"] == withdrawn
    assert payload["position"]["supported_tournament_complete"] is True

    with factory() as session:
        sources = OwnedTournamentRankingSourceStore(session).history(
            run_id="run",
            branch_id="branch",
        )
        assert len(sources) == 1
        source = sources[0]
        assert source.schema_version == "owned_tournament_ranking_source.v4"
        assert source.canonical_result is not None
        assert source.canonical_awards is not None

        result = source.canonical_result
        awards = {
            award.player_id: award
            for award in source.canonical_awards.awards
        }
        walkover_match = next(
            match for match in result.matches if match.match_id == final_match_id
        )
        assert walkover_match.scoreline == "W/O"

        winner = next(
            player
            for player in result.players
            if player.player_id == walkover_match.winner_player_id
        )
        loser = next(
            player
            for player in result.players
            if player.player_id == walkover_match.loser_player_id
        )
        assert winner.reached_stage == "champion"
        assert winner.walkovers_received == 1
        assert winner.wins == 1
        assert loser.reached_stage == "finalist"
        assert loser.retired_or_walkover_loss is True
        assert loser.losses == 0

        assert awards[winner.player_id].reached_stage == "champion"
        assert awards[loser.player_id].reached_stage == "finalist"
        assert awards[winner.player_id].ranking_points_awarded > (
            awards[loser.player_id].ranking_points_awarded
        )


def test_pending_next_slot_accepts_matching_close_by_other_commands(tmp_path):
    driver, factory, week = _driver_fixture(tmp_path / "interleaving")
    pending, _ = _driver_command(driver, week, "pending-slot")
    with pytest.raises(RuntimeError, match="before second"):
        driver.simulate_next_slot(pending, fault_at="before_second_group")

    position = driver.position(run_id="run", branch_id="branch")
    other = AuthoritativeSimulationCommand(
        command_id="other-semifinal",
        run_id="run",
        branch_id="branch",
        expected_week=week,
        expected_position_fingerprint=position.position_fingerprint,
        expected_revision_id="revision",
        group_id=position.eligible_match_ids[0],
    )
    driver.simulate_next_match(other)
    final, _ = _driver_command(driver, week, "other-final")
    driver.simulate_next_slot(final)

    resumed = driver.simulate_next_slot(pending)
    assert resumed["supported_tournament_complete"] is True
    with factory() as session:
        assert len(session.scalars(select(SimulationEventGroupModel)).all()) == 3
        assert len(
            OwnedTournamentRankingSourceStore(session).history(
                run_id="run", branch_id="branch"
            )
        ) == 1
        receipt = session.get(
            AuthoritativeSimulationCommandModel,
            ("run", "branch", "pending-slot"),
        )
        assert receipt.status == "complete"


def test_pending_next_slot_still_fails_closed_on_mismatching_owned_source(tmp_path):
    driver, factory, week = _driver_fixture(tmp_path / "interleaving-conflict")
    pending, _ = _driver_command(driver, week, "pending-slot")
    with pytest.raises(RuntimeError, match="before second"):
        driver.simulate_next_slot(pending, fault_at="before_second_group")
    position = driver.position(run_id="run", branch_id="branch")
    other = AuthoritativeSimulationCommand(
        command_id="other-semifinal",
        run_id="run",
        branch_id="branch",
        expected_week=week,
        expected_position_fingerprint=position.position_fingerprint,
        expected_revision_id="revision",
        group_id=position.eligible_match_ids[0],
    )
    driver.simulate_next_match(other)
    final, _ = _driver_command(driver, week, "other-final")
    driver.simulate_next_slot(final)

    with factory.begin() as session:
        row = session.scalar(select(OwnedTournamentRankingSourceModel))
        payload = json.loads(row.payload_json)
        payload["result"]["match_result_refs"][0]["result_fingerprint"] = "0" * 64
        row.payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        # Make the store-level fingerprint agree so the driver must detect the
        # semantic mismatch rather than relying only on row corruption checks.
        from beta_engine.domain.rankings.tournament_source import OwnedTournamentRankingSource

        changed = OwnedTournamentRankingSource.model_validate(payload)
        row.source_fingerprint = changed.fingerprint

    with pytest.raises(ValueError, match="Conflicting owned tournament source"):
        driver.simulate_next_slot(pending)


def test_legacy_replay_reader_accepts_v10_snapshot(tmp_path):
    service, event_id = make_match_service(tmp_path / "replay-v10")
    service.generate_match_package(
        event_id=event_id,
        request=MatchPackageGenerateRequest(seed=101, dry_run=False),
    )
    package = service.simulate_next_match(
        event_id=event_id,
        request=MatchSimulateRequest(seed=777),
    ).match_package
    assert package is not None
    completed = next(
        match
        for match in package.qualification_matches + package.main_draw_matches
        if match.status == "completed"
    )
    old = completed.match_input_snapshot
    assert old is not None
    current = MatchInputSnapshot.create(
        context=old.context,
        effective_match_format=old.effective_match_format,
        simulation_seed=old.simulation_seed,
        match_engine_version="match_engine_v10",
        effective_match_timing=old.effective_match_timing,
        effective_match_stamina=old.effective_match_stamina,
        rally_calibration_profile=old.rally_calibration_profile,
        effective_match_gameplans=old.effective_match_gameplans,
        effective_rally_rules=old.effective_rally_rules,
    )
    result = MatchEngine(rng=DeterministicRng(current.simulation_seed)).simulate(
        current.context,
        log_anchor_hash=current.snapshot_hash,
        effective_match_timing=current.effective_match_timing,
        effective_match_stamina=current.effective_match_stamina,
        rally_calibration_profile=current.rally_calibration_profile,
        effective_match_gameplans=current.effective_match_gameplans,
        effective_rally_rules=current.effective_rally_rules,
    )
    result_payload = result.model_dump(mode="json")
    result_fp = service._fingerprint(
        {
            "event_id": event_id,
            "match_id": completed.match_id,
            "match_input_snapshot_hash": current.snapshot_hash,
            "result": result_payload,
        }
    )

    registry = service._load_registry()
    stored = next(
        match
        for match in (
            registry.matches_by_event_id[event_id].qualification_matches
            + registry.matches_by_event_id[event_id].main_draw_matches
        )
        if match.match_id == completed.match_id
    )
    prior = stored.simulated_result
    assert prior is not None
    scoreline = service._scoreline(result.winner_player_id, result.sets)
    match_log_hash = (
        result.stamina_log.match_log_hash
        if result.stamina_log is not None
        else result.timeline_log.match_log_hash
        if result.timeline_log is not None
        else result.rally_log.match_log_hash
        if result.rally_log is not None
        else None
    )
    rally_elapsed_seconds = (
        result.rally_log.rally_elapsed_seconds if result.rally_log is not None else None
    )
    match_elapsed_seconds = (
        result.timeline_log.total_elapsed_seconds
        if result.timeline_log is not None
        else rally_elapsed_seconds
    )

    stored.match_input_snapshot = current
    stored.winner_player_id = result.winner_player_id
    stored.loser_player_id = result.loser_player_id
    stored.scoreline = scoreline
    stored.simulated_result = prior.model_copy(
        update={
            "winner_player_id": result.winner_player_id,
            "loser_player_id": result.loser_player_id,
            "scoreline": scoreline,
            "games": [item.model_dump(mode="json") for item in result.sets],
            "points_summary": {
                "sets_won": result.sets_won,
                "best_of": result.best_of,
                "games_to": result.games_to,
                "win_by": result.win_by,
            },
            "retired": result.retired_player_id is not None,
            "walkover": False,
            "simulation_fingerprint": result_fp,
            "seed": current.simulation_seed,
            "rally_log": result.rally_log,
            "timeline_log": result.timeline_log,
            "stamina_log": result.stamina_log,
            "match_log_hash": match_log_hash,
            "rally_elapsed_seconds": rally_elapsed_seconds,
            "match_elapsed_seconds": match_elapsed_seconds,
        }
    )
    stored.result_fingerprint = result_fp
    stored.simulation_seed = current.simulation_seed
    service._save_registry(registry)

    replay = service.get_match_replay(event_id=event_id, match_id=completed.match_id)
    assert replay.verified is True
    assert replay.match_input_snapshot.schema_version == "match_input_snapshot.v10"
    assert replay.final_result.simulation_fingerprint == result_fp
    assert replay.rng_rerun is False
