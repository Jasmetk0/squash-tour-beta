from __future__ import annotations

import pytest

from beta_engine.application.authoritative_run_simulation_driver import (
    AuthoritativeWeekTournamentLockCommitCommand,
    AuthoritativeWeekTournamentLockPreviewRequest,
)
from beta_engine.domain.rankings.official import (
    OfficialRankingPolicy,
    calculate_official_ranking,
)
from beta_engine.domain.tournaments.entry_field import (
    TournamentEntryApplication,
    TournamentEntryFieldCapacity,
)
from beta_engine.infrastructure.db.models import PublishedOfficialRankingModel
from beta_engine.infrastructure.db.simulation_slot_state import (
    capture_saved_simulation_slots,
    restore_saved_simulation_slots,
)
from beta_engine.infrastructure.db.tournament_entry_field import (
    TournamentEntryFieldStore,
)
from beta_engine.infrastructure.db.tournament_ranking_snapshot_authority import (
    TournamentRankingSnapshotAuthorityStore,
)
from beta_engine.infrastructure.db.week_tournament_lock import (
    WeekTournamentLockStore,
)
from test_authoritative_slot_matches import _multi_driver_fixture


def _opening_players(package) -> tuple[str, ...]:
    return tuple(
        player_id
        for match in sorted(
            (item for item in package.main_draw_matches if item.round_number == 1),
            key=lambda item: item.bracket_position,
        )
        for player_id in (match.top_player_id, match.bottom_player_id)
        if player_id is not None
    )


def _stage_conflicting_fields(driver, factory, week, first, second):
    first_players = _opening_players(first)
    second_players = _opening_players(second)
    shared = first_players[0]
    event_players = {
        first.event_id: (shared, first_players[1], first_players[2]),
        second.event_id: (shared, second_players[0], second_players[1]),
    }

    with factory.begin() as session:
        snapshot = calculate_official_ranking(
            run_id="run",
            branch_id="branch",
            week=week,
            policy=OfficialRankingPolicy(policy_id="week-lock-test-ranking"),
            players=(),
            results=(),
            previous=None,
        )
        if session.get(
            PublishedOfficialRankingModel,
            ("run", "branch", week.ordinal),
        ) is None:
            session.add(
                PublishedOfficialRankingModel(
                    run_id="run",
                    branch_id="branch",
                    week_ordinal=week.ordinal,
                    snapshot_fingerprint=snapshot.fingerprint,
                    payload_json=snapshot.model_dump_json(),
                )
            )
            session.flush()

        ranking_store = TournamentRankingSnapshotAuthorityStore(session)
        field_store = TournamentEntryFieldStore(session)
        fields = {}
        for event_id, players in event_players.items():
            ranking_store.adopt(
                run_id="run",
                branch_id="branch",
                event_id=event_id,
                ranking_week=week,
                command_id=f"adopt-ranking-{event_id}",
            )
            applications = tuple(
                TournamentEntryApplication(
                    application_id=f"{event_id}-application-{index}",
                    run_id="run",
                    branch_id="branch",
                    event_id=event_id,
                    player_id=player_id,
                    entry_window="main",
                    decision_slot_ordinal=1,
                    nr_tie_break_token=f"{index:03d}",
                )
                for index, player_id in enumerate(players, start=1)
            )
            fields[event_id] = field_store.stage_initial(
                run_id="run",
                branch_id="branch",
                event_id=event_id,
                applications=applications,
                capacity=TournamentEntryFieldCapacity(main_draw_size=2),
                command_id=f"field-{event_id}",
            )

    return shared, event_players, fields


@pytest.mark.pr_critical
def test_week_tournament_lock_atomically_repairs_unselected_field_and_restores(tmp_path):
    driver, factory, week, first, second = _multi_driver_fixture(
        tmp_path / "week-lock"
    )
    shared, event_players, opening_fields = _stage_conflicting_fields(
        driver, factory, week, first, second
    )

    inspection = driver.inspect_week_tournament_lock(
        run_id="run",
        branch_id="branch",
    )
    assert inspection["lock_status"] == "required"
    assert inspection["conflicts"] == [
        {
            "player_id": shared,
            "eligible_event_ids": sorted((first.event_id, second.event_id)),
        }
    ]
    assert "Final Commitment" not in str(inspection)

    before_payload = {"content": {}}
    with factory() as session:
        capture_saved_simulation_slots(
            session,
            before_payload,
            run_id="run",
            branch_id="branch",
        )

    selected_event = first.event_id
    preview_request = AuthoritativeWeekTournamentLockPreviewRequest(
        command_id="week-lock-command",
        run_id="run",
        branch_id="branch",
        expected_week=week,
        expected_position_fingerprint=inspection["position_fingerprint"],
        expected_revision_id=inspection["expected_revision_id"],
        operator_label="Commissioner",
        audit_reason="Resolve overlapping accepted tournament fields",
        selections=(
            {
                "player_id": shared,
                "selected_event_id": selected_event,
            },
        ),
    )
    preview = driver.preview_week_tournament_lock(preview_request)
    assert preview["persisted"] is False
    assert preview["authority"]["player_locks"] == [
        {
            "player_id": shared,
            "eligible_event_ids": sorted((first.event_id, second.event_id)),
            "selected_event_id": selected_event,
        }
    ]

    command = AuthoritativeWeekTournamentLockCommitCommand(
        **preview_request.model_dump(),
        expected_authority_fingerprint=preview["authority_fingerprint"],
    )
    result = driver.commit_week_tournament_lock(command)
    assert result["adoption"] == "committed"
    assert result["authority_fingerprint"] == preview["authority_fingerprint"]
    assert result["field_repairs"] == [
        {
            "event_id": second.event_id,
            "withdrawn_player_ids": [shared],
            "field_fingerprint": result["field_repairs"][0]["field_fingerprint"],
        }
    ]
    assert driver.commit_week_tournament_lock(command) == result

    with factory() as session:
        field_store = TournamentEntryFieldStore(session)
        selected = field_store.latest(
            run_id="run",
            branch_id="branch",
            event_id=first.event_id,
        )
        unselected = field_store.latest(
            run_id="run",
            branch_id="branch",
            event_id=second.event_id,
        )
        assert selected is not None and unselected is not None
        assert selected.fingerprint == opening_fields[first.event_id].fingerprint
        assert shared in selected.direct_main_player_ids
        assert shared not in unselected.direct_main_player_ids
        assert shared in unselected.withdrawn_player_ids
        assert event_players[second.event_id][2] in unselected.direct_main_player_ids

        lock = WeekTournamentLockStore(session).get(
            run_id="run",
            branch_id="branch",
            week_ordinal=week.ordinal,
        )
        assert lock is not None
        assert lock.player_locks[0].selected_event_id == selected_event

        after_payload = {"content": {}}
        capture_saved_simulation_slots(
            session,
            after_payload,
            run_id="run",
            branch_id="branch",
        )
        assert after_payload["content"]["simulation_slot_match_state"][
            "week_tournament_locks"
        ][0]["authority_fingerprint"] == lock.fingerprint

        restore_saved_simulation_slots(
            session,
            current_payload=after_payload,
            target_payload=before_payload,
            run_id="run",
            branch_id="branch",
        )
        assert WeekTournamentLockStore(session).get(
            run_id="run",
            branch_id="branch",
            week_ordinal=week.ordinal,
        ) is None
        restored_before = field_store.latest(
            run_id="run",
            branch_id="branch",
            event_id=second.event_id,
        )
        assert restored_before is not None
        assert restored_before.fingerprint == opening_fields[second.event_id].fingerprint

        restore_saved_simulation_slots(
            session,
            current_payload=before_payload,
            target_payload=after_payload,
            run_id="run",
            branch_id="branch",
        )
        restored_lock = WeekTournamentLockStore(session).get(
            run_id="run",
            branch_id="branch",
            week_ordinal=week.ordinal,
        )
        assert restored_lock is not None
        restored_after = field_store.latest(
            run_id="run",
            branch_id="branch",
            event_id=second.event_id,
        )
        assert restored_after is not None
        assert restored_after.fingerprint == result["field_repairs"][0][
            "field_fingerprint"
        ]


@pytest.mark.pr_critical
def test_week_tournament_lock_rejects_partial_selection_without_mutation(tmp_path):
    driver, factory, week, first, second = _multi_driver_fixture(
        tmp_path / "week-lock-incomplete"
    )
    shared, _, opening_fields = _stage_conflicting_fields(
        driver, factory, week, first, second
    )
    inspection = driver.inspect_week_tournament_lock(
        run_id="run",
        branch_id="branch",
    )

    request = AuthoritativeWeekTournamentLockPreviewRequest(
        command_id="incomplete-lock",
        run_id="run",
        branch_id="branch",
        expected_week=week,
        expected_position_fingerprint=inspection["position_fingerprint"],
        expected_revision_id=inspection["expected_revision_id"],
        operator_label="Commissioner",
        audit_reason="Incomplete selection must fail",
        selections=(
            {
                "player_id": "not-a-conflict",
                "selected_event_id": first.event_id,
            },
        ),
    )
    with pytest.raises(ValueError, match="every and only conflict"):
        driver.preview_week_tournament_lock(request)

    with factory() as session:
        assert WeekTournamentLockStore(session).get(
            run_id="run",
            branch_id="branch",
            week_ordinal=week.ordinal,
        ) is None
        field_store = TournamentEntryFieldStore(session)
        for event_id, original in opening_fields.items():
            current = field_store.latest(
                run_id="run",
                branch_id="branch",
                event_id=event_id,
            )
            assert current is not None
            assert current.fingerprint == original.fingerprint
