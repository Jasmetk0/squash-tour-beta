"""Exact Official Ranking candidate from authenticated native lifecycle and Entry.

This read-only bridge cannot publish, persist or activate a Tour transition.
All incoming sources must have been authenticated by the future Signed replay
coordinator before use: particularly the real Tour results and previous ranking.
"""
from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.players.calendar_native_birth_replay import (
    verify_calendar_native_birth_history,
)
from beta_engine.domain.rankings.calendar_official import (
    CalendarRankingPlayer,
    CalendarRankingResult,
    CalendarDisciplinaryZero,
    CalendarOfficialRankingSnapshot,
    calculate_calendar_official_ranking,
)
from beta_engine.domain.rankings.official import FrozenInput, OfficialRankingPolicy
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.domain.tournaments.calendar_tour import ranking_week


class CalendarNativeRankingAdoptionProof(FrozenInput):
    """Canonical entry and retirement binding; no newcomer implicit Tour entry."""

    schema_version: Literal["calendar_native_ranking_adoption_proof.v1"] = (
        "calendar_native_ranking_adoption_proof.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    lifecycle_replay_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    target_lifecycle_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    previous_ranking_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    calculated_ranking_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_result_fingerprints: tuple[str, ...]
    source_zero_fingerprints: tuple[str, ...]
    eligible_player_ids: tuple[str, ...]
    classified_player_ids: tuple[str, ...]
    not_entered_player_ids: tuple[str, ...]
    retired_player_ids: tuple[str, ...]

    @model_validator(mode="after")
    def validate_canonical_rosters(self):
        lists = (
            self.eligible_player_ids,
            self.classified_player_ids,
            self.not_entered_player_ids,
            self.retired_player_ids,
            self.source_result_fingerprints,
            self.source_zero_fingerprints,
        )
        if any(ids != tuple(sorted(set(ids))) for ids in lists):
            raise ValueError("Native ranking bridge requires canonical distinct proofs")
        if set(self.classified_player_ids) - set(self.eligible_player_ids):
            raise ValueError("Native ranking bridge classified an ineligible newcomer")
        if set(self.not_entered_player_ids) & set(self.eligible_player_ids):
            raise ValueError("Native ranking bridge ranked a never-entered athlete")
        return self

    @property
    def fingerprint(self) -> str:
        return canonical_hash(self.model_dump(mode="json"))


def validate_previous_ranking_owner(previous, previous_life, replay) -> None:
    """The previous Ranking is owned by the immediate prior lifecycle week.

    One exact index of that lifecycle snapshot replaces a per-row linear search
    and the per-row rebuilt identity set. The first occurrence of an identity is
    the one consulted, as ``next(...)`` did, and the checks and their messages
    keep their order: every row is first checked to be born, then each row's
    prior Tour Entry is checked.
    """
    if previous is None or (
        (previous.run_id, previous.branch_id) != (replay.run_id, replay.branch_id)
        or previous.week != ranking_week(previous_life.week)
        or previous.run_calendar != previous_life.week.calendar.to_metadata()
    ):
        raise ValueError("Native Ranking bridge requires the exact previous Saved ranking")
    by_id = {}
    for person in previous_life.players:
        by_id.setdefault(person.player_id, person)
    if any(row.player_id not in by_id for row in previous.rows):
        raise ValueError("Previous ranking contains an athlete not born at its publication")
    # Any athlete listed in the prior ranking must have an actual first Entry
    # strictly BEFORE that ranking publication. The first v2 population snapshot
    # never invents such an Entry.
    for row in previous.rows:
        prior = by_id[row.player_id]
        if (
            prior.tour_entry_week is None
            or prior.tour_entry_week.ordinal >= previous_life.week.ordinal
            or prior.status == "retired"
        ):
            raise ValueError("Previous ranking contains an athlete without prior Tour Entry")


def result_source_fingerprints(results) -> tuple[str, ...]:
    """Every source result, counted or expired, is retained in the proof."""
    return tuple(sorted(canonical_hash(r.model_dump(mode="json")) for r in results))


def calculate_native_ranking_from_signed_lifecycle(
    *, states, source, world_package_id: str, submissions,
    previous: CalendarOfficialRankingSnapshot,
    policy: OfficialRankingPolicy,
    results: tuple[CalendarRankingResult, ...] = (),
    disciplinary_zeros: tuple[CalendarDisciplinaryZero, ...] = (),
    expected: CalendarOfficialRankingSnapshot | None = None,
) -> tuple[CalendarOfficialRankingSnapshot, CalendarNativeRankingAdoptionProof]:
    """Read-only genuine Best N/NR/tie-break projection from v2/v3/v4 history.

    The lifecycle is replayed *before* reading its first Entry markers.
    We never award ranking eligibility merely because a player turned 15.
    The previous Ranking remains immutable and has to be owned by the actual
    immediate prior week. All result and zero receipts are external signed
    authorities, not generated from birthdays.
    """
    replay = verify_calendar_native_birth_history(
        states=states, source=source, world_package_id=world_package_id,
        submissions=submissions,
    )
    if len(states) < 2:
        raise ValueError("Native Ranking bridge requires a completed Week Transition")
    current = states[-1]
    previous_life = states[-2]
    clock = current.week.calendar
    validate_previous_ranking_owner(previous, previous_life, replay)

    players = tuple(
        CalendarRankingPlayer(
            player_id=p.player_id,
            tie_break_token=p.tie_break_token,
            tour_entry_week=ranking_week(p.tour_entry_week),
            retired=p.status == "retired",
        )
        for p in current.players if p.tour_entry_week is not None
    )
    eligible_ids = tuple(sorted(p.player_id for p in players))
    never_entered = tuple(sorted(
        p.player_id for p in current.players if p.tour_entry_week is None
    ))
    retired = tuple(sorted(
        p.player_id for p in current.players if p.status == "retired"
    ))
    candidate = calculate_calendar_official_ranking(
        run_id=replay.run_id, branch_id=replay.branch_id,
        run_calendar=clock, week=ranking_week(current.week),
        policy=policy, players=players, results=results,
        disciplinary_zeros=disciplinary_zeros, previous=previous,
    )
    if expected is not None and candidate != expected:
        raise ValueError("Published native ranking differs from Signed birth/Entry/NR authority")
    proof = CalendarNativeRankingAdoptionProof(
        run_id=replay.run_id, branch_id=replay.branch_id,
        lifecycle_replay_fingerprint=replay.fingerprint,
        target_lifecycle_fingerprint=current.fingerprint,
        previous_ranking_fingerprint=previous.fingerprint,
        calculated_ranking_fingerprint=candidate.fingerprint,
        source_result_fingerprints=result_source_fingerprints(results),
        source_zero_fingerprints=tuple(sorted(canonical_hash(z.model_dump(mode="json")) for z in disciplinary_zeros)),
        eligible_player_ids=eligible_ids,
        classified_player_ids=tuple(sorted(r.player_id for r in candidate.rows)),
        not_entered_player_ids=never_entered,
        retired_player_ids=retired,
    )
    return candidate, proof
