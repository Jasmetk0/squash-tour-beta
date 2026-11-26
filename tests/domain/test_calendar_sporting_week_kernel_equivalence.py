"""The faster development kernel equals the original per-attribute kernel.

The reference below is the previous implementation verbatim. Both run on the
same varied populations (ages around growth end, physical/other decline and
retirement, every timing, above/below potential, form above/below norm,
played/idle, W from 1 to 80, official and exhibition) and must return the
identical developed and recovered records, hence identical fingerprints.
"""

import random
from types import SimpleNamespace

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.players.attribute_catalog import (
    ATTRIBUTE_TO_GROUP,
    CANONICAL_PLAYER_ATTRIBUTES,
)
from beta_engine.domain.players.calendar_sporting_week import (
    CalendarAnnualDevelopmentPolicy,
    age_in_run_years,
    develop_and_recover,
    records_fingerprint,
)
from beta_engine.domain.players.sporting import PlayerSportingRecord, _roll

pytestmark = pytest.mark.pr_critical


def reference_develop_and_recover(checkpoint, world, *, completed_week, seed, policy, counts, official=False):
    if completed_week.ordinal != checkpoint.week.ordinal:
        raise ValueError("Development cannot use a future or skipped week")
    profiles = {p.player_id: p for p in world.players}
    if set(profiles) != {p.player_id for p in checkpoint.players} or tuple(
        p for p, _ in counts
    ) != tuple(p.player_id for p in checkpoint.players):
        raise ValueError("Sporting development population/counts mismatch")
    old = policy.weekly_state_policy
    width = completed_week.calendar.weeks_per_year
    source = checkpoint.fingerprint
    developed, recovered = [], []
    count_by_id = dict(counts)
    for player in checkpoint.players:
        if official and age_in_run_years(profiles[player.player_id], completed_week) >= world.lifecycle_policy.automatic_retirement_age:
            developed.append(player)
            recovered.append(player)
            continue
        age = age_in_run_years(
            profiles[player.player_id], completed_week
        ) - old.timing_shift(player.development_timing)
        threshold = max(
            0,
            policy.annual_change_basis_points
            + (player.current_form - player.long_term_form_norm)
            * policy.annual_form_influence_basis_points,
        )
        attrs = []
        below_potential = player.ovr < player.potential_ovr
        for name, value in player.attributes:
            decline = (
                old.physical_decline_age
                if ATTRIBUTE_TO_GROUP[name] in {"Physical", "Move"}
                else old.other_decline_age
            )
            direction = (
                1
                if age <= old.growth_end_age and below_potential
                else (-1 if age >= decline else 0)
            )
            roll = _roll(policy.policy_id, source, seed, player.player_id, name, modulus=10000 * width)
            whole, remainder = divmod(threshold, 10000 * width)
            delta = direction * (whole + (1 if roll < remainder else 0))
            attrs.append((name, min(200, max(0, value + delta))))
        developed_player = player.model_copy(update={"attributes": tuple(attrs)})
        developed.append(developed_player)
        difference = player.long_term_form_norm - player.current_form
        regression = (abs(difference) // old.form_regression_divisor) * (
            1 if difference > 0 else -1
        )
        if not regression and difference:
            regression = 1 if difference > 0 else -1
        recovered.append(
            developed_player.model_copy(
                update={
                    "current_form": player.current_form + regression,
                    "match_sharpness": max(
                        0,
                        player.match_sharpness
                        - (old.inactive_sharpness_decay if count_by_id[player.player_id] == 0 else 0),
                    ),
                    "long_term_fatigue": max(0, player.long_term_fatigue - old.fatigue_recovery),
                }
            )
        )
    return tuple(developed), tuple(recovered)


def _population(width, count, rng):
    clock = RunCalendar(width, width, 2030, 2)
    week = RunWeekPosition(calendar=clock, season_index=0, week=1)
    players, profiles = [], []
    for index in range(count):
        pid = f"P-{index:04d}"
        players.append(PlayerSportingRecord(
            player_id=pid,
            # Edge values 0/200 exercise the clamp in both directions.
            attributes=tuple((a, rng.choice((0, 1, 199, 200, rng.randint(0, 200))))
                             for a in CANONICAL_PLAYER_ATTRIBUTES),
            potential_ovr=rng.randint(0, 200),
            potential_identity="fixed",
            potential_provenance="original",
            development_timing=rng.choice(("Early Bloomer", "Standard", "Late Bloomer")),
            current_form=rng.randint(0, 200),
            long_term_form_norm=rng.randint(0, 200),
            match_sharpness=rng.randint(0, 100),
            long_term_fatigue=rng.randint(0, 100),
        ))
        # Ages from 14 to 45 at week granularity, around every boundary.
        profiles.append(SimpleNamespace(
            player_id=pid, birth_year=2030 - rng.randint(14, 45),
            birth_year_week=rng.randint(1, width),
        ))
    checkpoint = SimpleNamespace(
        week=week, players=tuple(players),
        fingerprint=f"{rng.getrandbits(256):064x}",
    )
    world = SimpleNamespace(
        players=tuple(profiles),
        lifecycle_policy=SimpleNamespace(automatic_retirement_age=rng.choice((36, 40, 99))),
    )
    return checkpoint, world


@pytest.mark.parametrize("width", (1, 2, 8, 52, 61, 80))
def test_kernel_equals_the_original_per_attribute_kernel(width):
    rng = random.Random(width * 7919)
    for case in range(6):
        checkpoint, world = _population(width, 60, rng)
        counts = tuple((p.player_id, rng.choice((0, 0, 1, 3))) for p in checkpoint.players)
        policy = CalendarAnnualDevelopmentPolicy(
            annual_change_basis_points=rng.choice((0, 1098, 5000, 10000)),
            annual_form_influence_basis_points=rng.choice((0, 244, 1000)),
        )
        for official in (False, True):
            kwargs = dict(completed_week=checkpoint.week, seed=rng.randint(-5, 10**12),
                          policy=policy, counts=counts, official=official)
            actual = develop_and_recover(checkpoint, world, **kwargs)
            expected = reference_develop_and_recover(checkpoint, world, **kwargs)
            assert actual == expected, (width, case, official)
            assert tuple(map(records_fingerprint, actual)) == tuple(map(records_fingerprint, expected))


def test_kernel_hashes_the_identical_roll_texts():
    # Every roll that can change a value uses the same hashed text as before.
    seen_new, seen_old = [], []
    checkpoint, world = _population(52, 40, random.Random(3))
    counts = tuple((p.player_id, 0) for p in checkpoint.players)
    from beta_engine.domain.players import calendar_sporting_week as kernel

    original = kernel._roll

    def record(store):
        def roll(*parts, modulus):
            store.append(("|".join(str(p) for p in parts), modulus))
            return original(*parts, modulus=modulus)
        return roll

    kwargs = dict(completed_week=checkpoint.week, seed=17, policy=CalendarAnnualDevelopmentPolicy(), counts=counts)
    try:
        kernel._roll = record(seen_new)
        develop_and_recover(checkpoint, world, **kwargs)
    finally:
        kernel._roll = original
    module = globals()
    try:
        module["_roll"] = record(seen_old)
        reference_develop_and_recover(checkpoint, world, **kwargs)
    finally:
        module["_roll"] = original
    assert seen_new and set(seen_new) <= set(seen_old)
