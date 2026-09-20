import pytest

from beta_engine.domain.calendar.season_weeks import (
    age_at_calendar_position,
    season_week_to_calendar_position,
)
from beta_engine.domain.players.lifecycle import (
    PlayerLifecycleIdentity,
    PlayerLifecycleWeekState,
)
from beta_engine.domain.players.tour_entry import PlayerTourEntryTrigger
from beta_engine.domain.players.tour_entry_projection import (
    project_lifecycle_tour_entries,
)
from beta_engine.domain.rankings.official import RankingWeek


def _player(
    player_id="prospect",
    *,
    week=RankingWeek(season_index=0, week=20),
    tour_entry_week=None,
    retirement_effective_week=None,
):
    position = season_week_to_calendar_position(2000 + week.season_index, week.week)
    return PlayerLifecycleIdentity(
        player_id=player_id,
        birth_year=1985,
        birth_year_week=10,
        tie_break_token=f"token-{player_id}",
        tie_break_provenance="test",
        tour_entry_week=tour_entry_week,
        age=age_at_calendar_position(
            birth_year=1985,
            birth_year_week=10,
            calendar_year=position.calendar_year,
            year_week=position.year_week,
        ),
        status="retired" if retirement_effective_week is not None else "active",
        retirement_effective_week=retirement_effective_week,
        origin="run_prospect:weekly_15yo_cohort:prospect_profile_v1",
    )


def _state(week=RankingWeek(season_index=0, week=20), players=None):
    return PlayerLifecycleWeekState(
        run_id="run",
        branch_id="branch",
        week=week,
        players=tuple(players or (_player(week=week),)),
        source_initial_world_fingerprint="world",
        predecessor_fingerprint="a" * 64,
    )


def _trigger(
    *,
    player_id="prospect",
    week=RankingWeek(season_index=0, week=20),
    slot=3,
    branch_id="branch",
):
    return PlayerTourEntryTrigger(
        run_id="run",
        branch_id=branch_id,
        player_id=player_id,
        event_id="event",
        trigger_kind="valid_tournament_application",
        trigger_week=week,
        decision_slot_ordinal=slot,
        source_evidence_id="application",
        source_evidence_fingerprint="b" * 64,
        provenance="test",
    )


@pytest.mark.pr_critical
def test_current_week_projection_exposes_midweek_tour_entry_without_mutating_snapshot():
    stored = _state()
    projected = project_lifecycle_tour_entries(stored, (_trigger(),))

    assert stored.players[0].tour_entry_week is None
    assert projected.players[0].tour_entry_week == stored.week
    assert tuple(player.player_id for player in projected.ranking_roster()) == (
        "prospect",
    )
    assert projected.predecessor_fingerprint == stored.predecessor_fingerprint
    assert projected.fingerprint != stored.fingerprint


@pytest.mark.pr_critical
def test_historical_week_ignores_later_trigger_but_later_snapshot_folds_it():
    old = _state(week=RankingWeek(season_index=0, week=20))
    trigger = _trigger(week=RankingWeek(season_index=0, week=21))
    assert project_lifecycle_tour_entries(old, (trigger,)) == old

    later_week = RankingWeek(season_index=0, week=22)
    later = _state(week=later_week, players=(_player(week=later_week),))
    projected = project_lifecycle_tour_entries(later, (trigger,))
    assert projected.players[0].tour_entry_week == RankingWeek(
        season_index=0, week=21
    )


@pytest.mark.pr_critical
def test_projection_is_idempotent_when_snapshot_already_sealed_same_trigger():
    week = RankingWeek(season_index=0, week=20)
    stored = _state(
        week=week,
        players=(_player(week=week, tour_entry_week=week),),
    )
    projected = project_lifecycle_tour_entries(stored, (_trigger(week=week),))
    assert projected == stored
    assert projected.fingerprint == stored.fingerprint


@pytest.mark.pr_critical
def test_projection_rejects_conflicting_or_invalid_effective_history():
    week = RankingWeek(season_index=0, week=20)

    with pytest.raises(ValueError, match="at most one trigger"):
        project_lifecycle_tour_entries(
            _state(week=week),
            (_trigger(week=week), _trigger(week=week, slot=4)),
        )

    with pytest.raises(ValueError, match="scope differs"):
        project_lifecycle_tour_entries(
            _state(week=week),
            (_trigger(week=week, branch_id="other"),),
        )

    with pytest.raises(ValueError, match="absent from lifecycle"):
        project_lifecycle_tour_entries(
            _state(week=week),
            (_trigger(player_id="missing", week=week),),
        )

    already = _state(
        week=week,
        players=(
            _player(
                week=week,
                tour_entry_week=RankingWeek(season_index=0, week=19),
            ),
        ),
    )
    with pytest.raises(ValueError, match="conflicts"):
        project_lifecycle_tour_entries(already, (_trigger(week=week),))


@pytest.mark.pr_critical
def test_projection_rejects_pre_15_and_post_retirement_triggers():
    early_week = RankingWeek(season_index=0, week=5)
    later_week = RankingWeek(season_index=0, week=20)
    later_state = _state(week=later_week, players=(_player(week=later_week),))
    with pytest.raises(ValueError, match="15th birthday"):
        project_lifecycle_tour_entries(
            later_state,
            (_trigger(week=early_week),),
        )

    retired_week = RankingWeek(season_index=31, week=10)
    retired = _state(
        week=retired_week,
        players=(
            _player(
                week=retired_week,
                retirement_effective_week=retired_week,
            ),
        ),
    )
    with pytest.raises(ValueError, match="retirement"):
        project_lifecycle_tour_entries(
            retired,
            (_trigger(week=retired_week),),
        )
