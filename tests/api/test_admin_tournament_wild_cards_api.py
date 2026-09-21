"""Real HTTP coverage for canonical explicit Admin WC/RWC review."""

from __future__ import annotations

import pytest

from beta_engine.domain.calendar.season_weeks import (
    age_at_calendar_position,
    season_week_to_calendar_position,
)
from beta_engine.domain.players.lifecycle import (
    PlayerLifecycleIdentity,
    PlayerLifecycleWeekState,
)
from beta_engine.domain.rankings.official import (
    OfficialRankingPlayer,
    OfficialRankingPolicy,
    OfficialRankingResult,
    RankingWeek,
    calculate_official_ranking,
)
from beta_engine.domain.tournaments.entry_field import (
    TournamentEntryApplication,
    TournamentEntryFieldCapacity,
)
from beta_engine.infrastructure.db.models import (
    AuthoritativeWorldStateModel,
    PublishedOfficialRankingModel,
    RunBranchModel,
    RunContainerModel,
)
from beta_engine.infrastructure.db.player_lifecycle_state import put_lifecycle
from beta_engine.infrastructure.db.tournament_entry_field import TournamentEntryFieldStore
from beta_engine.infrastructure.db.tournament_ranking_snapshot_authority import (
    TournamentRankingSnapshotAuthorityStore,
)
from tests.api.test_saved_revision_history_api import ApiServer, _request


pytestmark = pytest.mark.smoke

WEEK = RankingWeek(season_index=0, week=3)


def _player(player_id: str, *, pre_tour: bool = False) -> PlayerLifecycleIdentity:
    position = season_week_to_calendar_position(2000, WEEK.week)
    return PlayerLifecycleIdentity(
        player_id=player_id,
        birth_year=1980,
        birth_year_week=1,
        tie_break_token=f"token-{player_id}",
        tie_break_provenance="canonical WC HTTP fixture",
        tour_entry_week=None if pre_tour else RankingWeek(season_index=0, week=1),
        age=age_at_calendar_position(
            birth_year=1980,
            birth_year_week=1,
            calendar_year=position.calendar_year,
            year_week=position.year_week,
        ),
        status="active",
        origin="canonical-wc-http-fixture",
    )


def _application(player_id: str, window: str) -> TournamentEntryApplication:
    return TournamentEntryApplication(
        application_id=f"app-{player_id}",
        run_id="run",
        branch_id="branch",
        event_id="event",
        player_id=player_id,
        entry_window=window,
        decision_slot_ordinal=10,
        nr_tie_break_token=f"entry-{player_id}",
    )


def _install(server: ApiServer) -> None:
    completed = RankingWeek(season_index=0, week=1)
    published = RankingWeek(season_index=0, week=2)
    points = {
        "A": 100,
        "B": 90,
        "C": 80,
        "D": 70,
        "E": 60,
        "F": 50,
        "G": 40,
    }
    ranking = calculate_official_ranking(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        policy=OfficialRankingPolicy(policy_id="canonical-wc-http-ranking"),
        players=tuple(
            OfficialRankingPlayer(
                player_id=player_id,
                tie_break_token=f"rank-{player_id}",
                tour_entry_week=RankingWeek(season_index=0, week=1),
            )
            for player_id in sorted(points)
        ),
        results=tuple(
            OfficialRankingResult(
                edition_id=f"prior-{player_id}",
                player_id=player_id,
                source_fingerprint=f"source-{player_id}",
                completed_week=completed,
                first_publication_week=published,
                main_points=value,
            )
            for player_id, value in sorted(points.items())
        ),
    )
    factory = server.app.state.runtime.repository._session_factory
    with factory.begin() as session:
        session.add(
            RunContainerModel(
                run_id="run",
                display_name="Run",
                storage_kind="custom_local",
                read_only=0,
                timeline_start_season=2000,
                timeline_end_season=2049,
                official_branch_id="branch",
                status="working",
            )
        )
        session.add(
            RunBranchModel(
                run_id="run",
                branch_id="branch",
                display_name="Timeline 1",
                status="active",
                read_only=0,
                saved_head_revision_id="revision-1",
            )
        )
        session.add(
            PublishedOfficialRankingModel(
                run_id="run",
                branch_id="branch",
                week_ordinal=WEEK.ordinal,
                snapshot_fingerprint=ranking.fingerprint,
                payload_json=ranking.model_dump_json(),
            )
        )
        session.add(
            AuthoritativeWorldStateModel(
                run_id="run",
                branch_id="branch",
                current_ordinal=WEEK.ordinal,
                ranking_fingerprint=ranking.fingerprint,
            )
        )
        put_lifecycle(
            session,
            PlayerLifecycleWeekState(
                run_id="run",
                branch_id="branch",
                week=WEEK,
                players=tuple(
                    sorted(
                        (
                            *(_player(player_id) for player_id in "ABCDEFG"),
                            _player("PROSPECT", pre_tour=True),
                        ),
                        key=lambda player: player.player_id,
                    )
                ),
                source_initial_world_fingerprint="world",
            ),
        )
        TournamentRankingSnapshotAuthorityStore(session).adopt(
            run_id="run",
            branch_id="branch",
            event_id="event",
            ranking_week=WEEK,
            command_id="adopt-ranking",
        )
        TournamentEntryFieldStore(session).stage_initial(
            run_id="run",
            branch_id="branch",
            event_id="event",
            applications=(
                _application("A", "main"),
                _application("C", "main"),
                _application("D", "main"),
                _application("B", "qualification"),
                _application("E", "qualification"),
                _application("F", "qualification"),
                _application("G", "qualification"),
            ),
            capacity=TournamentEntryFieldCapacity(
                main_draw_size=4,
                qualification_draw_size=2,
                qualifier_spots=1,
                wild_card_slots=1,
            ),
            command_id="initial-field",
        )


def _root(server: ApiServer) -> str:
    return (
        f"{server.base_url}/admin/runs/run/branches/branch/"
        "tournaments/event/wild-cards"
    )


@pytest.mark.pr_critical
def test_canonical_wc_preview_commit_and_exact_retry_over_http(tmp_path) -> None:
    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'canonical-wc-http.sqlite'}"
    ) as server:
        _install(server)
        root = _root(server)

        status, before = _request("GET", root)
        assert status == 200
        assert before["authority"] is None
        assert before["definitive_assignments"] == []

        review = {
            "command_id": "http-wc-review-1",
            "original_wild_card_player_ids": ["A"],
            "reserve_wild_card_player_ids": ["PROSPECT"],
            "unavailable_player_ids": [],
            "operator_label": "Commissioner",
            "reason": "Explicit review because automatic WC eligibility is open.",
        }
        status, preview = _request("POST", root + "/preview", review)
        assert status == 200, preview
        assert preview["persisted"] is False
        assert preview["week"] == WEEK.model_dump(mode="json")
        assert preview["decision_slot_ordinal"] == 1
        assert preview["authority"]["schema_version"] == (
            "tournament_wild_card_authority.v3"
        )
        slot = preview["authority"]["slots"][0]
        assert slot["original_player_id"] == "A"
        assert slot["released_because_direct_acceptance"] is True
        assert slot["source"] == "reserve_wc"
        assert slot["active_player_id"] == "PROSPECT"
        assert preview["first_tour_entry_source_player_ids"] == ["PROSPECT"]

        command = {
            **review,
            "expected_week": preview["week"],
            "expected_revision_id": preview["expected_revision_id"],
            "expected_decision_slot_ordinal": preview["decision_slot_ordinal"],
            "expected_proposal_fingerprint": preview["proposal_fingerprint"],
        }
        status, committed = _request("POST", root + "/commit", command)
        assert status == 201, committed
        assert committed["adoption"] == "committed"
        assert committed["authority"] == preview["authority"]
        assert len(committed["assignment_results"]) == 1
        item = committed["assignment_results"][0]
        assert item["assignment"]["player_id"] == "PROSPECT"
        assert item["assignment_is_first_tour_entry_source"] is True

        status, retry = _request("POST", root + "/commit", command)
        assert status == 201, retry
        assert retry["adoption"] == "exact_retry"
        assert retry["authority"] == committed["authority"]

        status, after = _request("GET", root)
        assert status == 200
        assert after["authority"] == committed["authority"]
        assert [item["player_id"] for item in after["definitive_assignments"]] == [
            "PROSPECT"
        ]
