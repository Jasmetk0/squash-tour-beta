"""Native sporting-week substep, not the complete Official Week Transition.

Annual attribute exposure is 1/W; recovery and inactivity remain weekly units.
Health healing, lifecycle/intake, rankings and publication are separate unimplemented
transition steps. This bounded exhibition timeline must not unlock those consumers.
"""

from fractions import Fraction
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.players.attribute_catalog import ATTRIBUTE_TO_GROUP
from beta_engine.domain.players.sporting import PlayerDevelopmentPolicy, _roll
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash


class CalendarAnnualDevelopmentPolicy(FrozenInput):
    policy_id: Literal["calendar-annual-development.provisional.v1"] = (
        "calendar-annual-development.provisional.v1"
    )
    # Existing provisional 18 bp/week at reference W61, expressed annually.
    annual_change_basis_points: int = Field(default=1098, ge=0, le=10000)
    annual_form_influence_basis_points: int = Field(default=244, ge=0)
    weekly_state_policy: PlayerDevelopmentPolicy = PlayerDevelopmentPolicy()
    provenance: str = "Provisional W-aware adapter; annual attribute exposure only; weekly recovery unchanged; not realism acceptance"


class CalendarSportingWeekAdvance(FrozenInput):
    schema_version: Literal["calendar_sporting_week_advance.v1"] = (
        "calendar_sporting_week_advance.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    command_id: str = Field(min_length=1, max_length=128)
    source_saved_head: str = Field(min_length=1)
    source_checkpoint_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    completed_week: RunWeekPosition
    target_week: RunWeekPosition
    seed: int
    operator_label: str = Field(min_length=1, max_length=160)
    audit_reason: str = Field(min_length=1, max_length=1000)
    request_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    policy: CalendarAnnualDevelopmentPolicy = CalendarAnnualDevelopmentPolicy()
    played_counts: tuple[tuple[str, int], ...]
    developed_players_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    recovered_players_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    scope: Literal["sporting_only_exhibition_timeline"] = (
        "sporting_only_exhibition_timeline"
    )

    @model_validator(mode="after")
    def validate_advance(self):
        if (
            self.completed_week.calendar != self.target_week.calendar
            or self.target_week.ordinal != self.completed_week.ordinal + 1
            or self.target_week.season_index != self.completed_week.season_index
        ):
            raise ValueError(
                "Sporting advance requires consecutive weeks within one season; Season Transition is unsupported"
            )
        if self.policy != CalendarAnnualDevelopmentPolicy():
            raise ValueError("Unknown native annual development calibration")
        if tuple(p for p, _ in self.played_counts) != tuple(
            sorted({p for p, _ in self.played_counts})
        ) or any(type(n) is not int or n < 0 for _, n in self.played_counts):
            raise ValueError(
                "Sporting advance requires sorted unique nonnegative played counts"
            )
        command = {
            "command_id": self.command_id,
            "expected_saved_head": self.source_saved_head,
            "expected_checkpoint_fingerprint": self.source_checkpoint_fingerprint,
            "seed": self.seed,
            "operator_label": self.operator_label,
            "audit_reason": self.audit_reason,
        }
        if self.request_fingerprint != canonical_hash(
            {"run_id": self.run_id, "branch_id": self.branch_id, "command": command}
        ):
            raise ValueError("Sporting advance command fingerprint mismatch")
        return self

    @property
    def fingerprint(self):
        return canonical_hash(self.model_dump(mode="json"))


def records_fingerprint(players):
    return canonical_hash([p.model_dump(mode="json") for p in players])


def age_in_run_years(profile, week):
    position = week.calendar_position
    width = week.calendar.weeks_per_year
    return Fraction(
        (position.calendar_year - profile.birth_year) * width
        + position.year_week
        - profile.birth_year_week,
        width,
    )


def played_counts(checkpoint, knockout):
    counts = {p.player_id: 0 for p in checkpoint.players}
    if checkpoint.week.ordinal == 0:
        for match in knockout.matches:
            for pid in (match.result.player_a_id, match.result.player_b_id):
                counts[pid] += 1
    for match in checkpoint.played_continuations:
        if match.week.ordinal == checkpoint.week.ordinal:
            for pid in (match.result.player_a_id, match.result.player_b_id):
                counts[pid] += 1
    return tuple(sorted(counts.items()))


def develop_and_recover(checkpoint, world, *, completed_week, seed, policy, counts):
    """Two pure stages consuming only end-of-completed-week facts."""
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
        age = age_in_run_years(
            profiles[player.player_id], completed_week
        ) - old.timing_shift(player.development_timing)
        # A yearly rate divided by W, without float rounding or a universal 61-week clock.
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
            roll = _roll(
                policy.policy_id,
                source,
                seed,
                player.player_id,
                name,
                modulus=10000 * width,
            )
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
                        - (
                            old.inactive_sharpness_decay
                            if count_by_id[player.player_id] == 0
                            else 0
                        ),
                    ),
                    "long_term_fatigue": max(
                        0, player.long_term_fatigue - old.fatigue_recovery
                    ),
                }
            )
        )
    return tuple(developed), tuple(recovered)


def append_sporting_week(checkpoint, world, knockout, event):
    from beta_engine.domain.players.calendar_sporting_checkpoint import (
        CalendarSportingCheckpoint,
    )

    previous = (
        checkpoint.week.calendar
        if checkpoint.week_events or not checkpoint.continuations
        else checkpoint.continuations[-1].week.calendar
    )
    clock = event.completed_week.calendar
    if (
        (event.run_id, event.branch_id) != (checkpoint.run_id, checkpoint.branch_id)
        or event.source_checkpoint_fingerprint != checkpoint.fingerprint
        or event.completed_week.ordinal != checkpoint.week.ordinal
        or (
            previous.weeks_per_year,
            previous.season_start_year_week,
            previous.start_year,
        )
        != (clock.weeks_per_year, clock.season_start_year_week, clock.start_year)
        or previous.season_count > clock.season_count
        or event.command_id
        in {
            knockout.command_id,
            *(e.command_id for e in checkpoint.played_continuations),
            *(e.command_id for e in checkpoint.weekly_advances),
            *(e.command_id for e in checkpoint.tournaments),
        }
        or event.played_counts != played_counts(checkpoint, knockout)
    ):
        raise ValueError(
            "Sporting week predecessor, history, identity, calendar or played counts mismatch"
        )
    developed, recovered = develop_and_recover(
        checkpoint,
        world,
        completed_week=event.completed_week,
        seed=event.seed,
        policy=event.policy,
        counts=event.played_counts,
    )
    if (records_fingerprint(developed), records_fingerprint(recovered)) != (
        event.developed_players_fingerprint,
        event.recovered_players_fingerprint,
    ):
        raise ValueError("Sporting week does not rebuild from actual terminal players")
    return CalendarSportingCheckpoint.model_validate_json(
        checkpoint.model_copy(
            update={
                "schema_version": (
                    "calendar_sporting_checkpoint.v5"
                    if checkpoint.schema_version == "calendar_sporting_checkpoint.v5"
                    else "calendar_sporting_checkpoint.v4"
                    if checkpoint.schema_version == "calendar_sporting_checkpoint.v4"
                    else "calendar_sporting_checkpoint.v3"
                ),
                "phase": "sporting_week_active",
                "week": event.target_week,
                "players": recovered,
                "annual_development_applied": True,
                "week_events": checkpoint.week_events + (event,),
            }
        ).model_dump_json()
    )
