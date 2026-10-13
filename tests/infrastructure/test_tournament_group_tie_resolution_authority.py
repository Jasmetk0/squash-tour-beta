"""Persistence coverage for audited group tie-resolution command semantics."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from beta_engine.domain.matches.formats import EffectiveMatchFormatSnapshot, MatchFormat
from beta_engine.domain.tournaments.group_match_schedule_authority import (
    TournamentGroupMatchScheduleAuthority,
    TournamentGroupScheduledMatch,
)
from beta_engine.domain.tournaments.group_standings_authority import (
    TournamentGroupPlayedGame,
    TournamentGroupResultReceipt,
)
from beta_engine.infrastructure.db.models import Base, RunBranchModel, RunContainerModel
from beta_engine.infrastructure.db import tournament_group_tie_resolution_authority as module
from beta_engine.infrastructure.db.tournament_group_tie_resolution_authority import (
    TournamentGroupTieResolutionAuthorityConflict,
    TournamentGroupTieResolutionAuthorityStore,
)


def fp(char: str) -> str:
    return char * 64


def schedule() -> TournamentGroupMatchScheduleAuthority:
    fmt = EffectiveMatchFormatSnapshot.create(
        format=MatchFormat(best_of=3, games_to=11, win_by=2),
        source_scope="tournament_group_rules_policy",
        source_key="tie-resolution-test",
    )
    pairs = (
        ("A-B", 1, 1, 2, "A", "B"),
        ("A-C", 2, 1, 3, "A", "C"),
        ("B-C", 3, 2, 3, "B", "C"),
    )
    return TournamentGroupMatchScheduleAuthority(
        run_id="run",
        branch_id="branch",
        event_id="event",
        generated_by_command_id="schedule",
        format_authority_fingerprint=fp("a"),
        topology_authority_fingerprint=fp("b"),
        group_rules_policy_fingerprint=fp("c"),
        group_count=1,
        group_size=3,
        match_day_count=3,
        matches=tuple(
            TournamentGroupScheduledMatch(
                match_id=match_id,
                group_index=1,
                topology_match_index=index,
                match_day_ordinal=index,
                match_order=1,
                top_slot_index=top_slot,
                bottom_slot_index=bottom_slot,
                top_player_id=top,
                bottom_player_id=bottom,
                effective_match_format=fmt,
            )
            for match_id, index, top_slot, bottom_slot, top, bottom in pairs
        ),
    )


def played_receipt(
    *,
    match_id: str,
    winner: str,
    loser: str,
    char: str,
) -> TournamentGroupResultReceipt:
    return TournamentGroupResultReceipt(
        match_id=match_id,
        group_index=1,
        result_fingerprint=fp(char),
        result_kind="played",
        winner_player_id=winner,
        loser_player_id=loser,
        best_of=3,
        termination_reason="COMPLETED",
        games=(
            TournamentGroupPlayedGame(
                winner_player_id=winner,
                loser_player_id=loser,
                winner_points=11,
                loser_points=9,
            ),
            TournamentGroupPlayedGame(
                winner_player_id=loser,
                loser_player_id=winner,
                winner_points=11,
                loser_points=9,
            ),
            TournamentGroupPlayedGame(
                winner_player_id=winner,
                loser_player_id=loser,
                winner_points=11,
                loser_points=9,
            ),
        ),
    )


@pytest.mark.pr_critical
def test_group_tie_resolution_exact_retry_survives_after_case_is_resolved(
    monkeypatch,
):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = Session(engine)
    session.add(
        RunContainerModel(
            run_id="run",
            display_name="Tie resolution test",
            timeline_start_season=2000,
            timeline_end_season=2049,
        )
    )
    session.add(
        RunBranchModel(
            branch_id="branch",
            run_id="run",
            display_name="Timeline 1",
        )
    )
    session.flush()

    frozen_schedule = schedule()
    receipts = (
        played_receipt(match_id="A-B", winner="A", loser="B", char="1"),
        played_receipt(match_id="A-C", winner="C", loser="A", char="2"),
        played_receipt(match_id="B-C", winner="B", loser="C", char="3"),
    )

    class FakeScheduleStore:
        def __init__(self, session):
            self.session = session

        def get(self, *, run_id: str, branch_id: str, event_id: str):
            assert (run_id, branch_id, event_id) == ("run", "branch", "event")
            return frozen_schedule

    monkeypatch.setattr(module, "TournamentGroupMatchScheduleAuthorityStore", FakeScheduleStore)
    monkeypatch.setattr(
        module.TournamentGroupStandingsAuthorityStore,
        "_result_receipts",
        lambda self, **kwargs: receipts,
    )

    store = TournamentGroupTieResolutionAuthorityStore(session)
    case = store.current_unresolved_case(
        run_id="run",
        branch_id="branch",
        event_id="event",
    )
    assert case is not None
    assert case.player_ids == ("A", "B", "C")

    first = store.resolve(
        run_id="run",
        branch_id="branch",
        event_id="event",
        command_id="resolve-tie",
        case_fingerprint=case.fingerprint,
        ordered_player_ids=("C", "A", "B"),
        admin_reason="Reviewed exact unresolved evidence.",
    )
    session.flush()

    # The recorded decision now resolves the only open case.
    assert (
        store.current_unresolved_case(
            run_id="run",
            branch_id="branch",
            event_id="event",
        )
        is None
    )

    # Lost-response retry still replays the completed command exactly.
    retry = store.resolve(
        run_id="run",
        branch_id="branch",
        event_id="event",
        command_id="resolve-tie",
        case_fingerprint=case.fingerprint,
        ordered_player_ids=("C", "A", "B"),
        admin_reason="Reviewed exact unresolved evidence.",
    )
    assert retry == first

    with pytest.raises(
        TournamentGroupTieResolutionAuthorityConflict,
        match="different request",
    ):
        store.resolve(
            run_id="run",
            branch_id="branch",
            event_id="event",
            command_id="resolve-tie",
            case_fingerprint=case.fingerprint,
            ordered_player_ids=("A", "C", "B"),
            admin_reason="Reviewed exact unresolved evidence.",
        )

    session.close()


@pytest.mark.pr_critical
def test_sqlite_reopen_preserves_intermediate_audit_without_publishing_standings(
    tmp_path, monkeypatch,
):
    """Real SQLite rows survive reconnect before separately frozen final tables.

    Domain-level competitive results are deterministic fixtures: this is not
    presented as a browser simulation of three real played matches.
    """
    from beta_engine.application.run_saved_tour_group_schedule import (
        RunSavedTourGroupSchedule,
    )
    from beta_engine.application.run_saved_tour_group_standings import (
        resolve_saved_tour_group_standings,
    )
    from beta_engine.infrastructure.db import (
        tournament_group_standings_authority as standings_module,
    )
    from beta_engine.infrastructure.db.models import (
        TournamentGroupTieResolutionAuthorityModel,
        TournamentGroupStandingsAuthorityModel,
    )
    from beta_engine.infrastructure.db.tournament_group_standings_authority import (
        TournamentGroupStandingsAuthorityStore,
    )

    uri = f"sqlite:///{tmp_path / 'durable_group_tie.sqlite'}"
    database = create_engine(uri)
    Base.metadata.create_all(database)
    with Session(database) as session:
        session.add(RunContainerModel(
            run_id="run", display_name="Intermediate group tie",
            timeline_start_season=2000, timeline_end_season=2049,
        ))
        session.add(RunBranchModel(
            branch_id="branch", run_id="run", display_name="Test Branch",
        ))
        session.commit()

    frozen_schedule = schedule()
    receipts = (
        played_receipt(match_id="A-B", winner="A", loser="B", char="1"),
        played_receipt(match_id="A-C", winner="C", loser="A", char="2"),
        played_receipt(match_id="B-C", winner="B", loser="C", char="3"),
    )

    class RealScheduleFixture:
        def __init__(self, session):
            self.session = session

        def get(self, *, run_id, branch_id, event_id):
            assert (run_id, branch_id, event_id) == ("run", "branch", "event")
            return frozen_schedule

    monkeypatch.setattr(module, "TournamentGroupMatchScheduleAuthorityStore", RealScheduleFixture)
    monkeypatch.setattr(
        standings_module, "TournamentGroupMatchScheduleAuthorityStore", RealScheduleFixture,
    )
    monkeypatch.setattr(
        standings_module.TournamentGroupStandingsAuthorityStore,
        "_result_receipts", lambda self, **kwargs: receipts,
    )
    saved_schedule = RunSavedTourGroupSchedule(
        run_id="run", revision_branch_id="branch", event_id="event",
        authority_fingerprint=frozen_schedule.fingerprint,
        group_count=1, group_size=3, match_day_count=3, matches=(),
    )

    with Session(database) as session:
        tie_store = TournamentGroupTieResolutionAuthorityStore(session)
        case = tie_store.current_unresolved_case(
            run_id="run", branch_id="branch", event_id="event",
        )
        assert case and case.player_ids == ("A", "B", "C")
        tie_store.resolve(
            run_id="run", branch_id="branch", event_id="event",
            command_id="intermediate-audited-tie",
            case_fingerprint=case.fingerprint,
            ordered_player_ids=("C", "A", "B"),
            admin_reason="Operator reviewed genuine cyclical sporting evidence.",
        )
        session.commit()
    database.dispose()

    # A different engine and connection must see the persisted audited case.
    database = create_engine(uri)
    with Session(database) as session:
        tie_store = TournamentGroupTieResolutionAuthorityStore(session)
        decisions = tie_store.list_authorities(
            run_id="run", branch_id="branch", event_id="event",
        )
        assert len(decisions) == 1
        assert decisions[0].decision.ordered_player_ids == ("C", "A", "B")
        assert tie_store.current_unresolved_case(
            run_id="run", branch_id="branch", event_id="event",
        ) is None

        tie_row = session.get(
            TournamentGroupTieResolutionAuthorityModel,
            ("run", "branch", "event", decisions[0].case.fingerprint),
        )
        assert tie_row is not None
        saved_tie = {
            "run_id": tie_row.run_id, "branch_id": tie_row.branch_id,
            "event_id": tie_row.event_id, "command_id": tie_row.command_id,
            "authority_fingerprint": tie_row.authority_fingerprint,
            "case_fingerprint": tie_row.case_fingerprint,
            "group_match_schedule_fingerprint": tie_row.group_match_schedule_fingerprint,
            "payload_json": tie_row.payload_json,
        }
        interim = {"group_tie_resolutions": [saved_tie]}
        assert resolve_saved_tour_group_standings(
            interim, run_id="run", branch_id="branch",
            event_id="event", group_schedule=saved_schedule,
        ) is None

        final = TournamentGroupStandingsAuthorityStore(session).generate(
            run_id="run", branch_id="branch", event_id="event",
            command_id="generate-after-interim-reopen",
        )
        session.commit()
        row = session.get(
            TournamentGroupStandingsAuthorityModel, ("run", "branch", "event"),
        )
        assert row is not None
        frozen = resolve_saved_tour_group_standings(
            {
                **interim,
                "group_standings": [{
                    "run_id": row.run_id, "branch_id": row.branch_id,
                    "event_id": row.event_id, "command_id": row.command_id,
                    "authority_fingerprint": row.authority_fingerprint,
                    "group_match_schedule_fingerprint": row.group_match_schedule_fingerprint,
                    "group_rules_policy_fingerprint": row.group_rules_policy_fingerprint,
                    "payload_json": row.payload_json,
                }],
            },
            run_id="run", branch_id="branch", event_id="event",
            group_schedule=saved_schedule,
        )
        assert frozen and frozen.authority_fingerprint == final.fingerprint
        assert [p.player_id for p in frozen.groups[0].rows] == ["C", "A", "B"]
        assert len(frozen.tie_decisions) == 1
        # An earlier saved interim component must remain an unfinalized table.
        assert resolve_saved_tour_group_standings(
            interim, run_id="run", branch_id="branch",
            event_id="event", group_schedule=saved_schedule,
        ) is None
    database.dispose()
