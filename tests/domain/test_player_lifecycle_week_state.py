import pytest
from pydantic import ValidationError

from beta_engine.domain.calendar.season_weeks import (
    age_at_calendar_position,
    birth_year_for_age_at_calendar_position,
    season_week_to_calendar_position,
    season_week_to_year_week,
    year_week_to_season_week,
)
from beta_engine.domain.players.lifecycle import (
    PlayerLifecycleIdentity,
    PlayerLifecyclePolicy,
    PlayerLifecycleWeekState,
    advance_lifecycle,
)
from beta_engine.domain.rankings.official import RankingWeek


def state(
    *, age=30, birthday=38, season_week=1, status="active", retirement=None, policy=None
):
    position = season_week_to_calendar_position(2000, season_week)
    birth_year = birth_year_for_age_at_calendar_position(
        age=age,
        birth_year_week=birthday,
        calendar_year=position.calendar_year,
        year_week=position.year_week,
    )
    return PlayerLifecycleWeekState(
        run_id="run",
        branch_id="branch",
        week=RankingWeek(season_index=0, week=season_week),
        source_initial_world_fingerprint="world",
        **({"policy": policy} if policy is not None else {}),
        players=(
            PlayerLifecycleIdentity(
                player_id="p1",
                birth_year=birth_year,
                birth_year_week=birthday,
                tie_break_token="token",
                tie_break_provenance="owned identity",
                tour_entry_week=RankingWeek(season_index=0, week=1),
                age=age,
                status=status,
                retirement_effective_week=retirement,
                origin="initial_world:world",
            ),
        ),
    )


def test_fax_year_week_mapping_drives_birthday_not_season_week():
    assert season_week_to_year_week(1) == 37
    birthday = advance_lifecycle(
        state(birthday=38), RankingWeek(season_index=0, week=2)
    )
    assert birthday.players[0].age == 31
    sw50 = advance_lifecycle(
        state(birthday=8, season_week=49), RankingWeek(season_index=0, week=50)
    )
    assert sw50.players[0].age == 30


def test_year_week_50_occurs_at_mapped_season_week_only():
    target = year_week_to_season_week(50)
    assert target != 50
    after = advance_lifecycle(
        state(birthday=50, season_week=target - 1),
        RankingWeek(season_index=0, week=target),
    )
    assert after.players[0].age == 31


def test_birthday_and_retirement_are_effective_in_opened_week():
    after = advance_lifecycle(state(age=45), RankingWeek(season_index=0, week=2))
    player = after.players[0]
    assert (player.age, player.status, player.retirement_effective_week) == (
        46,
        "retired",
        RankingWeek(season_index=0, week=2),
    )
    assert after.ranking_roster()[0].retired is True


def test_stored_policy_controls_custom_retirement_age_and_fingerprint():
    custom = PlayerLifecyclePolicy(
        policy_id="custom-50",
        automatic_retirement_age=50,
        provenance="Explicit custom test policy",
    )
    snapshot = state(age=46, policy=custom)
    validated = PlayerLifecycleWeekState.model_validate(snapshot.model_dump())
    assert validated.players[0].status == "active"
    assert (
        validated.fingerprint
        == PlayerLifecycleWeekState.model_validate(validated.model_dump()).fingerprint
    )
    assert (
        validated.fingerprint
        != state(
            age=46, policy=custom.model_copy(update={"automatic_retirement_age": 51})
        ).fingerprint
    )


def test_retired_player_keeps_aging_and_original_retirement_week():
    retirement = RankingWeek(season_index=0, week=1)
    before = state(
        age=46, birthday=8, season_week=32, status="retired", retirement=retirement
    )
    after = advance_lifecycle(before, RankingWeek(season_index=0, week=33))
    assert (
        after.players[0].age,
        after.players[0].status,
        after.players[0].retirement_effective_week,
    ) == (47, "retired", retirement)


def test_age_helper_and_lifecycle_integrity():
    assert (
        age_at_calendar_position(
            birth_year=1975, birth_year_week=20, calendar_year=2000, year_week=37
        )
        == 25
    )
    assert (
        age_at_calendar_position(
            birth_year=1975, birth_year_week=50, calendar_year=2000, year_week=37
        )
        == 24
    )
    valid = state(age=30)
    with pytest.raises(ValidationError, match="canonical birth identity"):
        PlayerLifecycleWeekState.model_validate(
            valid.model_dump()
            | {"players": (valid.players[0].model_dump() | {"age": 29},)}
        )


def test_season_transition_advances_contiguous_lifecycle():
    before = state(age=45, birthday=37, season_week=61)
    after = advance_lifecycle(before, RankingWeek(season_index=1, week=1))
    player = after.players[0]
    assert after.week == RankingWeek(season_index=1, week=1)
    assert after.predecessor_fingerprint == before.fingerprint
    assert (player.age, player.status, player.retirement_effective_week) == (
        46,
        "retired",
        RankingWeek(season_index=1, week=1),
    )


def test_lifecycle_nonconsecutive_transition_fails_closed():
    before = state(season_week=60)
    with pytest.raises(ValueError, match="only consecutive"):
        advance_lifecycle(before, RankingWeek(season_index=1, week=1))
