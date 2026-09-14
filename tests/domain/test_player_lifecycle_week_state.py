import pytest
from beta_engine.domain.players.lifecycle import (
    PlayerLifecycleIdentity,
    PlayerLifecycleWeekState,
    advance_lifecycle,
)
from beta_engine.domain.rankings.official import RankingWeek


def state(*, age=30, birthday=8):
    week = RankingWeek(season_index=0, week=7)
    return PlayerLifecycleWeekState(
        run_id="run",
        branch_id="branch",
        week=week,
        source_initial_world_fingerprint="world",
        players=(
            PlayerLifecycleIdentity(
                player_id="p1",
                birth_year=2000 - age,
                birth_year_week=birthday,
                tie_break_token="token",
                tie_break_provenance="owned identity",
                tour_entry_week=RankingWeek(season_index=0, week=1),
                age=age,
                status="active",
                origin="initial_world:world",
            ),
        ),
    )


def test_non_birthday_carries_identity_into_new_historical_snapshot():
    before = state(birthday=9)
    after = advance_lifecycle(before, RankingWeek(season_index=0, week=8))
    assert after.players == before.players
    assert after.fingerprint != before.fingerprint
    assert after.predecessor_fingerprint == before.fingerprint


def test_birthday_and_retirement_are_effective_in_opened_week():
    after = advance_lifecycle(state(age=45), RankingWeek(season_index=0, week=8))
    player = after.players[0]
    assert (player.age, player.status, player.retirement_effective_week) == (
        46,
        "retired",
        RankingWeek(season_index=0, week=8),
    )
    assert after.ranking_roster()[0].retired is True


def test_season_transition_fails_closed():
    before = state().model_copy(update={"week": RankingWeek(season_index=0, week=61)})
    with pytest.raises(ValueError, match="ordinary same-season"):
        advance_lifecycle(before, RankingWeek(season_index=1, week=1))
