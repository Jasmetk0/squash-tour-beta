"""Native authority versions retain legacy bytes and never reinterpret W time."""

import json

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.rankings.calendar_official import (
    CalendarRankingPlayer,
    CalendarRankingResult,
    CalendarRankingWeek,
    calculate_calendar_official_ranking,
)
from beta_engine.domain.rankings.official import OfficialRankingPolicy
from beta_engine.domain.tournaments.application_submission_authority import (
    TournamentApplicationSubmissionAuthority,
    TournamentApplicationSubmissionBatchAuthority,
)
from beta_engine.domain.tournaments.calendar_tour import CalendarTourEdition

pytestmark = pytest.mark.pr_critical


@pytest.mark.parametrize("width", [52, 61, 80])
def test_native_submission_trigger_and_batch_use_run_year(width):
    clock = RunCalendar(width, width, 2030, 3)
    week = RunWeekPosition(calendar=clock, season_index=1, week=width)
    submission = TournamentApplicationSubmissionAuthority(
        schema_version="tournament_application_submission_authority.v2",
        application_id="edition:player",
        run_id="r",
        branch_id="b",
        event_id="edition",
        player_id="player",
        entry_window="main",
        submission_week=week,
        decision_slot_ordinal=1,
        nr_tie_break_token="stable",
        validation_authority_id="review",
        validation_authority_fingerprint="a" * 64,
        provenance="Manual validated",
    )
    restored = TournamentApplicationSubmissionAuthority.model_validate_json(
        submission.model_dump_json()
    )
    assert restored == submission and restored.decision_position == (2 * width - 1, 1)
    trigger = restored.to_tour_entry_trigger()
    assert trigger.schema_version == "player_tour_entry_trigger.v2"
    assert trigger.decision_position == submission.decision_position
    batch = TournamentApplicationSubmissionBatchAuthority.from_submissions(
        (submission,)
    )
    assert batch == TournamentApplicationSubmissionBatchAuthority.model_validate_json(
        batch.model_dump_json()
    )
    forged = json.loads(submission.model_dump_json())
    forged["schema_version"] = "tournament_application_submission_authority.v1"
    with pytest.raises(ValueError):
        TournamentApplicationSubmissionAuthority.model_validate_json(json.dumps(forged))


@pytest.mark.parametrize("width", [52, 61, 80])
def test_exact_annual_result_expiry_and_no_future_publication(width):
    clock = RunCalendar(width, width, 2030, 3)
    result = CalendarRankingResult(
        edition_id="e",
        player_id="p",
        source_fingerprint="frozen-policy-100",
        completed_week=CalendarRankingWeek(season_index=0, week=1),
        first_publication_week=CalendarRankingWeek(season_index=0, week=2),
        main_points=100,
    )
    player = CalendarRankingPlayer(
        player_id="p",
        tie_break_token="stable",
        tour_entry_week=CalendarRankingWeek(season_index=0, week=1),
    )

    def calculate(week):
        return calculate_calendar_official_ranking(
            run_id="r",
            branch_id="b",
            run_calendar=clock,
            week=week,
            policy=OfficialRankingPolicy(policy_id="new-best1", best_n=1),
            players=(player,),
            results=(result,),
        )

    assert calculate(CalendarRankingWeek(season_index=1, week=1)).rows[0].points == 100
    assert calculate(CalendarRankingWeek(season_index=1, week=2)).rows[0].points == 0
    with pytest.raises(ValueError, match="future leakage"):
        calculate(CalendarRankingWeek(season_index=0, week=1))
    assert (
        result.main_points == 100 and result.source_fingerprint == "frozen-policy-100"
    )


def test_edition_capacity_remains_general_and_announcement_needs_full_week():
    clock = RunCalendar(80, 80, 2030, 3)
    play = RunWeekPosition(calendar=clock, season_index=0, week=70)
    announcement = RunWeekPosition(calendar=clock, season_index=0, week=69)
    edition = CalendarTourEdition(
        edition_id="general-13",
        name="Thirteen players",
        week=play,
        announcement_week=announcement,
        start_slot=1,
        main_entrant_count=13,
        ranked=False,
        point_table={},
        validity_weeks=80,
    )
    assert edition.capacity.main_draw_size == 16 and edition.capacity.bye_slots == 3
    with pytest.raises(ValueError):
        CalendarTourEdition.model_validate_json(
            edition.model_copy(update={"announcement_week": play}).model_dump_json()
        )


def approved_authority():
    from beta_engine.domain.tournaments.calendar_tour import (
        CalendarEditionAuthority,
        build_draw,
    )
    from beta_engine.domain.tournaments.entry_field import TournamentEntryFieldResolver
    from beta_engine.domain.tournaments.ranking_snapshot_authority import (
        TournamentRankingSnapshotAuthority,
    )

    clock = RunCalendar(52, 35, 2030, 3)
    week = RunWeekPosition(calendar=clock, season_index=0, week=4)
    config = CalendarTourEdition(
        edition_id="configured",
        name="Configured",
        week=week,
        announcement_week=RunWeekPosition(calendar=clock, season_index=0, week=3),
        start_slot=1,
        main_entrant_count=8,
        point_table={
            "champion": 100,
            "finalist": 60,
            "semifinal": 30,
            "quarterfinal": 15,
        },
        validity_weeks=52,
    )
    submissions = tuple(
        TournamentApplicationSubmissionAuthority(
            schema_version="tournament_application_submission_authority.v2",
            application_id=f"configured:p{i}",
            run_id="r",
            branch_id="b",
            event_id="configured",
            player_id=f"p{i}",
            entry_window="main",
            submission_week=week,
            decision_slot_ordinal=1,
            nr_tie_break_token=f"token{i}",
            validation_authority_id="review",
            validation_authority_fingerprint="a" * 64,
            provenance="Reviewed",
        )
        for i in range(8)
    )
    snapshot = calculate_calendar_official_ranking(
        run_id="r",
        branch_id="b",
        run_calendar=clock,
        week=CalendarRankingWeek(season_index=0, week=4),
        policy=OfficialRankingPolicy(policy_id="initial", best_n=15),
        players=(),
        results=(),
    )
    ranking = TournamentRankingSnapshotAuthority(
        schema_version="tournament_ranking_snapshot_authority.v2",
        run_id="r",
        branch_id="b",
        event_id="configured",
        ranking_week=week,
        ranking_snapshot=snapshot,
        adopted_by_command_id="approve",
    )
    source = CalendarEditionAuthority(
        edition=config,
        created_command_id="create",
        created_saved_head="saved",
        submissions=submissions,
        ranking_authority=ranking,
    )
    field = TournamentEntryFieldResolver.build_initial(
        authority=ranking,
        applications=tuple(s.to_entry_field_application() for s in submissions),
        capacity=config.capacity,
    )
    source = source.model_copy(update={"field": field})
    source = source.model_copy(
        update={
            "draw": build_draw(source, "draw", 71),
            "draw_seed": 71,
            "draw_command_id": "draw",
        }
    )
    return CalendarEditionAuthority.model_validate_json(
        source.model_dump_json()
    ), snapshot


def test_native_field_and_draw_rebuild_from_production_entries_and_reject_foreign_scope():
    from beta_engine.domain.tournaments.calendar_tour import (
        CalendarEditionAuthority,
        CalendarTourPolicy,
        CalendarTourState,
    )

    authority, snapshot = approved_authority()
    assert len(authority.field.direct_main_player_ids) == 8
    assert {s.player_id for s in authority.draw.main.slots} == {
        f"p{i}" for i in range(8)
    }
    raw = authority.model_dump(mode="json")
    raw["ranking_authority"]["event_id"] = "foreign"
    with pytest.raises(ValueError):
        CalendarEditionAuthority.model_validate_json(json.dumps(raw))
    state = CalendarTourState(
        run_id="r",
        branch_id="b",
        week=authority.edition.week,
        checkpoint_fingerprint="a" * 64,
        lifecycle_fingerprint="c" * 64,
        policies=(
            CalendarTourPolicy(
                effective_week=authority.edition.week, ranking=snapshot.policy
            ),
        ),
        rankings=(snapshot,),
        editions=(authority,),
    )
    for damage in ("foreign_branch", "foreign_policy_clock", "nonempty_initial"):
        raw = state.model_dump(mode="json")
        if damage == "foreign_branch":
            raw["branch_id"] = "foreign"
        elif damage == "foreign_policy_clock":
            raw["policies"][0]["effective_week"]["calendar"]["start_year"] = 2040
        else:
            raw["rankings"][0]["previous_fingerprint"] = "b" * 64
        with pytest.raises(ValueError):
            CalendarTourState.model_validate_json(json.dumps(raw))


def test_edition_result_uses_one_frozen_source_hash_and_rejects_exhibition_or_changed_policy():
    from beta_engine.domain.players.calendar_followup_points import (
        CalendarFollowupEightPointPolicy,
        CalendarFollowupPreparedAward,
    )
    from beta_engine.domain.tournaments.calendar_tour import edition_results

    authority, _ = approved_authority()
    authority = authority.model_copy(
        update={"tournament_fingerprint": "f" * 64, "played_saved_head": "pre-play"}
    )

    class Played:
        schema_version = "calendar_followup_knockout.v5"
        edition_authority_fingerprint = authority.execution_fingerprint
        tournament_id = authority.edition.edition_id
        entrant_ids = tuple(s.player_id for s in authority.draw.main.slots)
        week = authority.edition.week
        prepared_policy = CalendarFollowupEightPointPolicy(
            category_label="configured",
            **authority.edition.point_table,
            validity_weeks=52,
        )
        prepared_awards = tuple(
            CalendarFollowupPreparedAward(
                player_id=f"p{i}",
                reached_stage="champion" if i == 0 else "quarterfinal",
                main_points=100 if i == 0 else 15,
                source_tournament_fingerprint="c" * 64,
                source_policy_fingerprint="d" * 64,
            )
            for i in range(8)
        )
        reads = 0

        @property
        def fingerprint(self):
            self.reads += 1
            return "f" * 64

    event = Played()
    results = edition_results(authority, event)
    assert event.reads == 1 and len(results) == 8
    assert all(
        r.first_publication_week.week == 5 and r.validity_weeks == 52 for r in results
    )
    event.schema_version = "calendar_followup_knockout.v4"
    with pytest.raises(ValueError, match="Exhibition"):
        edition_results(authority, event)
    event.schema_version = "calendar_followup_knockout.v5"
    event.prepared_policy = event.prepared_policy.model_copy(update={"champion": 999})
    with pytest.raises(ValueError, match="pre-existing Edition table"):
        edition_results(authority, event)
