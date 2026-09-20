import pytest

from beta_engine.application.authoritative_run_simulation_driver import (
    AuthoritativeEntryDecisionSlotCommand,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.infrastructure.db.models import RunBranchModel
from beta_engine.infrastructure.db.run_entry_decision_slots import (
    RunEntryDecisionSlotStore,
)
from test_authoritative_slot_matches import (
    _driver_fixture,
    _multi_driver_fixture,
)


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
def test_entry_slot_preview_fails_closed_when_compatibility_roster_drifts(
    tmp_path,
    monkeypatch,
):
    driver, _, _ = _driver_fixture(tmp_path / "entry-roster-drift")
    event_id = next(iter(driver.match_service._load_registry().matches_by_event_id))
    active_service = (
        driver.match_service.draw_service.entry_list_service.active_players_service
    )
    original = active_service.get_active_players(season="2000/2001")
    assert len(original.players) > 1
    drifted = original.model_copy(update={"players": original.players[:-1]})
    monkeypatch.setattr(
        active_service,
        "get_active_players",
        lambda *, season: drifted,
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
    driver, factory, _ = _driver_fixture(tmp_path / "stale-entry-head")
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
