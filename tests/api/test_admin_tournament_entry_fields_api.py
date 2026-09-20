"""Real HTTP/SQLite coverage for canonical Tournament Entry Field Admin routes."""

from __future__ import annotations

import pytest

from beta_engine.domain.rankings.official import (
    OfficialRankingPlayer,
    OfficialRankingPolicy,
    OfficialRankingResult,
    RankingWeek,
    calculate_official_ranking,
)
from beta_engine.domain.tournaments.application_submission_authority import (
    TournamentApplicationSubmissionAuthority,
)
from beta_engine.domain.tournaments.entry_field import (
    TournamentEntryApplication,
    TournamentEntryFieldCapacity,
)
from beta_engine.infrastructure.db.models import PublishedOfficialRankingModel
from beta_engine.infrastructure.db.tournament_draw_input_authority import (
    TournamentDrawInputAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_application_submissions import (
    TournamentApplicationSubmissionStore,
)
from beta_engine.infrastructure.db.tournament_entry_field import TournamentEntryFieldStore
from beta_engine.infrastructure.db.tournament_ranking_snapshot_authority import (
    TournamentRankingSnapshotAuthorityStore,
)
from tests.api.test_saved_revision_history_api import ApiServer, _create_run, _request


pytestmark = pytest.mark.smoke


def _ranking_snapshot(*, run_id: str, branch_id: str):
    completed = RankingWeek(season_index=0, week=1)
    published = RankingWeek(season_index=0, week=2)
    target = RankingWeek(season_index=0, week=3)
    points = {
        "A": 100,
        "B": 90,
        "C": 80,
        "D": 70,
        "E": 60,
        "F": 50,
        "G": 40,
    }
    players = tuple(
        OfficialRankingPlayer(
            player_id=player_id,
            tie_break_token=f"rank-{player_id}",
            tour_entry_week=RankingWeek(season_index=0, week=1),
        )
        for player_id in sorted(points)
    )
    results = tuple(
        OfficialRankingResult(
            edition_id=f"prior-{player_id}",
            player_id=player_id,
            source_fingerprint=f"source-{player_id}",
            completed_week=completed,
            first_publication_week=published,
            main_points=value,
        )
        for player_id, value in sorted(points.items())
    )
    return calculate_official_ranking(
        run_id=run_id,
        branch_id=branch_id,
        week=target,
        policy=OfficialRankingPolicy(policy_id="policy"),
        players=players,
        results=results,
    )


def _application(
    *,
    run_id: str,
    branch_id: str,
    event_id: str,
    player_id: str,
    window: str,
) -> TournamentEntryApplication:
    return TournamentEntryApplication(
        application_id=f"app-{player_id}",
        run_id=run_id,
        branch_id=branch_id,
        event_id=event_id,
        player_id=player_id,
        entry_window=window,
        decision_slot_ordinal=10,
        nr_tie_break_token=f"entry-{player_id}",
    )


def _install_entry_field(server, *, run_id: str, branch_id: str, event_id: str):
    snapshot = _ranking_snapshot(run_id=run_id, branch_id=branch_id)
    applications = (
        _application(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            player_id="A",
            window="main",
        ),
        _application(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            player_id="C",
            window="main",
        ),
        _application(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            player_id="D",
            window="main",
        ),
        _application(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            player_id="B",
            window="qualification",
        ),
        _application(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            player_id="E",
            window="qualification",
        ),
        _application(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            player_id="F",
            window="qualification",
        ),
        _application(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            player_id="G",
            window="qualification",
        ),
    )
    with server.app.state.runtime.repository._session_factory.begin() as session:
        session.add(
            PublishedOfficialRankingModel(
                run_id=run_id,
                branch_id=branch_id,
                week_ordinal=snapshot.week.ordinal,
                snapshot_fingerprint=snapshot.fingerprint,
                payload_json=snapshot.model_dump_json(),
            )
        )
        session.flush()
        TournamentRankingSnapshotAuthorityStore(session).adopt(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            ranking_week=snapshot.week,
            command_id="adopt-ranking",
        )
        return TournamentEntryFieldStore(session).stage_initial(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            applications=applications,
            capacity=TournamentEntryFieldCapacity(
                main_draw_size=4,
                qualification_draw_size=2,
                qualifier_spots=1,
            ),
            command_id="initial-field",
        )


def _valid_submission(
    *,
    run_id: str,
    branch_id: str,
    event_id: str,
    player_id: str,
    window: str,
) -> TournamentApplicationSubmissionAuthority:
    return TournamentApplicationSubmissionAuthority(
        application_id=f"valid-{player_id}",
        run_id=run_id,
        branch_id=branch_id,
        event_id=event_id,
        player_id=player_id,
        entry_window=window,
        submission_week=RankingWeek(season_index=0, week=2),
        decision_slot_ordinal=1,
        nr_tie_break_token=f"entry-{player_id}",
        validation_authority_id=f"validation-{player_id}",
        validation_authority_fingerprint="a" * 64,
        provenance="HTTP valid-submission fixture",
    )


def _root(server, run_id: str, branch_id: str, event_id: str) -> str:
    return (
        f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}"
        f"/tournaments/{event_id}/entry-field"
    )


def _command(
    *,
    run_id: str,
    branch_id: str,
    event_id: str,
    command_id: str,
    expected_field_fingerprint: str,
    withdrawn_player_ids: tuple[str, ...],
) -> dict:
    return {
        "schema_version": "canonical_pre_draw_withdrawal_command.v1",
        "command_id": command_id,
        "run_id": run_id,
        "branch_id": branch_id,
        "event_id": event_id,
        "expected_field_fingerprint": expected_field_fingerprint,
        "withdrawn_player_ids": list(withdrawn_player_ids),
    }


@pytest.mark.pr_critical
def test_initial_entry_field_can_be_created_from_persisted_valid_submissions_http(
    tmp_path,
):
    server = ApiServer(
        database_url=f"sqlite:///{tmp_path / 'valid-submission-field-api.sqlite'}"
    )
    with server:
        run_id, branch_id, _ = _create_run(
            server, display_name="Valid Submission Field HTTP"
        )
        event_id = "event"
        snapshot = _ranking_snapshot(run_id=run_id, branch_id=branch_id)
        with server.app.state.runtime.repository._session_factory.begin() as session:
            session.add(
                PublishedOfficialRankingModel(
                    run_id=run_id,
                    branch_id=branch_id,
                    week_ordinal=snapshot.week.ordinal,
                    snapshot_fingerprint=snapshot.fingerprint,
                    payload_json=snapshot.model_dump_json(),
                )
            )
            session.flush()
            TournamentRankingSnapshotAuthorityStore(session).adopt(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                ranking_week=snapshot.week,
                command_id="adopt-valid-submission-ranking",
            )
            submissions = TournamentApplicationSubmissionStore(session)
            for player_id, window in (
                ("A", "main"),
                ("C", "main"),
                ("D", "main"),
                ("B", "qualification"),
                ("E", "qualification"),
                ("F", "qualification"),
                ("G", "qualification"),
            ):
                submissions.append(
                    _valid_submission(
                        run_id=run_id,
                        branch_id=branch_id,
                        event_id=event_id,
                        player_id=player_id,
                        window=window,
                    )
                )

        root = _root(server, run_id, branch_id, event_id)
        status, field = _request(
            "POST",
            root + "/from-valid-submissions",
            {
                "command_id": "initial-from-valid-submissions",
                "capacity": {
                    "main_draw_size": 4,
                    "qualification_draw_size": 2,
                    "qualifier_spots": 1,
                },
            },
        )
        assert status == 201
        assert field["direct_main_player_ids"] == ["A", "C", "D"]
        assert field["qualification_player_ids"] == ["B", "E"]
        assert field["below_qualification_cut_player_ids"] == ["F", "G"]

        status, inspected = _request("GET", root)
        assert status == 200
        returned_field = TournamentEntryField.model_validate(field)
        assert inspected["field_fingerprint"] == returned_field.fingerprint


def test_canonical_entry_field_state_withdrawal_and_retry_over_http(tmp_path):
    server = ApiServer(database_url=f"sqlite:///{tmp_path / 'entry-field-api.sqlite'}")
    with server:
        run_id, branch_id, _ = _create_run(
            server, display_name="Canonical Entry Field HTTP"
        )
        event_id = "event"
        initial = _install_entry_field(
            server,
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        root = _root(server, run_id, branch_id, event_id)

        status, before = _request("GET", root)
        assert status == 200
        assert before["field_sequence"] == 1
        assert before["field_fingerprint"] == initial.fingerprint
        assert before["mode"] == "initial"
        assert before["direct_main_player_ids"] == ["A", "C", "D"]
        assert before["qualification_player_ids"] == ["B", "E"]
        assert before["schema_version"] == "canonical_tournament_entry_field_state.v2"
        assert before["main_draw_capacity"] == 4
        assert before["active_main_entrant_count"] == 4
        assert before["effective_main_bye_count"] == 0
        assert before["main_diagnostics"] == []
        assert before["draw_input_committed"] is False
        assert before["pre_draw_repair_locked_by_draw_input"] is False

        command = _command(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            command_id="withdraw-d",
            expected_field_fingerprint=initial.fingerprint,
            withdrawn_player_ids=("D",),
        )
        status, repaired = _request(
            "POST", root + "/pre-draw-withdrawal", command
        )
        assert status == 200
        assert repaired["field_sequence"] == 2
        assert repaired["newly_withdrawn_player_ids"] == ["D"]
        assert repaired["promoted_to_main_player_ids"] == ["B"]
        assert repaired["qualification_backfill_player_ids"] == ["F"]
        assert repaired["direct_main_player_ids"] == ["A", "B", "C"]
        assert repaired["qualification_player_ids"] == ["E", "F"]
        assert repaired["withdrawn_player_ids"] == ["D"]

        # Exact HTTP retry returns the same persisted result.
        assert _request("POST", root + "/pre-draw-withdrawal", command) == (
            200,
            repaired,
        )

        status, after = _request("GET", root)
        assert status == 200
        assert after["field_sequence"] == 2
        assert after["field_fingerprint"] == repaired["field_fingerprint"]
        assert after["mode"] == "pre_draw_repair"
        assert after["direct_main_player_ids"] == ["A", "B", "C"]
        assert after["qualification_player_ids"] == ["E", "F"]
        assert after["withdrawn_player_ids"] == ["D"]


@pytest.mark.pr_critical
def test_canonical_entry_field_warning_tracks_post_withdrawal_underfill(tmp_path):
    server = ApiServer(
        database_url=f"sqlite:///{tmp_path / 'entry-field-underfill.sqlite'}"
    )
    with server:
        run_id, branch_id, _ = _create_run(
            server, display_name="Dynamic Main Field Diagnostics"
        )
        event_id = "event"
        snapshot = _ranking_snapshot(run_id=run_id, branch_id=branch_id)

        with server.app.state.runtime.repository._session_factory.begin() as session:
            session.add(
                PublishedOfficialRankingModel(
                    run_id=run_id,
                    branch_id=branch_id,
                    week_ordinal=snapshot.week.ordinal,
                    snapshot_fingerprint=snapshot.fingerprint,
                    payload_json=snapshot.model_dump_json(),
                )
            )
            session.flush()
            TournamentRankingSnapshotAuthorityStore(session).adopt(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                ranking_week=snapshot.week,
                command_id="adopt-underfill-ranking",
            )
            initial = TournamentEntryFieldStore(session).stage_initial(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                applications=tuple(
                    _application(
                        run_id=run_id,
                        branch_id=branch_id,
                        event_id=event_id,
                        player_id=player_id,
                        window="main",
                    )
                    for player_id in ("A", "B", "C", "D")
                ),
                capacity=TournamentEntryFieldCapacity(main_draw_size=4),
                command_id="underfill-initial-field",
            )

        root = _root(server, run_id, branch_id, event_id)
        status, before = _request("GET", root)
        assert status == 200
        assert before["active_main_entrant_count"] == 4
        assert before["effective_main_bye_count"] == 0
        assert before["main_diagnostics"] == []

        status, repaired = _request(
            "POST",
            root + "/pre-draw-withdrawal",
            _command(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                command_id="withdraw-d-without-reserve",
                expected_field_fingerprint=initial.fingerprint,
                withdrawn_player_ids=("D",),
            ),
        )
        assert status == 200
        assert repaired["direct_main_player_ids"] == ["A", "B", "C"]

        status, after = _request("GET", root)
        assert status == 200
        assert after["main_draw_capacity"] == 4
        assert after["active_main_entrant_count"] == 3
        assert after["effective_main_bye_count"] == 1
        assert [item["code"] for item in after["main_diagnostics"]] == [
            "odd_main_entrant_count"
        ]
        assert after["main_diagnostics"][0]["entrant_count"] == 3
        assert after["main_diagnostics"][0]["bye_count"] == 1


@pytest.mark.pr_critical
def test_canonical_entry_field_http_exposes_odd_main_warning(tmp_path):
    server = ApiServer(database_url=f"sqlite:///{tmp_path / 'entry-field-odd.sqlite'}")
    with server:
        run_id, branch_id, _ = _create_run(
            server, display_name="Odd Main Field Diagnostics"
        )
        event_id = "event"
        snapshot = _ranking_snapshot(run_id=run_id, branch_id=branch_id)
        player_ids = tuple("ABCDEFG")

        with server.app.state.runtime.repository._session_factory.begin() as session:
            session.add(
                PublishedOfficialRankingModel(
                    run_id=run_id,
                    branch_id=branch_id,
                    week_ordinal=snapshot.week.ordinal,
                    snapshot_fingerprint=snapshot.fingerprint,
                    payload_json=snapshot.model_dump_json(),
                )
            )
            session.flush()
            TournamentRankingSnapshotAuthorityStore(session).adopt(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                ranking_week=snapshot.week,
                command_id="adopt-odd-ranking",
            )
            capacity = TournamentEntryFieldCapacity.for_main_entrant_count(
                main_entrant_count=len(player_ids),
            )
            assert capacity.main_draw_size == 8
            assert capacity.bye_slots == 1
            TournamentEntryFieldStore(session).stage_initial(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                applications=tuple(
                    _application(
                        run_id=run_id,
                        branch_id=branch_id,
                        event_id=event_id,
                        player_id=player_id,
                        window="main",
                    )
                    for player_id in player_ids
                ),
                capacity=capacity,
                command_id="odd-initial-field",
            )

        status, state = _request(
            "GET",
            _root(server, run_id, branch_id, event_id),
        )
        assert status == 200
        assert state["schema_version"] == "canonical_tournament_entry_field_state.v2"
        assert state["main_draw_capacity"] == 8
        assert state["active_main_entrant_count"] == 7
        assert state["effective_main_bye_count"] == 1

        diagnostics = state["main_diagnostics"]
        assert len(diagnostics) == 1
        warning = diagnostics[0]
        assert warning["severity"] == "warning"
        assert warning["code"] == "odd_main_entrant_count"
        assert warning["entrant_count"] == 7
        assert warning["bracket_capacity"] == 8
        assert warning["bye_count"] == 1
        assert warning["first_round_match_count"] == 4
        assert warning["first_round_bye_match_count"] == 1
        assert warning["first_round_bye_share"] == 0.25
        assert warning["message"].startswith("! Main Draw has an odd entrant count (7).")


def test_canonical_entry_field_http_rejects_stale_scope_and_post_draw_mutation(tmp_path):
    server = ApiServer(database_url=f"sqlite:///{tmp_path / 'entry-field-guards.sqlite'}")
    with server:
        run_id, branch_id, _ = _create_run(
            server, display_name="Canonical Entry Field Guards"
        )
        event_id = "event"
        initial = _install_entry_field(
            server,
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        root = _root(server, run_id, branch_id, event_id)

        first_command = _command(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            command_id="withdraw-d",
            expected_field_fingerprint=initial.fingerprint,
            withdrawn_player_ids=("D",),
        )
        status, first = _request(
            "POST", root + "/pre-draw-withdrawal", first_command
        )
        assert status == 200

        stale = _command(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            command_id="withdraw-e-stale",
            expected_field_fingerprint=initial.fingerprint,
            withdrawn_player_ids=("E",),
        )
        status, body = _request("POST", root + "/pre-draw-withdrawal", stale)
        assert status == 409
        assert body["detail"]["code"] == "canonical_pre_draw_withdrawal_conflict"
        assert "changed since" in body["detail"]["message"]

        wrong_scope = _command(
            run_id=run_id,
            branch_id=branch_id,
            event_id="other-event",
            command_id="wrong-scope",
            expected_field_fingerprint=first["field_fingerprint"],
            withdrawn_player_ids=("E",),
        )
        status, body = _request(
            "POST", root + "/pre-draw-withdrawal", wrong_scope
        )
        assert status == 409
        assert "scope mismatch" in body["detail"]["message"]

        with server.app.state.runtime.repository._session_factory.begin() as session:
            TournamentDrawInputAuthorityStore(session).commit(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                command_id="commit-draw",
                draw_seed=123,
            )

        status, locked_state = _request("GET", root)
        assert status == 200
        assert locked_state["draw_input_committed"] is True
        assert locked_state["pre_draw_repair_locked_by_draw_input"] is True

        locked = _command(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            command_id="withdraw-e",
            expected_field_fingerprint=first["field_fingerprint"],
            withdrawn_player_ids=("E",),
        )
        status, body = _request("POST", root + "/pre-draw-withdrawal", locked)
        assert status == 409
        assert "locked after Tournament Draw Input authority is committed" in body[
            "detail"
        ]["message"]

        # Historical retry remains valid after the draw commitment.
        assert _request(
            "POST", root + "/pre-draw-withdrawal", first_command
        ) == (200, first)


def test_canonical_entry_field_http_missing_and_invalid_command(tmp_path):
    server = ApiServer(database_url=f"sqlite:///{tmp_path / 'entry-field-errors.sqlite'}")
    with server:
        run_id, branch_id, _ = _create_run(
            server, display_name="Canonical Entry Field Errors"
        )
        event_id = "missing"
        root = _root(server, run_id, branch_id, event_id)

        assert _request("GET", root)[0] == 404

        invalid = {
            "command_id": "bad",
            "run_id": run_id,
            "branch_id": branch_id,
            "event_id": event_id,
            "expected_field_fingerprint": "not-a-fingerprint",
            "withdrawn_player_ids": ["D"],
        }
        assert _request("POST", root + "/pre-draw-withdrawal", invalid)[0] == 422