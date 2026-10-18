"""Annual units, causal ordering, fractional age and untouched identities."""

from fractions import Fraction
from types import SimpleNamespace

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.players.attribute_catalog import CANONICAL_PLAYER_ATTRIBUTES
from beta_engine.domain.players.calendar_sporting_checkpoint import (
    CalendarSportingCheckpoint,
)
from beta_engine.domain.players.calendar_sporting_week import (
    CalendarAnnualDevelopmentPolicy,
    age_in_run_years,
    develop_and_recover,
    records_fingerprint,
)
from beta_engine.domain.players.sporting import PlayerSportingRecord

pytestmark = pytest.mark.pr_critical


def population(width=52):
    clock = RunCalendar(width, width, 2030, 2)
    week = RunWeekPosition(calendar=clock, season_index=0, week=1)
    players = tuple(
        PlayerSportingRecord(
            player_id=str(i),
            attributes=tuple((a, 100) for a in CANONICAL_PLAYER_ATTRIBUTES),
            potential_ovr=190,
            potential_identity="fixed",
            potential_provenance="original",
            development_timing="Standard",
            current_form=120,
            long_term_form_norm=80,
            match_sharpness=10,
            long_term_fatigue=20,
        )
        for i in range(4)
    )
    cp = CalendarSportingCheckpoint(
        run_id="r",
        branch_id="b",
        week=week,
        source_saved_head="h",
        source_initial_world_fingerprint="a" * 64,
        source_knockout_fingerprint="b" * 64,
        players=players,
    )
    profiles = tuple(
        SimpleNamespace(player_id=p.player_id, birth_year=2010, birth_year_week=width)
        for p in players
    )
    return cp, SimpleNamespace(players=profiles)


def test_annual_exposure_is_inverse_W_and_weekly_recovery_is_not_rescaled(monkeypatch):
    from beta_engine.domain.players import calendar_sporting_week as kernel

    denominators = []
    monkeypatch.setattr(
        kernel, "_roll", lambda *args, modulus: denominators.append(modulus) or 0
    )
    policy = CalendarAnnualDevelopmentPolicy()
    for width in (1, 52, 61, 80):
        cp, world = population(width)
        counts = tuple((p.player_id, 0) for p in cp.players)
        developed, recovered = develop_and_recover(
            cp, world, completed_week=cp.week, seed=3, policy=policy, counts=counts
        )
        assert denominators[-1] == 10000 * width
        # Exact annual expected opportunities, with identical full-year form conditions.
        numerator = (
            policy.annual_change_basis_points
            + 40 * policy.annual_form_influence_basis_points
        )
        assert Fraction(numerator, denominators[-1]) * width == Fraction(
            numerator, 10000
        )
        assert all(
            v
            == 100
            + numerator // denominators[-1]
            + (1 if numerator % denominators[-1] else 0)
            for _, v in developed[0].attributes
        )
        assert recovered[0].current_form == 115 and recovered[0].match_sharpness == 8
        assert recovered[0].long_term_fatigue == 12
        assert developed[0].current_form == 120  # growth stage precedes regression
        assert recovered[0].potential_identity == cp.players[0].potential_identity
        assert recovered[0].potential_provenance == cp.players[0].potential_provenance
        assert recovered[0].long_term_form_norm == 80


def test_development_reads_terminal_form_before_regression_and_is_seed_reproducible(
    monkeypatch,
):
    from beta_engine.domain.players import calendar_sporting_week as kernel

    cp, world = population()
    policy = CalendarAnnualDevelopmentPolicy()
    # Between pre-regression and post-regression form thresholds.
    monkeypatch.setattr(kernel, "_roll", lambda *args, modulus: 10200)
    counts = tuple((p.player_id, 1) for p in cp.players)
    first = develop_and_recover(
        cp, world, completed_week=cp.week, seed=4, policy=policy, counts=counts
    )
    assert all(v == 101 for _, v in first[0][0].attributes)
    assert first[1][0].match_sharpness == 10
    assert first == develop_and_recover(
        cp, world, completed_week=cp.week, seed=4, policy=policy, counts=counts
    )
    assert records_fingerprint(first[0]) != records_fingerprint(first[1])
    future = RunWeekPosition(calendar=cp.week.calendar, season_index=0, week=2)
    with pytest.raises(ValueError):
        develop_and_recover(
            cp, world, completed_week=future, seed=4, policy=policy, counts=counts
        )
    with pytest.raises(ValueError):
        develop_and_recover(
            cp, world, completed_week=cp.week, seed=4, policy=policy, counts=counts[:-1]
        )


def test_age_uses_actual_birth_week_and_fraction_of_Run_year():
    for width in (52, 61, 80):
        cp, world = population(width)
        assert age_in_run_years(world.players[0], cp.week) == 20
        target = RunWeekPosition(calendar=cp.week.calendar, season_index=0, week=2)
        assert age_in_run_years(world.players[0], target) == 20 + Fraction(1, width)


def test_old_checkpoint_cannot_be_promoted_by_empty_weekly_history():
    cp, _ = population()
    for fields in (
        {"week_events": []},
        {
            "schema_version": "calendar_sporting_checkpoint.v3",
            "phase": "sporting_week_active",
            "annual_development_applied": True,
            "week_events": [],
        },
    ):
        with pytest.raises(ValueError):
            CalendarSportingCheckpoint.model_validate(
                {**cp.model_dump(mode="json"), **fields}
            )


@pytest.mark.parametrize("width", [1, 52, 80])
def test_sporting_preparation_stops_before_Season_Transition(width):
    from beta_engine.application.calendar_sporting_week_service import (
        CalendarSportingWeekCommand,
        CalendarSportingWeekService,
    )

    cp, _ = population(width)
    terminal = cp.model_copy(
        update={
            "week": RunWeekPosition(
                calendar=cp.week.calendar, season_index=0, week=width
            )
        }
    )
    cmd = CalendarSportingWeekCommand(
        command_id="boundary",
        expected_saved_head="h",
        expected_checkpoint_fingerprint=terminal.fingerprint,
        seed=1,
        operator_label="Admin",
        audit_reason="Must not invent Season Transition",
    )
    with pytest.raises(ValueError, match="Season Transition"):
        CalendarSportingWeekService(None)._preview(
            terminal.week.calendar,
            SimpleNamespace(saved_head_revision_id="h"),
            None,
            terminal,
            terminal,
            None,
            cmd,
        )
