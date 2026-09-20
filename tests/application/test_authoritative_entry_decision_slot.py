import pytest
from sqlalchemy import select

from beta_engine.application.authoritative_run_simulation_driver import (
    AuthoritativeApplicationValidationCommand,
    AuthoritativeEntryDecisionSlotCommand,
)
from beta_engine.domain.tournaments.application_validation_authority import (
    TournamentApplicationValidationAuthority,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.infrastructure.db.models import RunBranchModel, SimulationSlotModel
from beta_engine.infrastructure.db.player_lifecycle_state import get_lifecycle
from beta_engine.infrastructure.db.player_sporting_state import get_sporting
from beta_engine.infrastructure.db.run_entry_decision_slots import (
    RunEntryDecisionSlotStore,
)
from beta_engine.infrastructure.db.player_tour_entry_triggers import (
    PlayerTourEntryTriggerStore,
)
from beta_engine.infrastructure.db.tournament_application_submissions import (
    TournamentApplicationSubmissionStore,
)
from test_authoritative_slot_matches import (
    _driver_command,
    _driver_fixture,
    _multi_driver_fixture,
)


def _align_compatibility_roster(driver, factory, week):
    with factory() as session:
        lifecycle = get_lifecycle(
            session,
            run_id="run",
            branch_id="branch",
            week=week,
        )
        sporting = get_sporting(
            session,
            run_id="run",
            branch_id="branch",
            week=week,
        )
        assert lifecycle is not None and sporting is not None
        sporting_ids = {player.player_id for player in sporting.players}
        owned_ids = {
            player.player_id
            for player in lifecycle.players
            if player.status == "active" and player.player_id in sporting_ids
        }

    active_service = (
        driver.match_service.draw_service.entry_list_service.active_players_service
    )
    season = f"{2000 + week.season_index}/{2001 + week.season_index}"
    registry = active_service._load_registry()
    available = {
        player.player_id: player
        for player in registry.players_by_season.get(season, [])
    }
    assert owned_ids <= set(available)
    registry.players_by_season[season] = [
        available[player_id] for player_id in sorted(owned_ids)
    ]
    active_service._save_registry(registry)


def _lifecycle_tokens(factory, week):
    with factory() as session:
        lifecycle = get_lifecycle(
            session,
            run_id="run",
            branch_id="branch",
            week=week,
        )
        assert lifecycle is not None
        return {
            player.player_id: player.tie_break_token
            for player in lifecycle.players
        }


def _command_from_preview(preview, *, command_id="entry-slot"):
    return AuthoritativeEntryDecisionSlotCommand(
        command_id=command_id,
        run_id=preview["run_id"],
        branch_id=preview["branch_id"],
        expected_week=RankingWeek(**preview["week"]),
        expected_revision_id=preview["expected_revision_id"],
        decision_slot_ordinal=preview["decision_slot_ordinal"],
        event_ids=tuple(preview["event_ids"]),
        seed=preview["seed"],
        expected_entry_batch_fingerprint=preview["entry_batch_fingerprint"],
        expected_slot_fingerprint=preview["slot_fingerprint"],
    )


@pytest.mark.pr_critical
def test_single_event_entry_slot_preview_commit_and_retry_are_run_owned(tmp_path):
    driver, factory, week = _driver_fixture(tmp_path / "single-entry-slot")
    _align_compatibility_roster(driver, factory, week)
    entry_service = driver.match_service.draw_service.entry_list_service
    event_id = next(iter(driver.match_service._load_registry().matches_by_event_id))
    before_registry = entry_service._load_registry().model_dump(mode="json")

    preview = driver.preview_entry_decision_slot(
        run_id="run",
        branch_id="branch",
        event_ids=(event_id,),
        decision_slot_ordinal=1,
        seed=4201,
    )
    assert preview["week"] == week.model_dump(mode="json")
    assert preview["event_ids"] == [event_id]
    assert preview["decision_count"] == len(preview["authority"]["decisions"])
    assert preview["persisted"] is False

    command = _command_from_preview(preview)
    committed = driver.commit_entry_decision_slot(command)
    assert committed["adoption"] == "committed"
    assert committed["slot_fingerprint"] == preview["slot_fingerprint"]

    retry = driver.commit_entry_decision_slot(command)
    assert retry["adoption"] == "exact_retry"
    assert retry["slot_fingerprint"] == committed["slot_fingerprint"]

    with factory() as session:
        stored = RunEntryDecisionSlotStore(session).list(
            run_id="run",
            branch_id="branch",
        )
        assert len(stored) == 1
        assert stored[0].fingerprint == preview["slot_fingerprint"]
        assert stored[0].week == week
        assert stored[0].decision_slot_ordinal == 1

    # Authoritative Run preview/commit must not mutate the compatibility EntryList registry.
    assert entry_service._load_registry().model_dump(mode="json") == before_registry


@pytest.mark.pr_critical
def test_multi_event_entry_slot_uses_one_shared_snapshot_and_canonical_events(tmp_path):
    driver, factory, week, first, second = _multi_driver_fixture(
        tmp_path / "multi-entry-slot"
    )
    _align_compatibility_roster(driver, factory, week)
    event_ids = tuple(sorted((first.event_id, second.event_id)))
    preview = driver.preview_entry_decision_slot(
        run_id="run",
        branch_id="branch",
        event_ids=event_ids,
        decision_slot_ordinal=1,
        seed=7301,
    )

    assert preview["event_ids"] == list(event_ids)
    assert preview["decision_count"] == len(preview["authority"]["decisions"])
    assert {
        item["event_id"] for item in preview["authority"]["decisions"]
    } <= set(event_ids)

    result = driver.commit_entry_decision_slot(_command_from_preview(preview))
    assert result["adoption"] == "committed"

    with factory() as session:
        stored = RunEntryDecisionSlotStore(session).get(
            run_id="run",
            branch_id="branch",
            week_ordinal=week.ordinal,
            decision_slot_ordinal=1,
        )
        assert stored is not None
        assert stored.source_active_players_fingerprint == (
            preview["active_players_fingerprint"]
        )
        assert stored.source_application_decisions_fingerprint == (
            preview["application_decisions_fingerprint"]
        )


@pytest.mark.pr_critical
def test_entry_slot_validation_commits_valid_submission_and_first_tour_entry(tmp_path):
    driver, factory, week = _driver_fixture(tmp_path / "entry-validation-command")
    _align_compatibility_roster(driver, factory, week)
    event_id = next(iter(driver.match_service._load_registry().matches_by_event_id))
    preview = driver.preview_entry_decision_slot(
        run_id="run",
        branch_id="branch",
        event_ids=(event_id,),
        decision_slot_ordinal=1,
        seed=4201,
    )
    driver.commit_entry_decision_slot(_command_from_preview(preview))
    decisions = preview["authority"]["decisions"]
    assert decisions
    lifecycle_tokens = _lifecycle_tokens(factory, week)

    validations = []
    for index, decision in enumerate(decisions):
        valid = index == 0
        validations.append(
            TournamentApplicationValidationAuthority(
                validation_id=f"validation-{index + 1}",
                application_id=f"application-{index + 1}",
                run_id="run",
                branch_id="branch",
                week=week,
                decision_slot_ordinal=1,
                source_slot_fingerprint=preview["slot_fingerprint"],
                event_id=decision["event_id"],
                player_id=decision["player_id"],
                entry_window=(
                    "main" if decision["target"] == "MAIN" else "qualification"
                ),
                source_decision_fingerprint=decision[
                    "source_decision_fingerprint"
                ],
                outcome="valid" if valid else "invalid",
                nr_tie_break_token=(
                    lifecycle_tokens[decision["player_id"]] if valid else None
                ),
                validation_policy_id="explicit-test-policy.v1",
                validation_policy_fingerprint="f" * 64,
                reasons=() if valid else ("explicit_test_rejection",),
                provenance="explicit validation command test",
            )
        )

    command = AuthoritativeApplicationValidationCommand(
        run_id="run",
        branch_id="branch",
        expected_week=week,
        expected_revision_id=preview["expected_revision_id"],
        decision_slot_ordinal=1,
        expected_entry_slot_fingerprint=preview["slot_fingerprint"],
        validations=tuple(validations),
    )
    result = driver.commit_application_validation_slot(command)
    assert result["valid_submission_count"] == 1
    assert result["submission_batch_fingerprint"] is not None
    assert len(result["first_tour_entry_trigger_fingerprints"]) == 1

    retry = driver.commit_application_validation_slot(command)
    assert retry == result

    with factory() as session:
        submissions = TournamentApplicationSubmissionStore(session).list(
            run_id="run",
            branch_id="branch",
        )
        assert len(submissions) == 1
        assert submissions[0].player_id == decisions[0]["player_id"]
        trigger = PlayerTourEntryTriggerStore(session).get(
            run_id="run",
            branch_id="branch",
            player_id=decisions[0]["player_id"],
        )
        assert trigger is not None
        assert trigger.decision_slot_ordinal == 1
        assert trigger.trigger_week == week


@pytest.mark.pr_critical
def test_entry_slot_validation_rejects_forged_lifecycle_tie_break_token(tmp_path):
    driver, factory, week = _driver_fixture(tmp_path / "entry-validation-token-drift")
    _align_compatibility_roster(driver, factory, week)
    event_id = next(iter(driver.match_service._load_registry().matches_by_event_id))
    preview = driver.preview_entry_decision_slot(
        run_id="run",
        branch_id="branch",
        event_ids=(event_id,),
        decision_slot_ordinal=1,
        seed=4201,
    )
    driver.commit_entry_decision_slot(_command_from_preview(preview))
    decision = preview["authority"]["decisions"][0]

    validation = TournamentApplicationValidationAuthority(
        validation_id="forged-token-validation",
        application_id="forged-token-application",
        run_id="run",
        branch_id="branch",
        week=week,
        decision_slot_ordinal=1,
        source_slot_fingerprint=preview["slot_fingerprint"],
        event_id=decision["event_id"],
        player_id=decision["player_id"],
        entry_window=(
            "main" if decision["target"] == "MAIN" else "qualification"
        ),
        source_decision_fingerprint=decision["source_decision_fingerprint"],
        outcome="valid",
        nr_tie_break_token="forged-token",
        validation_policy_id="explicit-test-policy.v1",
        validation_policy_fingerprint="f" * 64,
        provenance="forged identity regression",
    )

    with pytest.raises(
        ValueError,
        match="NR tie-break token differs from authoritative lifecycle identity",
    ):
        driver.commit_application_validation_slot(
            AuthoritativeApplicationValidationCommand(
                run_id="run",
                branch_id="branch",
                expected_week=week,
                expected_revision_id=preview["expected_revision_id"],
                decision_slot_ordinal=1,
                expected_entry_slot_fingerprint=preview["slot_fingerprint"],
                validations=(
                    validation,
                    *tuple(
                        TournamentApplicationValidationAuthority(
                            validation_id=f"invalid-{index}",
                            application_id=f"invalid-application-{index}",
                            run_id="run",
                            branch_id="branch",
                            week=week,
                            decision_slot_ordinal=1,
                            source_slot_fingerprint=preview["slot_fingerprint"],
                            event_id=item["event_id"],
                            player_id=item["player_id"],
                            entry_window=(
                                "main"
                                if item["target"] == "MAIN"
                                else "qualification"
                            ),
                            source_decision_fingerprint=item[
                                "source_decision_fingerprint"
                            ],
                            outcome="invalid",
                            nr_tie_break_token=None,
                            validation_policy_id="explicit-test-policy.v1",
                            validation_policy_fingerprint="f" * 64,
                            reasons=("not_selected_for_forged_token_test",),
                            provenance="complete validation coverage",
                        )
                        for index, item in enumerate(
                            preview["authority"]["decisions"][1:], start=2
                        )
                    ),
                ),
            )
        )

    with factory() as session:
        assert TournamentApplicationSubmissionStore(session).list(
            run_id="run", branch_id="branch"
        ) == ()
        assert PlayerTourEntryTriggerStore(session).list(
            run_id="run", branch_id="branch"
        ) == ()


@pytest.mark.pr_critical
def test_entry_slot_preview_fails_closed_when_compatibility_roster_drifts(
    tmp_path,
    monkeypatch,
):
    driver, factory, week = _driver_fixture(tmp_path / "entry-roster-drift")
    _align_compatibility_roster(driver, factory, week)
    event_id = next(iter(driver.match_service._load_registry().matches_by_event_id))
    active_service = (
        driver.match_service.draw_service.entry_list_service.active_players_service
    )
    original = active_service.get_active_players(season="2000/2001")
    assert len(original.players) > 1
    drifted = original.model_copy(update={"players": original.players[:-1]})
    monkeypatch.setattr(
        type(active_service),
        "get_active_players",
        lambda self, *, season: drifted,
    )

    with pytest.raises(
        ValueError,
        match="Compatibility Entry AI roster differs",
    ):
        driver.preview_entry_decision_slot(
            run_id="run",
            branch_id="branch",
            event_ids=(event_id,),
            decision_slot_ordinal=1,
            seed=8111,
        )


@pytest.mark.pr_critical
def test_entry_slot_commit_rejects_stale_batch_fingerprint_without_persistence(tmp_path):
    driver, factory, week = _driver_fixture(tmp_path / "stale-entry-batch")
    _align_compatibility_roster(driver, factory, week)
    event_id = next(iter(driver.match_service._load_registry().matches_by_event_id))
    preview = driver.preview_entry_decision_slot(
        run_id="run",
        branch_id="branch",
        event_ids=(event_id,),
        decision_slot_ordinal=1,
        seed=9201,
    )
    command = _command_from_preview(preview).model_copy(
        update={"expected_entry_batch_fingerprint": "0" * 64}
    )

    with pytest.raises(ValueError, match="batch proposal is stale"):
        driver.commit_entry_decision_slot(command)

    with factory() as session:
        assert RunEntryDecisionSlotStore(session).list(
            run_id="run",
            branch_id="branch",
        ) == ()


@pytest.mark.pr_critical
def test_entry_slot_commit_rejects_stale_branch_head(tmp_path):
    driver, factory, week = _driver_fixture(tmp_path / "stale-entry-head")
    _align_compatibility_roster(driver, factory, week)
    event_id = next(iter(driver.match_service._load_registry().matches_by_event_id))
    preview = driver.preview_entry_decision_slot(
        run_id="run",
        branch_id="branch",
        event_ids=(event_id,),
        decision_slot_ordinal=1,
        seed=10101,
    )
    command = _command_from_preview(preview)

    with factory.begin() as session:
        branch = session.get(RunBranchModel, "branch")
        assert branch is not None
        branch.saved_head_revision_id = "new-revision"

    with pytest.raises(ValueError, match="Branch head is stale"):
        driver.commit_entry_decision_slot(command)

    with factory() as session:
        assert RunEntryDecisionSlotStore(session).list(
            run_id="run",
            branch_id="branch",
        ) == ()

@pytest.mark.pr_critical
def test_pending_entry_validation_blocks_match_slot_materialization(tmp_path):
    driver, factory, week, first, second = _multi_driver_fixture(
        tmp_path / "pending-entry-blocks-match"
    )
    _align_compatibility_roster(driver, factory, week)
    event_ids = tuple(sorted((first.event_id, second.event_id)))
    preview = driver.preview_entry_decision_slot(
        run_id="run",
        branch_id="branch",
        event_ids=event_ids,
        decision_slot_ordinal=1,
        seed=12001,
    )
    driver.commit_entry_decision_slot(_command_from_preview(preview))

    proposal = driver.propose_topological_schedule(
        run_id="run",
        branch_id="branch",
    )
    driver.adopt_topological_schedule_proposal(
        run_id="run",
        branch_id="branch",
        request_id="schedule-after-entry",
        expected_week=week,
        expected_schedule_fingerprint=proposal["schedule_fingerprint"],
        expected_position_fingerprint=proposal["position_fingerprint"],
    )

    command, before = _driver_command(driver, week, "blocked-by-entry-validation")
    assert before.current_slot_kind == "entry"
    assert before.slot_ordinal == 1
    assert before.current_slot_id == f"week-{week.ordinal}:entry-slot:1"
    assert before.current_slot_complete is False
    assert "entry_validation_pending" in before.transition_blockers

    with pytest.raises(
        ValueError,
        match="nearest unresolved global Simulation Slot is an Entry decision slot",
    ):
        driver.simulate_next_slot(command)

    with factory() as session:
        materialized = tuple(
            session.scalars(
                select(SimulationSlotModel).where(
                    SimulationSlotModel.run_id == "run",
                    SimulationSlotModel.branch_id == "branch",
                    SimulationSlotModel.week_ordinal == week.ordinal,
                )
            ).all()
        )
        assert materialized == ()

    validations = tuple(
        TournamentApplicationValidationAuthority(
            validation_id=f"resolve-{index + 1}",
            application_id=f"resolve-application-{index + 1}",
            run_id="run",
            branch_id="branch",
            week=week,
            decision_slot_ordinal=1,
            source_slot_fingerprint=preview["slot_fingerprint"],
            event_id=decision["event_id"],
            player_id=decision["player_id"],
            entry_window=(
                "main" if decision["target"] == "MAIN" else "qualification"
            ),
            source_decision_fingerprint=decision["source_decision_fingerprint"],
            outcome="invalid",
            nr_tie_break_token=None,
            validation_policy_id="explicit-test-policy.v1",
            validation_policy_fingerprint="f" * 64,
            reasons=("explicit_test_resolution",),
            provenance="resolve pending Entry slot for chronology test",
        )
        for index, decision in enumerate(preview["authority"]["decisions"])
    )
    driver.commit_application_validation_slot(
        AuthoritativeApplicationValidationCommand(
            run_id="run",
            branch_id="branch",
            expected_week=week,
            expected_revision_id=preview["expected_revision_id"],
            decision_slot_ordinal=1,
            expected_entry_slot_fingerprint=preview["slot_fingerprint"],
            validations=validations,
        )
    )

    after = driver.position(run_id="run", branch_id="branch")
    assert after.current_slot_kind == "match"
    assert after.slot_ordinal is not None
    assert after.slot_ordinal > 1
    assert "entry_validation_pending" not in after.transition_blockers

